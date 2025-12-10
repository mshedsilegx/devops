# Python Package Upgrader

## Application Overview and Objectives

The `python_pkg_upgrader.py` script is a command-line utility designed for system administrators and developers to manage Python packages. Its primary objectives are:

1.  **Inspection**: To provide a detailed, consolidated view of all installed Python packages, including their version, location, and type.
2.  **Maintenance**: To simplify the process of keeping Python environments up-to-date by providing a one-step command to upgrade all outdated packages.

The script is designed to be robust and informative, providing clear output in either a human-readable format or a machine-readable JSON format.

## Architecture and Design Choices

The script is designed with the following principles in mind:

*   **Modularity**: The script leverages a shared `python_pkg_utils.py` module for common functionalities like package metadata resolution. This promotes code reuse and consistency with other tools like `python_pkg_info.py`.
*   **Standard Tools**: It relies on standard Python libraries like `argparse`, `importlib.metadata`, and `subprocess` to ensure compatibility and avoid external dependencies. It uses `pip` for package management, which is the standard for the Python ecosystem.
*   **Safety**: The upgrade functionality includes a `--simulate` mode. This allows users to preview the changes that will be made without actually modifying the environment, preventing accidental or unwanted upgrades.
*   **Flexibility**: The script supports both human-readable and JSON output, making it suitable for both manual administration and automated scripting.

## Command Line Arguments

| Argument | Description | Type | Default |
| --- | --- | --- | --- |
| `--list` | Lists all installed Python packages with detailed metadata. | Flag | N/A |
| `--upgrade` | Upgrades all outdated Python packages. | Flag | N/A |
| `--simulate` | Simulates the upgrade process without making changes. Only works with `--upgrade`. | Flag | N/A |
| `--json` | Outputs the results in JSON format. Works with `--list` or `--upgrade --simulate`. | Flag | N/A |
| `--target <path>` | Specifies a custom installation directory for upgrades. Useful for environments with split library paths. Only works with `--upgrade`. | String | None |

## Handling Custom Environments

In environments where packages are split across multiple directories (e.g., a custom `PYTHONPATH` that takes precedence over standard `site-packages`), standard `pip install --upgrade` might install the new version into the default location, leaving the old version active in the custom path (package shadowing).

To prevent this, use the `--target` flag to force the upgrade into the correct directory:

```bash
# Force upgrades into the custom module directory
python python_pkg_upgrader.py --upgrade --target /path/to/custom/library
```

**Note**: `--list` and `--upgrade` are mutually exclusive.

## Examples

### 1. List all installed packages in a human-readable format

```bash
python3 python_pkg_upgrader.py --list
```

**Example Output:**

```
Package                        Version         Location    Type               Path
=======================================================================================
certifi                        2023.7.22       system      wheel(purelib)     /usr/lib/python3.10/site-packages
charset-normalizer             3.3.0           system      wheel(purelib)     /usr/lib/python3.10/site-packages
idna                           3.4             system      wheel(purelib)     /usr/lib/python3.10/site-packages
requests                       2.31.0          system      wheel(purelib)     /usr/lib/python3.10/site-packages
urllib3                        2.0.7           system      wheel(purelib)     /usr/lib/python3.10/site-packages
```

### 2. List all installed packages in JSON format

```bash
python3 python_pkg_upgrader.py --list --json
```

### 3. Simulate an upgrade to see outdated packages

```bash
python3 python_pkg_upgrader.py --upgrade --simulate
```

**Example Output:**

```
Module                         Old Version     New Version
============================================================
some-package                   1.0.0           1.1.0
another-package                2.1.5           2.2.0
```

### 4. Simulate an upgrade and output in JSON format

```bash
python3 python_pkg_upgrader.py --upgrade --simulate --json
```

### 5. Upgrade all outdated packages

```bash
python3 python_pkg_upgrader.py --upgrade
```

**Example Output:**
```
Upgrading 2 packages...
Collecting some-package
  Downloading some-package-1.1.0-py3-none-any.whl (1.1 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 1.1 MB/s eta 0:00:00
Collecting another-package
  Downloading another-package-2.2.0-py3-none-any.whl (2.2 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.2/2.2 MB 2.2 MB/s eta 0:00:00
Installing collected packages: some-package, another-package
  Attempting uninstall: some-package
    Found existing installation: some-package 1.0.0
    Uninstalling some-package-1.0.0:
      Successfully uninstalled some-package-1.0.0
  Attempting uninstall: another-package
    Found existing installation: another-package 2.1.5
    Uninstalling another-package-2.1.5:
      Successfully uninstalled another-package-2.1.5
Successfully installed some-package-1.1.0 another-package-2.2.0

Successfully upgraded all packages.
```
