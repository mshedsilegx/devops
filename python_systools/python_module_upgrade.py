#!/usr/bin/env python3

import argparse
import sys
import importlib.metadata
import site
import json
import os


def get_package_location(dist):
    """Determine the location category of a distribution."""
    # Get the path of one of the package's files to determine its location.
    try:
        # Get the first file path from the distribution files.
        # The specific file doesn't matter, we just need its directory.
        first_file = next(iter(dist.files))
        # locate_file gives the absolute path to the file.
        location = str(dist.locate_file(first_file))
    except (StopIteration, TypeError):
        return "unknown (no files listed)"

    # 1. Check for virtual environment
    is_virtualenv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if is_virtualenv and location.startswith(sys.prefix):
        return "local (virtualenv)"

    # 2. Check for user-specific installation (e.g., pip install --user)
    user_site_packages = site.getusersitepackages()
    if isinstance(user_site_packages, str):
        user_site_packages = [user_site_packages]
    for user_path in user_site_packages:
        if location.startswith(user_path):
            return "local (user)"

    # 3. Check for PYTHONPATH
    pythonpath = os.environ.get('PYTHONPATH')
    if pythonpath:
        # os.path.abspath is important for matching relative paths
        for path in [os.path.abspath(p) for p in pythonpath.split(os.pathsep) if p]:
            if location.startswith(path):
                return "custom (PYTHONPATH)"

    # 4. Check for system-wide installation
    # site.getsitepackages() returns system-specific paths
    for path in site.getsitepackages():
        if location.startswith(path):
            return "global system"

    return "unknown"

def get_package_type(dist):
    """Determine the packaging type of a distribution (e.g., wheel, sdist)."""
    # A simple way to check is to look at the path of one of its metadata files.
    # Wheel installations use .dist-info directories, legacy sdists use .egg-info.
    try:
        # dist.files contains paths relative to the site-packages directory.
        # One of these files is the METADATA file.
        for file_path in dist.files:
            if str(file_path).endswith('.dist-info/METADATA'):
                return "wheel"
            elif str(file_path).endswith('.egg-info/PKG-INFO'):  # sdists have PKG-INFO
                return "sdist (egg)"
            # Some old packages might just have an .egg-info file.
            elif str(file_path).endswith('.egg-info'):
                return "sdist (egg)"
    except Exception:
        pass  # If we can't determine it, we'll return "unknown"
    return "unknown"

def list_modules():
    """Lists all installed Python modules and their locations."""
    print(f"{'Module':<30} {'Version':<15} {'Location':<25} {'Type':<15}")
    print("="*85)
    dists = importlib.metadata.distributions()
    # Sort distributions by name for consistent output
    sorted_dists = sorted(dists, key=lambda d: d.metadata['name'].lower())
    for dist in sorted_dists:
        name = dist.metadata['name']
        version = dist.version
        location_category = get_package_location(dist)
        package_type = get_package_type(dist)
        print(f"{name:<30} {version:<15} {location_category:<25} {package_type:<15}")

import subprocess

def get_outdated_packages():
    """Gets a list of outdated packages."""
    try:
        # We specify the columns to ensure consistent output format
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--outdated', '--format=json'],
            capture_output=True,
            text=True,
            check=True
        )
        # Pip's JSON format gives us a list of dictionaries
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error checking for outdated packages: {e}", file=sys.stderr)
        return []

def upgrade_modules(simulate=False, target=None):
    """Upgrades all installed Python modules."""
    outdated_packages = get_outdated_packages()

    if not outdated_packages:
        print("All packages are up to date.")
        return

    if simulate:
        print(f"{'Module':<30} {'Old Version':<15} {'New Version':<15}")
        print("="*60)
        for package in outdated_packages:
            name = package['name']
            current_version = package['version']
            latest_version = package['latest_version']
            print(f"{name:<30} {current_version:<15} {latest_version:<15}")
    else:
        package_names = [pkg['name'] for pkg in outdated_packages]
        print(f"Upgrading {len(package_names)} packages...")
        command = [sys.executable, '-m', 'pip', 'install', '--upgrade'] + package_names
        if target:
            command.extend(['--target', target])

        try:
            # We stream the output of pip to give the user real-time feedback
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
                # Read and print stdout line by line
                if proc.stdout:
                    for line in proc.stdout:
                        print(line, end='')

                # Wait for the process to complete
                proc.wait()

                # Check for errors after the process has finished
                if proc.returncode != 0 and proc.stderr:
                    stderr_output = "".join(proc.stderr.readlines())
                    raise subprocess.CalledProcessError(proc.returncode, command, stderr=stderr_output)

            print("\nSuccessfully upgraded all packages.")
        except subprocess.CalledProcessError as e:
            print(f"\nFailed to upgrade packages. Error:\n{e.stderr}", file=sys.stderr)
        except FileNotFoundError:
            print(f"Error: The command '{command[0]}' was not found.", file=sys.stderr)


def main():
    """Main function to parse arguments and execute the script."""
    parser = argparse.ArgumentParser(description="A script to list and upgrade Python modules.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all installed modules.")
    group.add_argument("--upgrade", action="store_true", help="Upgrade all installed modules.")
    parser.add_argument("--simulate", action="store_true", help="Simulate the upgrade process.")
    parser.add_argument("--target", type=str, help="Specify a target directory for module upgrades.")

    args = parser.parse_args()

    if args.list:
        list_modules()
    elif args.upgrade:
        upgrade_modules(simulate=args.simulate, target=args.target)
    else:
        # This branch is technically unreachable because the group is required,
        # but we keep it for clarity and robustness.
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
