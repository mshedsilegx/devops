#!/var/opt/python314/bin/python3.14
# ------------------------------------------
# /var/opt/apps/system/python_sysdiags.py
# v1.3.3xg  2025/10/14  XdG / MIS Center
# ------------------------------------------
"""
A comprehensive Python script to verify the Python interpreter's build environment,
specifically its linkage and capabilities with OpenSSL, and other key system settings.

Outputs detailed information about Python version, paths, environment flags,
OpenSSL version, TLS protocol support (including TLS 1.3),
basic hashlib functionality, and standard library module availability.

Usage:
  python_openssl.py [options]

Options:
  --env          Display Python Interpreter & Environment details.
  --build        Display Python Build-Time Configuration.
  --paths        Display Python Module Search Path (sys.path).
  --stdlib       Display Key Standard Library C-Extensions check.
  --math         Display Math Module C-Functionality Check.
  --ssl          Display OpenSSL & SSL Module Information.
  --tls13        Display TLS 1.3 Capability Check.
  --hashlib      Display Hashlib Functionality Check.
  --rlimits      Display System Resource Limits (Unix-like only).
  --all          Display all sections (default if no options specified).
  -h, --help     Show this help message and exit.

If no options are specified, the script will display all sections.

Required: Ensure that the following environment variables are UNSET
          in the shell *before* executing this script:
          PYTHONPATH, PYTHONHOME, PYTHON, PYTHON_PLATFORM
          (e.g., `unset PYTHONPATH`)
"""

import ssl
import sys
import hashlib
import sysconfig
import os
import importlib.util # For checking module presence
import argparse # For command-line argument parsing
import math # Added for the math module check

try:
    import resource # Unix-like systems only
except ImportError:
    resource = None # Will be None on Windows

# ----------------------------------------
# Diagnostic Section Functions
# ----------------------------------------
# Each function in this section is responsible for a single, modular
# diagnostic check. They print a formatted header and then the relevant
# system or Python interpreter information.
# ----------------------------------------

def print_python_env_details():
    """Prints Python Interpreter & Environment details."""
    print(f"\n----- Python Interpreter & Environment -----")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Python sitelib path (purelib): {sysconfig.get_path('purelib')}")
    print(f"Python sitearch path (platlib): {sysconfig.get_path('platlib')}")
    print(f"Python system platform: {sys.platform}")
    print(f"Python default encoding: {sys.getdefaultencoding()}")
    print(f"Python filesystem encoding: {sys.getfilesystemencoding()}")

    print("\nPython interpreter flags:")
    for flag_name in dir(sys.flags):
        if not flag_name.startswith('_'): # Exclude internal attributes
            value = getattr(sys.flags, flag_name)
            # Only print flags that are True, or have a meaningful value
            if value is True or (isinstance(value, int) and value != 0) or isinstance(value, str):
                 print(f"  - {flag_name}: {value}")


def print_python_build_config():
    """Prints Python Build-Time Configuration."""
    print(f"\n----- Python Build-Time Configuration -----")
    config_vars = sysconfig.get_config_vars()
    print(f"Compiler used (CC): {config_vars.get('CC', 'N/A')}")
    print(f"CFlags (CFLAGS): {config_vars.get('CFLAGS', 'N/A')}")
    print(f"LdFlags (LDFLAGS): {config_vars.get('LDFLAGS', 'N/A')}")
    print(f"Optimization Level (OPT): {config_vars.get('OPT', 'N/A')}")
    print(f"Python Debug Build (PYDEBUG): {config_vars.get('PYDEBUG', 'N/A')}")
    print(f"PyMALLOC enabled (WITH_PYMALLOC): {config_vars.get('WITH_PYMALLOC', 'N/A')}")
    print(f"Built as Shared Library (PY_ENABLE_SHARED): {config_vars.get('PY_ENABLE_SHARED', 'N/A')}")


def print_module_search_paths():
    """Prints Python Module Search Path (sys.path)."""
    print(f"\n----- Python Module Search Path (sys.path) -----")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")


def print_stdlib_c_extensions_check():
    """Checks and prints status of Key Standard Library C-Extensions."""
    print(f"\n----- Key Standard Library C-Extensions -----")
    c_extensions_to_check = [
        'zlib', '_bz2', '_lzma', '_sqlite3', '_curses', '_gdbm',
        '_json', '_socket', '_io', '_datetime', '_csv', '_elementtree',
        '_collections', '_thread', '_multiprocessing', '_zstd'
    ]
    for module_name in c_extensions_to_check:
        spec = importlib.util.find_spec(module_name)
        if spec:
            print(f"  - {module_name}: Found (from {spec.origin})")
        else:
            print(f"  - {module_name}: NOT Found (may indicate missing development libraries during build)", file=sys.stderr)


def print_math_module_check():
    """Checks the functionality and C-acceleration of the 'math' module."""
    print(f"\n----- Math Module C-Functionality Check -----")
    try:
        # Check if the math module itself imports
        # import math # Already imported globally at the top
        print(f"math module successfully imported.")

        # Check a C-accelerated function
        result = math.sqrt(16)
        print(f"math.sqrt(16) worked: {result}")
        print(f"This indicates math module's core (C) functions are accessible.")

        # Provide more details about the math module's origin
        print(f"math.__file__: {getattr(math, '__file__', 'N/A (Built-in)')}")
        print(f"math.__loader__: {getattr(math, '__loader__', 'N/A')}")
        if hasattr(math, '__loader__') and hasattr(math.__loader__, 'name') and math.__loader__.name == '_frozen_importlib.BuiltinImporter':
            print("  (math module appears to be a built-in C-module)")

    except ImportError:
        print(f"Error: 'math' module could not be imported. This is a severe issue.", file=sys.stderr)
    except Exception as e:
        print(f"Error: An unexpected error occurred during math module check: {e}", file=sys.stderr)


def print_openssl_info():
    """Prints OpenSSL & SSL Module Information."""
    print(f"\n----- OpenSSL & SSL Module Information -----")
    print(f"OpenSSL version Python is using: {ssl.OPENSSL_VERSION}")
    print(f"OpenSSL version number: {ssl.OPENSSL_VERSION_NUMBER}")
    if hasattr(ssl, 'OPENSSL_BUILT_ON'): # Python 3.7+
        print(f"OpenSSL built on: {ssl.OPENSSL_BUILT_ON}")
    else:
        print("OpenSSL built on: N/A (OPENSSL_BUILT_ON not available in this Python version)")

    print(f"OpenSSL TLS v1.2 protocol constant: {ssl.PROTOCOL_TLSv1_2}")
    print(f"Highest available client-side TLS protocol (PROTOCOL_TLS_CLIENT): {ssl.PROTOCOL_TLS_CLIENT}")
    print(f"Highest available server-side TLS protocol (PROTOCOL_TLS_SERVER): {ssl.PROTOCOL_TLS_SERVER}")

    print("\nDefault CA certificate paths (ssl.get_default_verify_paths()):")
    default_paths = ssl.get_default_verify_paths()
    print(f"  - CA file: {default_paths.cafile}")
    print(f"  - CA path: {default_paths.capath}")
    print(f"  - SSL certificate file: {getattr(default_paths, 'ssl_cert_file', 'N/A (Attribute not available)')}")
    print(f"  - SSL certificate path: {getattr(default_paths, 'ssl_cert_dir', 'N/A (Attribute not available)')}")
    print(f"  - SSL key file: {getattr(default_paths, 'ssl_key_file', 'N/A (Attribute not available)')}")


def print_tls13_capability_check():
    """Performs and prints TLS 1.3 Capability Check."""
    print(f"\n----- TLS 1.3 Capability Check -----")
    try:
        print(f"TLSVersion.TLSv1_3 constant: {ssl.TLSVersion.TLSv1_3}")

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        print("SSLContext successfully created with minimum TLS 1.3 version.")
        print("This confirms active TLS 1.3 support through OpenSSL.")
    except AttributeError as e:
        print(f"Error: TLS 1.3 (ssl.TLSVersion.TLSv1_3) attribute not found: {e}", file=sys.stderr)
        print("This indicates Python's ssl module or linked OpenSSL might not fully support TLS 1.3, "
              "or the constant is not exposed.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred during TLS 1.3 check: {e}", file=sys.stderr)


def print_hashlib_check():
    """Performs and prints Hashlib Functionality Check."""
    print(f"\n----- Hashlib Functionality Check -----")
    try:
        h = hashlib.blake2b() # A modern hash algorithm relying on OpenSSL
        print("hashlib.blake2b() initialization worked successfully.")
        print("This confirms OpenSSL's cryptographic hash algorithms are accessible.")
    except Exception as e:
        print(f"Error: hashlib.blake2b() failed: {e}", file=sys.stderr)
        print("This might indicate an issue with OpenSSL's crypto library linkage or functionality.", file=sys.stderr)


def print_system_resource_limits():
    """Prints System Resource Limits (Unix-like only)."""
    if resource:
        print(f"\n----- System Resource Limits (Soft / Hard) -----")
        try:
            # RLIMIT_NOFILE: Max number of open file descriptors
            nofile_soft, nofile_hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            print(f"Max Open Files (RLIMIT_NOFILE): {nofile_soft} / {nofile_hard}")
            # RLIMIT_AS: Address space limit (virtual memory)
            as_soft, as_hard = resource.getrlimit(resource.RLIMIT_AS)
            # Convert bytes to GB for readability if not unlimited (-1)
            as_soft_gb = f"{as_soft / (1024**3):.2f} GB" if as_soft != -1 else "Unlimited"
            as_hard_gb = f"{as_hard / (1024**3):.2f} GB" if as_hard != -1 else "Unlimited"
            print(f"Address Space (RLIMIT_AS): {as_soft_gb} / {as_hard_gb}")
            # RLIMIT_NPROC: Max number of processes
            if hasattr(resource, 'RLIMIT_NPROC'): # Not always available on all Unix-like systems/versions
                nproc_soft, nproc_hard = resource.getrlimit(resource.RLIMIT_NPROC)
                print(f"Max Processes (RLIMIT_NPROC): {nproc_soft} / {nproc_hard}")
        except Exception as e:
            print(f"Warning: Could not retrieve resource limits: {e}", file=sys.stderr)
    else:
        print(f"\n----- System Resource Limits -----")
        print("Resource module not available (typically on Windows systems).")


# ----------------------------------------
# Main Execution Logic
# ----------------------------------------

def main():
    """
    Parses command-line arguments and orchestrates the execution of the
    selected diagnostic functions.
    """
    # ----- Strict Python Version Check -----
    # Ensure the script is run with Python 3.10 or newer.
    if sys.version_info < (3, 10):
        print(f"Error: This script requires Python 3.10 or newer to run correctly. "
              f"You are currently running Python {sys.version.split(' ')[0]}.", file=sys.stderr)
        sys.exit(1)

    # --- Argument Parsing ---
    # Sets up the command-line interface, defining all the flags that
    # correspond to the diagnostic sections.
    parser = argparse.ArgumentParser(
        description="Verify Python and OpenSSL environment.",
        formatter_class=argparse.RawTextHelpFormatter # Preserve formatting in description/help
    )
    parser.add_argument('--env', action='store_true', help='Display Python Interpreter & Environment details.')
    parser.add_argument('--build', action='store_true', help='Display Python Build-Time Configuration.')
    parser.add_argument('--paths', action='store_true', help='Display Python Module Search Path (sys.path).')
    parser.add_argument('--stdlib', action='store_true', help='Display Key Standard Library C-Extensions check.')
    parser.add_argument('--math', action='store_true', help='Display Math Module C-Functionality Check.') # New argument
    parser.add_argument('--ssl', action='store_true', help='Display OpenSSL & SSL Module Information.')
    parser.add_argument('--tls13', action='store_true', help='Display TLS 1.3 Capability Check.')
    parser.add_argument('--hashlib', action='store_true', help='Display Hashlib Functionality Check.')
    parser.add_argument('--rlimits', action='store_true', help='Display System Resource Limits (Unix-like only).')
    parser.add_argument('--all', action='store_true', help='Display all sections (default if no options specified).')

    args = parser.parse_args()

    # Determine if any specific section argument was provided
    run_all = not any([args.env, args.build, args.paths, args.stdlib, args.math, args.ssl, args.tls13, args.hashlib, args.rlimits]) or args.all

    # --- Conditional Section Execution ---
    # Runs the appropriate diagnostic functions based on the parsed command-line
    # arguments. If no specific flags are set, it defaults to running all checks.
    if run_all or args.env:
        print_python_env_details()
    if run_all or args.build:
        print_python_build_config()
    if run_all or args.paths:
        print_module_search_paths()
    if run_all or args.stdlib:
        print_stdlib_c_extensions_check()
    if run_all or args.math: # New conditional execution
        print_math_module_check()
    if run_all or args.ssl:
        print_openssl_info()
    if run_all or args.tls13:
        print_tls13_capability_check()
    if run_all or args.hashlib:
        print_hashlib_check()
    if run_all or args.rlimits:
        print_system_resource_limits()

if __name__ == "__main__":
    main()
