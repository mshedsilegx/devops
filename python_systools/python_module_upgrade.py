#!/usr/bin/env python3
# ----------------------------------------------
# python_module_upgrade.py
# v1.0.0xg  2025/12/08  XdG / MIS Center
# ----------------------------------------------
#
import argparse
import importlib.metadata
import importlib.util
import os
import sys
from pathlib import Path
import json
import subprocess
import site

# Define a dummy class for when requests is not installed.
class DummyRequests:
    @staticmethod
    def get(url, timeout):
        class DummyResponse:
            status_code = 503
            @staticmethod
            def json():
                return {'info': {'version': 'Error: requests not installed'}}
        return DummyResponse()

# Third-Party Imports
try:
    import requests
except ImportError:
    requests = DummyRequests()


# ====================================================================
# CONFIGURATION CONSTANTS
# ====================================================================

# Minimum required Python version tuple (3.8 is the minimum for importlib.metadata)
MIN_PYTHON_VERSION_TUPLE = (3, 8)

# Base URL for the PyPI JSON API lookup
PYPI_JSON_URL = "https://pypi.org/pypi/{package_name}/json"

# Global Debug Flag Placeholder (set in main())
DEBUG_MODE = False

# ====================================================================

def get_package_location_category(install_path):
    """
    Determines if a package is local, system, or custom.
    """
    if not install_path or not os.path.exists(install_path):
        return "unknown"

    real_install_path = os.path.realpath(install_path)
    home_dir = os.path.expanduser('~')

    # 1. If inside the user's home directory, it's 'local'.
    if real_install_path.startswith(home_dir):
        return "local"

    # 2. If in a system-wide site-packages directory, it's 'system'.
    for path in site.getsitepackages():
        if real_install_path.startswith(os.path.realpath(path)):
            return "system"

    # 3. Otherwise, it's 'custom'.
    return "custom"

# --- Helper function for External Data (Network Request) ---
def get_latest_version_from_pypi(package_name: str) -> str:
    """
    Fetches the latest published version of a package from the PyPI JSON API.
    """
    if isinstance(requests, DummyRequests):
        return "Error: requests library not found for network lookup"

    try:
        url = PYPI_JSON_URL.format(package_name=package_name)
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            return data['info']['version']
        elif response.status_code == 404:
            return "Package not found on PyPI"
        else:
            return f"Error: HTTP {response.status_code}"

    except requests.exceptions.RequestException:
        return "Error: Network failure"
    except Exception:
        return "Error: Metadata parsing failure"

# --- Helper function to determine module type (purelib vs platlib) ---
def get_module_type(dist: importlib.metadata.Distribution) -> str:
    """
    Determines if a package is purelib or platlib by checking for compiled files.
    """
    compiled_extensions = ('.so', '.pyd', '.dll', '.dylib')

    if dist.files is None:
        return "Type Unknown (No File Listing)"

    for file in dist.files:
        if Path(str(file)).suffix.lower() in compiled_extensions:
            return "wheel (platlib)"

    return "wheel (purelib)"


def resolve_package_metadata(package_name: str) -> dict:
    """
    Resolves all package properties, including path and versions, using definitive file-based logic.
    """
    global DEBUG_MODE

    if DEBUG_MODE:
        print("\n--- DEBUG: Path Resolution Start ---")

    if sys.version_info < MIN_PYTHON_VERSION_TUPLE:
        return {"error": f"Python {MIN_PYTHON_VERSION_TUPLE[0]}.{MIN_PYTHON_VERSION_TUPLE[1]} or newer required for metadata handling."}

    # --- 1. Get Distribution Metadata ---
    try:
        dist = importlib.metadata.distribution(package_name)
        current_version = dist.version
        metadata_dict = dist.metadata

    except importlib.metadata.PackageNotFoundError:
        return {"error": f"Package '{package_name}' not found."}

    # --- 2. Determine Top-Level Module (TML) ---
    top_level_text = dist.read_text('top_level.txt')

    if top_level_text:
        # Use the first line as the primary TML.
        raw_tml = top_level_text.splitlines()[0].strip()
    else:
        raw_tml = package_name.lower().replace('-', '_')

    # FIX 1: TML Correction. Ensure TML is the import name, not an internal component.
    package_name_normalized = package_name.lower().replace('-', '_')
    top_level_module = raw_tml

    # Specific fix for known complex packages where TML is not the package name
    if top_level_module == 'snowflake' and package_name_normalized == 'snowflake_connector_python':
         top_level_module = 'snowflake'
    elif top_level_module == '_cffi_backend' and package_name_normalized == 'cffi':
         top_level_module = 'cffi'
    # General fallback: if the derived TML looks like a sub-module, but the package name is the real import name.
    elif top_level_module not in package_name_normalized and top_level_module.startswith('_'):
        top_level_module = package_name_normalized
    elif package_name_normalized.startswith(top_level_module):
         pass # Assume TML is correct (e.g., 'urllib3')
    else:
        # Final fallback for namespace packages, often just the first word
        top_level_module = package_name_normalized.split('_')[0]


    # --- 3. Determine Installation Root (dist_root) ---
    dist_root = "Could not determine root."

    # Calculate root without relying on the unreliable 'dist.location' attribute
    try:
        dist_root = str(dist.locate_file('').parent)
    except Exception:
        dist_root = "Could not determine root via files."

    if DEBUG_MODE:
        print(f"DEBUG 1: Top-Level Module (TML): {top_level_module}")
        print(f"DEBUG 1: Distribution Root (Calculated): {dist_root}")

    # --- 4. Locate the installation folder (FINAL PATH LOGIC) ---
    resolved_path = "Could not resolve path."

    # Primary Method: Construct Path using the calculated root + TML
    if dist_root != "Could not determine root." and Path(dist_root).is_dir():
        potential_path = Path(dist_root) / top_level_module

        if DEBUG_MODE:
            print(f"DEBUG 2: Constructed Module Path: {potential_path}")
            print(f"DEBUG 2: Constructed Path Exists?: {potential_path.is_dir()}")

        # Use this path if the directory physically exists.
        if potential_path.is_dir():
            resolved_path = str(potential_path)

        # If the constructed path doesn't exist, we must fall through to find_spec().
        else:
             resolved_path = "Falling through to find_spec."

    # Fallback Method: Use find_spec() only if primary method failed or explicitly fell through.
    if resolved_path == "Could not resolve path." or resolved_path == "Falling through to find_spec.":
        try:
            spec = importlib.util.find_spec(top_level_module)

            if spec and spec.submodule_search_locations:
                # This is the most accurate result from the import system (e.g., /.../cffi)
                resolved_path = spec.submodule_search_locations[0]
            elif spec and spec.origin:
                resolved_path = os.path.dirname(spec.origin)
            else:
                 # Final resort: use the calculated install root
                 resolved_path = dist_root
        except ImportError:
            # If import fails, fall back to calculated root
            resolved_path = dist_root

    if DEBUG_MODE:
        print(f"DEBUG FINAL: Resolved Path Before Return: {resolved_path}")
        print("--- DEBUG: Path Resolution End ---\n")

    # --- 5. Gather Remaining Metadata ---
    latest_version = get_latest_version_from_pypi(package_name)
    module_type = get_module_type(dist)
    location_category = get_package_location_category(dist_root)

    requires_dist = metadata_dict.get('Requires-Dist')

    return {
        "package_name": package_name,
        "import_name": top_level_module,
        "exact_path": resolved_path,
        "current_version": current_version,
        "latest_version": latest_version,
        "module_type": module_type,
        "location_category": location_category,

        # Verbose/Additional Fields
        "metadata_summary": metadata_dict.get('Summary', 'N/A'),
        "required_python_version": metadata_dict.get('Requires-Python', 'N/A'),
        "license": metadata_dict.get('License', metadata_dict.get('Classifier', 'N/A')),
        "author": metadata_dict.get('Author', 'N/A'),
        "homepage": metadata_dict.get('Home-page', 'N/A'),
        "required_dependencies": requires_dist if isinstance(requires_dist, list) else ([requires_dist] if requires_dist else [])
    }

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
    global DEBUG_MODE

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

    # Optional arguments for output control
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output the results in JSON format.'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress introductory messages and separator lines in text output.'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Display detailed dependency, licensing, and author information.'
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
    DEBUG_MODE = args.debug

    if args.list:
        list_all_packages()
    elif args.upgrade:
        upgrade_modules(simulate=args.simulate, target=args.target)

if __name__ == "__main__":
    main()
