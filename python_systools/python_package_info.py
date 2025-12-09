#!/usr/bin/env python3
# ----------------------------------------------
# python_module_info.py
# v1.0.0xg  2025/12/08  XdG / MIS Center
# ----------------------------------------------
#
# Objective:
# This script provides a reliable and detailed inspection of an installed Python package.
# It is designed to find the exact on-disk installation location of a package and
# retrieve comprehensive metadata, including version, dependencies, and module type.
#
# Core Functionality:
# 1. Path Resolution: Implements a robust, multi-step process to determine the
#    exact path of the package, prioritizing Python's own import machinery to
#    ensure accuracy, especially for complex packages (e.g., namespace, editable).
# 2. Metadata Retrieval: Uses the standard `importlib.metadata` library to fetch
#    details like version, author, license, and dependencies.
# 3. External Version Check: Optionally queries the PyPI API to find the latest
#    available version of the package, helping identify outdated dependencies.
# 4. Output Flexibility: Provides both human-readable text output (with multiple
#    verbosity levels) and a machine-parseable JSON format for automation.
#
# ----------------------------------------------

import argparse
import importlib.metadata
import importlib.util
import os
import sys
from pathlib import Path
import json

# Third-Party Imports
# Note: Ensure 'requests' is installed (pip install requests)
try:
    import requests
except ImportError:
    # If requests is not installed, provide a dummy object to prevent errors
    class DummyRequests:
        @staticmethod
        def get(url, timeout):
            class DummyResponse:
                status_code = 503
                @staticmethod
                def json():
                    return {'info': {'version': 'Error: requests not installed'}}
            return DummyResponse()
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

# --- Helper function for External Data (Network Request) ---
def get_latest_version_from_pypi(package_name: str) -> str:
    """
    Fetches the latest published version of a package from the PyPI JSON API.

    This function performs a network request to the public PyPI repository to get
    the latest version number. It is designed to be resilient—if the 'requests'
    library is not installed or if there is a network error, it will return a
    descriptive error string instead of crashing the script.

    Args:
        package_name: The name of the package as it is known on PyPI.

    Returns:
        A string containing the latest version number, or an error message.
    """
    # Check if the real 'requests' library is available. If not, use the dummy and return an error.
    if 'requests' not in sys.modules and requests.__name__ == 'DummyRequests':
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

    A 'purelib' package contains only Python code and can run on any OS.
    A 'platlib' package contains platform-specific compiled code (e.g., C extensions)
    and is specific to an OS and architecture.

    Args:
        dist: An `importlib.metadata.Distribution` object for the package.

    Returns:
        A string indicating "purelib" or "platlib".
    """
    # Define a set of file extensions that indicate compiled, platform-specific binaries.
    compiled_extensions = ('.so', '.pyd', '.dll', '.dylib')
    
    # If the package metadata does not include a file list, we cannot determine the type.
    if dist.files is None:
        return "Type Unknown (No File Listing)"
        
    for file in dist.files:
        if Path(str(file)).suffix.lower() in compiled_extensions:
            return "platlib (Binary/Compiled C/C++)"
            
    return "purelib (Pure Python code)"


def resolve_package_metadata(package_name: str) -> dict:
    """
    Resolves all package properties, including path and versions, using definitive file-based logic.

    This is the core function of the script. It orchestrates the process of finding
    a package, determining its importable name, resolving its exact file path, and
    gathering all relevant metadata. The path resolution is particularly robust,
    employing a multi-step strategy to ensure accuracy.

    Args:
        package_name: The name of the package to resolve.

    Returns:
        A dictionary containing all the resolved metadata. In case of an error,
        it returns a dictionary with an "error" key.
    """
    global DEBUG_MODE
    
    if DEBUG_MODE:
        print("\n--- DEBUG: Path Resolution Start ---")
    
    if sys.version_info < MIN_PYTHON_VERSION_TUPLE:
        return {"error": f"Python {MIN_PYTHON_VERSION_TUPLE[0]}.{MIN_PYTHON_VERSION_TUPLE[1]} or newer required for metadata handling."}
        
    # --- 1. Get Distribution Metadata ---
    # Use the standard `importlib.metadata` to find the package. This is the
    # modern and reliable way to query installed package information.
    try:
        dist = importlib.metadata.distribution(package_name)
        current_version = dist.version
        metadata_dict = dist.metadata
        
    except importlib.metadata.PackageNotFoundError:
        return {"error": f"Package '{package_name}' not found."}

    # --- 2. Determine Top-Level Module (TML) ---
    # The "top-level module" is the name you actually use in an `import` statement.
    # It can be different from the package name (e.g., package `Pillow` -> import `PIL`).
    # The `top_level.txt` file within the package's `.dist-info` is the definitive source for this.
    top_level_text = dist.read_text('top_level.txt')
    
    if top_level_text:
        # Use the first line as the primary TML.
        raw_tml = top_level_text.splitlines()[0].strip()
    else:
        # If `top_level.txt` is missing, fall back to a normalized version of the package name.
        raw_tml = package_name.lower().replace('-', '_')

    # FIX 1: TML Correction. Ensure TML is the import name, not an internal component.
    # This section handles edge cases where the TML from `top_level.txt` might be
    # ambiguous or incorrect. It applies heuristics to select the correct import name.
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
    # This step calculates the base `site-packages` or `dist-packages` directory where
    # the package is installed. We do this by finding the `.dist-info` directory and
    # getting its parent. This is more reliable than using `dist.location`, which can be inconsistent.
    dist_root = "Could not determine root."
    
    # Calculate root without relying on the unreliable 'dist.location' attribute
    try:
        if dist.files:
            # Find the name of the .dist-info or .egg-info directory from the file list.
            dist_info_folder_name = [str(f).split(os.sep)[0] for f in dist.files if str(f).endswith('.dist-info') or str(f).endswith('.egg-info')][0]
            # Locate that folder and get its parent, which is the installation root.
            dist_root = str(Path(os.path.abspath(dist.locate_file(Path(dist_info_folder_name)))).parent)

    except Exception:
        dist_root = "Could not determine root via files."

    if DEBUG_MODE:
        print(f"DEBUG 1: Top-Level Module (TML): {top_level_module}")
        print(f"DEBUG 1: Distribution Root (Calculated): {dist_root}")

    # --- 4. Locate the installation folder (FINAL PATH LOGIC) ---
    # This is the most critical part of the script. It uses a multi-step strategy
    # to find the exact path of the package's code.
    resolved_path = "Could not resolve path."
    
    # Primary Method: Construct Path using the calculated root + TML.
    # This works for most standard packages. We guess the path by combining the
    # installation root (e.g., `.../site-packages/`) with the module name (e.g., `requests`).
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

    # Fallback Method: Use find_spec() only if the primary method failed.
    # `importlib.util.find_spec()` asks Python's import system directly to locate
    # the module. This is the ultimate source of truth and correctly handles
    # complex cases like namespace packages, editable installs, and single-file modules.
    if resolved_path == "Could not resolve path." or resolved_path == "Falling through to find_spec.":
        try:
            spec = importlib.util.find_spec(top_level_module)
            
            if spec and spec.submodule_search_locations:
                # For regular packages, this attribute gives the directory path.
                resolved_path = spec.submodule_search_locations[0]
            elif spec and spec.origin:
                # For single-file modules, we get the file path and then find its directory.
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
    # With the core path resolution complete, we now collect all other useful
    # information about the package.
    latest_version = get_latest_version_from_pypi(package_name)
    module_type = get_module_type(dist)
    
    # Get the list of dependencies.
    requires_dist = metadata_dict.get('Requires-Dist')
    
    # Assemble the final dictionary to be returned.
    return {
        "package_name": package_name,
        "import_name": top_level_module, 
        "exact_path": resolved_path, 
        "current_version": current_version,
        "latest_version": latest_version,
        "module_type": module_type,
        
        # Verbose/Additional Fields
        "metadata_summary": metadata_dict.get('Summary', 'N/A'),
        "required_python_version": metadata_dict.get('Requires-Python', 'N/A'),
        "license": metadata_dict.get('License', metadata_dict.get('Classifier', 'N/A')),
        "author": metadata_dict.get('Author', 'N/A'),
        "homepage": metadata_dict.get('Home-page', 'N/A'),
        "required_dependencies": requires_dist if isinstance(requires_dist, list) else ([requires_dist] if requires_dist else [])
    }

# --- Command-Line Entry Point (Handles Display) ---

def display_results(metadata: dict, json_output: bool, quiet_mode: bool, verbose_mode: bool):
    """
    Prints the structured metadata dictionary either as formatted text or JSON.

    This function is responsible for the presentation layer. It takes the data
    dictionary from `resolve_package_metadata` and formats it for the user based
    on the specified command-line flags.

    Args:
        metadata: The dictionary of package information.
        json_output: If True, output in JSON format.
        quiet_mode: If True, suppress headers in text output.
        verbose_mode: If True, include extra details in text output.
    """
    # If the metadata dictionary contains an error, print it to stderr and exit.
    if 'error' in metadata:
        sys.stderr.write(f"ERROR: {metadata['error']}\n")
        return
        
    # Handle JSON output.
    if json_output:
        print(json.dumps(metadata, indent=4))
    else:
        # Handle human-readable text output.
        
        if not quiet_mode:
            print("\n--- Package Metadata ---")
            
        print(f"Found Package:   {metadata['package_name']}")
        print(f"Import Name:     {metadata['import_name']}")
        print(f"Exact Path:      {metadata['exact_path']}")
        
        if not quiet_mode:
            print("---")
            
        print(f"Current Version: {metadata['current_version']}")
        print(f"Latest Version:  {metadata['latest_version']}")
        print(f"Module Type:     {metadata['module_type']}")
        
        if verbose_mode:
            if not quiet_mode:
                print("\n--- Dependencies & Licensing ---")
            
            def format_list(items):
                items = [str(item) for item in items]
                return "\n" + "    " + "\n    ".join(items) if items else "None"
            
            print(f"Summary:         {metadata['metadata_summary']}")
            print(f"License:         {metadata['license']}")
            print(f"Author:          {metadata['author']}")
            print(f"Homepage URL:    {metadata['homepage']}")
            print(f"Python Requires: {metadata['required_python_version']}")
            print(f"Dependencies:    {format_list(metadata['required_dependencies'])}")


def main():
    """
    The main entry point of the script.

    This function is responsible for:
    1. Parsing command-line arguments.
    2. Calling the core logic to resolve package metadata.
    3. Passing the results to the display function for output.
    """
    global DEBUG_MODE
    
    # Set up the command-line argument parser.
    parser = argparse.ArgumentParser(
        description="Locate the exact installation folder and retrieve metadata for a Python package."
    )
    
    # Define all the command-line arguments the script accepts.
    parser.add_argument(
        '--package',
        type=str,
        required=True,
        help="The name of the package as listed by 'pip list'."
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
    
    if not args.quiet and not args.json:
        print(f"Searching for: {args.package}")
    
    metadata = resolve_package_metadata(args.package)
    display_results(metadata, args.json, args.quiet, args.verbose)

if __name__ == "__main__":
    main()
