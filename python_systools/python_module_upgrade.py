#!/usr/bin/env python3
# ----------------------------------------------
# python_module_upgrade.py
# v1.0.0xg  2025/12/08  XdG / MIS Center
# ----------------------------------------------

import argparse
import sys
import importlib.metadata
import site
import json
import os
import importlib.util

def get_package_location(dist):
    """Determine the location category and exact path of a distribution."""
    full_path = "N/A"
    install_path = "N/A"

    try:
        # The installation path is the parent of the package's metadata directory.
        metadata_path = dist.locate_file('')
        install_path = str(metadata_path.parent)

        # Get the list of all files belonging to the package.
        package_files = list(dist.files)

        # Filter out metadata and pycache files to find the actual source files.
        source_files = [
            os.path.join(install_path, str(f))
            for f in package_files
            if '.dist-info/' not in str(f) and '.egg-info/' not in str(f) and '__pycache__' not in str(f)
        ]

        if not source_files:
            # If there are no source files, the path is the installation directory.
            full_path = install_path
        elif len(source_files) == 1:
            # If there is only one source file, that is the path.
            full_path = source_files[0]
        else:
            # For multiple files, the common path is the top-level directory of the module.
            common_path = os.path.commonpath(source_files)
            # If the common path is the installation root, we may have a package like snowflake-connector-python
            if os.path.realpath(common_path) == os.path.realpath(install_path):
                 # Check for a directory that matches the first part of the package name
                pkg_name_root = dist.metadata['name'].split('-')[0]
                potential_path = os.path.join(install_path, pkg_name_root)
                if os.path.isdir(potential_path):
                    full_path = potential_path
                else:
                    full_path = common_path
            else:
                full_path = common_path

    except Exception:
        return "unknown", "N/A"

    # Categorize the location based on the installation path.
    real_install_path = os.path.realpath(install_path)
    home_dir = os.path.expanduser('~')

    # 1. If inside the user's home directory, it's 'local'.
    if real_install_path.startswith(home_dir):
        return "local", full_path

    # 2. If in a system-wide site-packages directory, it's 'system'.
    for path in site.getsitepackages():
        if real_install_path.startswith(os.path.realpath(path)):
            return "system", full_path

    # 3. Otherwise, it's 'custom'.
    return "custom", full_path

def get_package_type(dist):
    """Determine the packaging type of a distribution (e.g., wheel, sdist)."""
    try:
        # Check for wheel metadata first.
        is_wheel = any(str(f).endswith('.dist-info/METADATA') for f in dist.files)
        
        if is_wheel:
            # A wheel is platform-specific ('platlib') if it contains compiled binaries.
            has_binaries = any(
                str(f).endswith(('.so', '.pyd')) for f in dist.files
            )
            return "wheel (platlib)" if has_binaries else "wheel (purelib)"

        # Check for sdist (egg) metadata as a fallback.
        is_sdist = any(
            str(f).endswith(('.egg-info/PKG-INFO', '.egg-info')) for f in dist.files
        )
        if is_sdist:
            return "sdist (egg)"

    except Exception:
        # If we can't inspect the files for any reason, return unknown.
        return "unknown"

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
    """Lists all installed Python modules and their locations, avoiding duplicates."""
    # Define column headers. Location is shrunk, and Type is slightly expanded.
    header = f"{'Module':<30} {'Version':<15} {'Location':<10} {'Type':<18} {'Path'}"
    print(header)
    print("=" * (len(header) + 2))

    # To avoid duplicates, we get a unique set of package names first.
    all_dists_for_names = importlib.metadata.distributions()
    package_names = sorted({dist.metadata['name'] for dist in all_dists_for_names}, key=str.lower)

    for name in package_names:
        try:
            dist = importlib.metadata.distribution(name)
            version = dist.version
            location_category, path = get_package_location(dist)
            package_type = get_package_type(dist)
            print(f"{name:<30} {version:<15} {location_category:<10} {package_type:<18} {path}")
        except importlib.metadata.PackageNotFoundError:
            print(f"{name:<30} {'N/A':<15} {'N/A':<10} {'N/A':<18} {'N/A'}")

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
        # This branch is technically unreachable because the group is required,
        # but we keep it for clarity and robustness.
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
