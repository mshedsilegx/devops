# Python System Diagnostics (`python_sysdiags.py`)

## 1. Application Overview and Objectives

The **Python System Diagnostics** script is a command-line tool designed to provide a comprehensive, detailed report on the Python interpreter's configuration and its interaction with the underlying system. Its primary objective is to help developers, system administrators, and security engineers quickly diagnose issues related to the Python build environment, library linkage (especially OpenSSL), and system capabilities.

The script is particularly useful for:
-   Verifying that a Python interpreter has been built with the expected capabilities (e.g., TLS 1.3 support).
-   Debugging issues related to missing C-extension modules.
-   Inspecting the Python module search path (`sys.path`).
-   Checking system resource limits that could impact application performance.
-   Auditing the versions of critical linked libraries like OpenSSL.

## 2. Architecture and Design Choices

The script is designed to be modular, clear, and easily extensible.

### Core Components

-   **Section-Based Functions:** The script is organized into a series of distinct functions, where each function is responsible for a specific diagnostic check (e.g., `print_python_env_details()`, `print_openssl_info()`, `print_system_resource_limits()`). This modular design makes the code easy to read, maintain, and test. It also allows new diagnostic checks to be added by simply creating a new function.

-   **`argparse` for Command-Line Control:** The script uses Python's built-in `argparse` module to handle command-line arguments. This provides a robust and user-friendly interface, allowing users to select which diagnostic sections they want to run. If no specific sections are requested, the script defaults to running all checks, providing a complete system overview.

-   **Platform-Aware Logic:** The script includes checks for platform-specific features. For example, the `resource` module for checking system limits is only imported on Unix-like systems, preventing `ImportError` exceptions on Windows and ensuring the script can run on multiple platforms.

-   **Strict Version Check:** The script includes a check to ensure it is run with Python 3.10 or newer. This is a deliberate design choice to guarantee the availability of modern `ssl` and `sysconfig` features that are critical for accurate diagnostics.

## 3. Command-Line Arguments

The script's behavior can be controlled via the following command-line arguments. If no arguments are provided, `--all` is assumed.

| Argument   | Description                                           |
| :--------- | :---------------------------------------------------- |
| `--env`      | Display Python Interpreter & Environment details.     |
| `--build`    | Display Python Build-Time Configuration.              |
| `--paths`    | Display Python Module Search Path (`sys.path`).       |
| `--stdlib`   | Display Key Standard Library C-Extensions check.      |
| `--math`     | Display Math Module C-Functionality Check.            |
| `--ssl`      | Display OpenSSL & SSL Module Information.             |
| `--tls13`    | Display TLS 1.3 Capability Check.                     |
| `--hashlib`  | Display Hashlib Functionality Check.                  |
| `--rlimits`  | Display System Resource Limits (Unix-like only).      |
| `--all`      | Display all sections (default if no options specified). |
| `-h`, `--help` | Show the help message and exit.                       |

## 4. Examples

### Example 1: Running a Full System Diagnostic

To run all checks and get a complete report, execute the script with no arguments or with the `--all` flag.

```bash
python python_systools/python_sysdiags.py
```
or
```bash
python python_systools/python_sysdiags.py --all
```

### Example 2: Checking Only SSL and TLS Capabilities

To investigate a specific area, such as the OpenSSL linkage and TLS 1.3 support, you can select just those sections.

```bash
python python_systools/python_sysdiags.py --ssl --tls13
```

### Example 3: Verifying Build Configuration and C-Extensions

To check how Python was compiled and verify that key C-extensions are available, use the `--build` and `--stdlib` flags.

```bash
python python_systools/python_sysdiags.py --build --stdlib
```

### Example 4: Viewing the Help Message

To see the list of all available commands and their descriptions, use the `-h` or `--help` flag.

```bash
python python_systools/python_sysdiags.py --help
```