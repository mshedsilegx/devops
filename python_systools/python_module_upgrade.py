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
import subprocess
from pathlib import Path

def get_package_type(dist):
    """Determine the distribution type of a package (e.g., wheel, sdist)."""
    # A reliable way to check for a wheel is the presence of a 'WHEEL' file in its metadata.
    if dist.read_text('WHEEL') is not None:
        return "wheel"
    # Egg-info indicates a source distribution installed via setup.py
    # The `_path` attribute is not public, but it's a reliable way to get the metadata dir.
    if hasattr(dist, '_path') and str(dist._path).endswith('.egg-info'):
        return "sdist"
    return "unknown"

def get_package_location(dist):
    """Determine the location category of a distribution and its full path."""
    try:
        # The `_path` attribute points to the .dist-info or .egg-info directory.
        # Its parent is the site-packages or equivalent directory.
        if hasattr(dist, '_path'):
            install_path = dist._path.parent
            location_str = str(install_path)
        else:
            # Fallback for older/unusual distributions
            first_file = next(iter(dist.files))
            install_path = dist.locate_file(first_file).parent
            location_str = str(install_path)
    except (StopIteration, TypeError):
        return "unknown", "N/A"

    # 1. Check for virtual environment (local)
    is_virtualenv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if is_virtualenv and location_str.startswith(sys.prefix):
        return "local (virtualenv)", install_path

    # 2. Check for custom paths from PYTHONPATH
    pythonpath = os.environ.get('PYTHONPATH')
    if pythonpath:
        # Normalize paths for reliable comparison
        custom_paths = [str(Path(p).resolve()) for p in pythonpath.split(os.pathsep)]
        resolved_location = str(install_path.resolve())
        for path in custom_paths:
            if resolved_location.startswith(path):
                return "custom (PYTHONPATH)", install_path

    # 3. Check for user-specific installation (local)
    user_site_packages = site.getusersitepackages()
    if isinstance(user_site_packages, str): # It can be a list or a string
        user_site_packages = [user_site_packages]
    for user_path in user_site_packages:
        if location_str.startswith(user_path):
            return "local (user)", install_path

    # 4. Check for system-wide installation (global)
    for path in sys.path:
        # Refine the check to avoid matching unrelated paths
        if path and ('site-packages' in path or 'dist-packages' in path) and location_str.startswith(path):
            return "global (system)", install_path

    return "unknown", install_path

def list_modules():
    """Lists all installed Python modules with their type, location, and path."""
    header = f"{'Module':<30} {'Version':<15} {'Type':<10} {'Location':<20} {'Path'}"
    print(header)
    print("=" * (len(header) + 5))

    dists = importlib.metadata.distributions()
    sorted_dists = sorted(dists, key=lambda d: d.metadata['name'].lower())

    for dist in sorted_dists:
        name = dist.metadata['name']
        version = dist.version
        pkg_type = get_package_type(dist)
        location_category, path = get_package_location(dist)
        print(f"{name:<30} {version:<15} {pkg_type:<10} {location_category:<20} {path}")

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
    """Upgrades all installed Python modules using a single pip command."""
    outdated_packages = get_outdated_packages()

    if not outdated_packages:
        print("All packages are up to date.")
        return

    # Extract package names for the upgrade command
    package_names = [pkg['name'] for pkg in outdated_packages]

    if simulate:
        print("--- Simulation Mode ---")
        print("The following packages would be upgraded:")
        print(f"{'Module':<30} {'Old Version':<15} {'New Version':<15}")
        print("="*60)
        for package in outdated_packages:
            print(f"{package['name']:<30} {package['version']:<15} {package['latest_version']:<15}")
    else:
        print(f"Attempting to upgrade {len(package_names)} packages...")

        # Construct a single command to upgrade all packages at once for correct dependency resolution
        command = [sys.executable, '-m', 'pip', 'install', '--upgrade'] + package_names
        if target:
            command.extend(['--target', target])

        try:
            # We stream the output directly to the console so the user can see pip's progress.
            process = subprocess.run(
                command,
                check=True,
                text=True,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            print("\nSuccessfully upgraded all packages.")
        except subprocess.CalledProcessError:
            # The error is already printed to stderr by the subprocess, so we just add context and exit.
            print(f"\nAn error occurred during the upgrade process.", file=sys.stderr)
            sys.exit(1)

def main():
    """Main function to parse arguments and execute the script."""
    parser = argparse.ArgumentParser(description="A script to list and upgrade Python modules.")

    # Create a mutually exclusive group, ensuring either --list or --upgrade is chosen
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all installed modules with details.")
    group.add_argument("--upgrade", action="store_true", help="Upgrade all outdated modules.")

    # These arguments are only relevant for the --upgrade action
    parser.add_argument("--simulate", action="store_true", help="Simulate the upgrade process (only valid with --upgrade).")
    parser.add_argument("--target", type=str, help="Specify a target directory for module upgrades (only valid with --upgrade).")

    args = parser.parse_args()

    # Manually validate that --simulate and --target are not used with --list
    if args.list and (args.simulate or args.target):
        parser.error("--simulate and --target can only be used with --upgrade.")

    if args.list:
        list_modules()
    elif args.upgrade:
        upgrade_modules(simulate=args.simulate, target=args.target)

if __name__ == "__main__":
    main()
