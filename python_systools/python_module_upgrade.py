#!/usr/bin/env python3
# ----------------------------------------------
# python_module_upgrade.py
# v1.1.0xg  2025/12/09  XdG / MIS Center
# ----------------------------------------------
#
"""
Objective:
    This script is a system utility designed to manage Python packages. It allows
    administrators to inspect installed packages with detailed metadata and
    perform bulk upgrades of all outdated modules.

Core Functionality:
    1. Package Listing (--list):
       - Scans all installed packages.
       - Uses the shared `python_pkg_utils` to resolve the exact on-disk location,
         version, and module type (pure Python vs. compiled extension).
       - Classifies packages as 'system', 'local', or 'custom' based on path.

    2. Bulk Upgrade (--upgrade):
       - Identifies outdated packages using `pip list --outdated`.
       - Performs a bulk upgrade of all identified packages.
       - Supports a simulation mode (--simulate) to preview changes without acting.

    3. Shared Logic:
       - Relies on `python_pkg_utils.py` for robust path resolution and common
         helper functions, ensuring consistency with `python_package_info.py`.
"""

import argparse
import sys
import json
import subprocess
import importlib.metadata
from python_pkg_utils import resolve_package_metadata, set_debug_mode

def list_all_packages():
    """
    Lists all installed packages with their metadata.
    """
    header = f"{'Package':<30} {'Version':<15} {'Location':<10} {'Type':<18} {'Path'}"
    print(header)
    print("=" * (len(header) + 5))

    dists = importlib.metadata.distributions()
    for dist in sorted(dists, key=lambda d: d.metadata['name'].lower()):
        package_name = dist.metadata['name']
        metadata = resolve_package_metadata(package_name)
        if 'error' not in metadata:
            print(f"{metadata['package_name']:<30} {metadata['current_version']:<15} {metadata['location_category']:<10} {metadata['module_type']:<18} {metadata['exact_path']}")

def get_outdated_packages():
    """Gets a list of outdated packages."""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--outdated', '--format=json'],
            capture_output=True,
            text=True,
            check=True
        )
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
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
                if proc.stdout:
                    for line in proc.stdout:
                        print(line, end='')
                proc.wait()
                if proc.returncode != 0 and proc.stderr:
                    stderr_output = "".join(proc.stderr.readlines())
                    raise subprocess.CalledProcessError(proc.returncode, command, stderr=stderr_output)
            print("\nSuccessfully upgraded all packages.")
        except subprocess.CalledProcessError as e:
            print(f"\nFailed to upgrade packages. Error:\n{e.stderr}", file=sys.stderr)
        except FileNotFoundError:
            print(f"Error: The command '{command[0]}' was not found.", file=sys.stderr)

def main():
    
    parser = argparse.ArgumentParser(
        description="A tool to list and upgrade Python modules."
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--list',
        action='store_true',
        help="List all installed packages."
    )
    group.add_argument(
        '--upgrade',
        action='store_true',
        help="Upgrade all installed packages."
    )
    
    # Optional arguments for --upgrade
    parser.add_argument(
        '--simulate',
        action='store_true',
        help='Simulate the upgrade process.'
    )
    parser.add_argument(
        '--target',
        type=str,
        help='Specify a target directory for module upgrades.'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Display detailed path resolution debugging information.'
    )
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args()
    
    # Set the global debug flag based on user input
    set_debug_mode(args.debug)
    
    if args.list:
        list_all_packages()
    elif args.upgrade:
        upgrade_modules(simulate=args.simulate, target=args.target)

if __name__ == "__main__":
    main()
