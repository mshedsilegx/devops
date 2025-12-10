# Python Package Inspector (`python_pkg_info.py`)

## 1. Application Overview and Objectives

The `python_pkg_info.py` script is a command-line utility designed to provide detailed, accurate, and reliable information about installed Python packages. Its primary objective is to resolve the exact on-disk installation path of a Python module, which can often be ambiguous, and to gather comprehensive metadata related to it.

This tool is essential for developers, system administrators, and automated scripts that need to:
- **Verify Package Installations:** Confirm that a package is installed and determine its exact location.
- **Debug Dependency Issues:** Understand a package's dependencies, version, and Python version requirements.
- **Automate Environment Analysis:** Integrate the tool into larger scripts (e.g., via JSON output) to programmatically inspect a Python environment.
- **Gather Licensing and Author Information:** Quickly retrieve metadata for compliance or reporting purposes.

The script is designed to be a definitive source of truth, overcoming the limitations and inconsistencies of other tools by using Python's own import machinery for path resolution.

## 2. Architecture and Design Choices

The script's architecture is centered around a modular, function-based design that prioritizes accuracy and reliability.

### Core Components:

1.  **`resolve_package_metadata(package_name)`**: This is the central function of the script. It orchestrates the entire data-gathering process.
    -   **Metadata First:** It begins by using `importlib.metadata` to retrieve the core distribution information. This is the standard and most reliable way to access package metadata in modern Python (3.8+).
    -   **Definitive Path Resolution Logic:** The most critical design choice is the multi-step process for resolving the package's installation path, which avoids unreliable methods.
        1.  **`top_level.txt` Analysis & Heuristics:** It first reads the `top_level.txt` file to find the importable module name. It then applies heuristic refinement to ensure the name is user-facing (e.g., handling cases where the internal module starts with `_` or is empty).
        2.  **Calculated Root Path:** The script calculates the installation root directory by locating the `.dist-info` folder and moving up one level. This is more reliable than trusting the `dist.location` attribute, which can be inconsistent.
        3.  **Constructed Path:** It attempts to construct the final path by combining the calculated root with the top-level module name. This works for the majority of standard packages.
        4.  **`importlib.util.find_spec` Fallback:** If the constructed path does not exist, it falls back to `importlib.util.find_spec()`. This leverages Python's import system directly to find the module, crucial for namespace packages and editable installs.
        5.  **Single-File Module Safety Net:** As a final resort for single-file modules (e.g., `pyodbc`), it attempts to locate the specific entry point file directly within the distribution files if directory-based lookups fail.
2.  **`get_latest_version_from_pypi(package_name)`**: This function handles external data fetching.
    -   **Network Resilience:** It uses the `requests` library to query the official PyPI JSON API. To prevent the script from failing if `requests` is not installed, it includes a `DummyRequests` class. This ensures the script can still provide local metadata even without network access, returning a clear error message for the "latest version" field.
3.  **`get_module_type(dist)`**: A helper function that inspects a package's file manifest to determine if it contains binary/compiled files (`.so`, `.pyd`). This categorizes the package as either `platlib` (platform-specific) or `purelib` (pure Python).
4.  **`main()` and `display_results()`**: These functions manage the command-line interface.
    -   **`argparse` for CLI:** The script uses the standard `argparse` module for robust and user-friendly command-line argument parsing.
    -   **Separation of Logic and Presentation:** The core logic in `resolve_package_metadata` returns a structured dictionary. The `display_results` function is solely responsible for formatting this data, either as human-readable text or as a JSON string. This separation makes the core logic reusable and easier to test.

### Key Design Principles:
- **Accuracy over Simplicity:** The path resolution logic is intentionally complex to handle edge cases correctly.
- **Resilience:** The script is designed to function without network access and provides clear error messages.
- **Usability:** It offers multiple output formats (`text`, `json`) and verbosity levels (`--quiet`, `--verbose`) to suit different use cases.
- **Standard Library First:** It relies heavily on modern, standard library modules like `importlib.metadata`, `pathlib`, and `argparse`.

## 3. Command-Line Arguments

The script's behavior is controlled through the following command-line arguments.

| Argument      | Type    | Default | Description                                                                                              |
| :------------ | :------ | :------ | :------------------------------------------------------------------------------------------------------- |
| `--package`   | String  |         | **Required.** The name of the package to inspect (e.g., `requests`, `numpy`, `snowflake-connector-python`). |
| `--json`      | Flag    | `False` | If present, outputs all metadata in a structured JSON format, suitable for machine parsing.              |
| `--quiet`     | Flag    | `False` | Suppresses headers and separators in the default text output for a more concise result.                  |
| `--verbose`   | Flag    | `False` | Includes additional details in the output, such as dependencies, author, license, and summary.           |
| `--debug`     | Flag    | `False` | Enables detailed, step-by-step diagnostic output for the path resolution logic.                          |

## 4. Examples on How to Use

### Basic Usage
To get the primary information for a package like `numpy`.

**Command:**
```sh
python3 python_pkg_info.py --package numpy
```

**Example Output:**
```
Searching for: numpy

--- Package Metadata ---
Found Package:   numpy
Import Name:     numpy
Exact Path:      /usr/lib/python3/dist-packages/numpy
---
Current Version: 1.21.5
Latest Version:  1.26.4
Module Type:     platlib (Binary/Compiled C/C++)
```

### Getting Verbose Information
To see all available metadata, including dependencies and licensing, for the `requests` package.

**Command:**
```sh
python3 python_pkg_info.py --package requests --verbose
```
**Example Output:**
```
Searching for: requests

--- Package Metadata ---
Found Package:   requests
Import Name:     requests
Exact Path:      /home/user/.local/lib/python3.10/site-packages/requests
---
Current Version: 2.31.0
Latest Version:  2.32.3
Module Type:     purelib (Pure Python code)

--- Dependencies & Licensing ---
Summary:         Python HTTP for Humans.
License:         Apache 2.0
Author:          Kenneth Reitz
Homepage URL:    https://requests.readthedocs.io
Python Requires: >=3.7
Dependencies:
    charset-normalizer<4,>=2
    idna<4,>=2.5
    urllib3<3,>=1.21.1
    certifi>=2017.4.17
```

### JSON Output for Automation
To get the output in a machine-readable JSON format. This is ideal for use in other scripts.

**Command:**
```sh
python3 python_pkg_info.py --package cffi --json
```

**Example JSON Output:**
```json
{
    "package_name": "cffi",
    "import_name": "cffi",
    "exact_path": "/usr/lib/python3/dist-packages/cffi",
    "current_version": "1.15.1",
    "latest_version": "1.16.0",
    "module_type": "platlib (Binary/Compiled C/C++)",
    "metadata_summary": "Foreign Function Interface for Python calling C code.",
    "required_python_version": ">=3.6",
    "license": "MIT",
    "author": "Armin Rigo, Maciej Fijalkowski",
    "homepage": "https://cffi.readthedocs.io",
    "required_dependencies": [
        "pycparser"
    ]
}
```

### Quiet Output
For a minimal, clean output that is easy to parse in a shell script.

**Command:**
```sh
python3 python_pkg_info.py --package urllib3 --quiet
```

**Example Output:**
```
Found Package:   urllib3
Import Name:     urllib3
Exact Path:      /usr/lib/python3/dist-packages/urllib3
Current Version: 1.26.5
Latest Version:  2.2.2
Module Type:     purelib (Pure Python code)
```

### Debugging a Path Resolution
If a package path is not being resolved as expected, the `--debug` flag provides insight into the internal logic.

**Command:**
```sh
python3 python_pkg_info.py --package snowflake-connector-python --debug
```
**Example Debug Output:**
```
Searching for: snowflake-connector-python

--- DEBUG: Path Resolution Start ---
DEBUG 1: Top-Level Module (TML): snowflake
DEBUG 1: Distribution Root (Calculated): /home/user/.local/lib/python3.10/site-packages
DEBUG 2: Constructed Module Path: /home/user/.local/lib/python3.10/site-packages/snowflake
DEBUG 2: Constructed Path Exists?: True
DEBUG FINAL: Resolved Path Before Return: /home/user/.local/lib/python3.10/site-packages/snowflake
--- DEBUG: Path Resolution End ---

--- Package Metadata ---
Found Package:   snowflake-connector-python
Import Name:     snowflake
Exact Path:      /home/user/.local/lib/python3.10/site-packages/snowflake
---
Current Version: 3.8.0
Latest Version:  3.9.0
Module Type:     purelib (Pure Python code)
```
