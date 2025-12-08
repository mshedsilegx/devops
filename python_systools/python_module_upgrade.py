#!/usr/bin/env python3

import argparse
import sys
import importlib.metadata
import site
import json

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
            return "global custom (user)"

    # 3. Check for system-wide installation
    for path in sys.path:
        if path and ('site-packages' in path or 'dist-packages' in path) and location.startswith(path):
            return "global system"

    return "unknown"

def list_modules():
    """Lists all installed Python modules and their locations."""
    print(f"{'Module':<30} {'Version':<15} {'Location':<25}")
    print("="*75)
    dists = importlib.metadata.distributions()
    # Sort distributions by name for consistent output
    sorted_dists = sorted(dists, key=lambda d: d.metadata['name'].lower())
    for dist in sorted_dists:
        name = dist.metadata['name']
        version = dist.version
        location_category = get_package_location(dist)
        print(f"{name:<30} {version:<15} {location_category:<25}")

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
        print("Upgrading packages...")
        for package in outdated_packages:
            package_name = package['name']
            print(f"Upgrading {package_name}...")
            command = [sys.executable, '-m', 'pip', 'install', '--upgrade', package_name]
            if target:
                command.extend(['--target', target])
            
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
                print(f"Successfully upgraded {package_name}.")
            except subprocess.CalledProcessError as e:
                print(f"Failed to upgrade {package_name}: {e.stderr}", file=sys.stderr)


def main():
    """Main function to parse arguments and execute the script."""
    parser = argparse.ArgumentParser(description="A script to list and upgrade Python modules.")
    parser.add_argument("--list", action="store_true", help="List all installed modules.")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade all installed modules.")
    parser.add_argument("--simulate", action="store_true", help="Simulate the upgrade process.")
    parser.add_argument("--target", type=str, help="Specify a target directory for module upgrades.")

    args = parser.parse_args()

    if args.list:
        list_modules()
    elif args.upgrade:
        upgrade_modules(simulate=args.simulate, target=args.target)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
