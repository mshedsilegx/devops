# Python System Diagnostics (`python_sysdiags.py`)

## 1. Application Overview and Objectives

The **Python System Diagnostics** script is a command-line tool designed to provide a comprehensive, detailed report on the Python interpreter's configuration and its interaction with the underlying system. Its primary objective is to help developers, system administrators, and security engineers quickly diagnose issues related to the Python build environment, library linkage (especially OpenSSL), and system capabilities.

The script can produce output in either a human-readable text format or a machine-readable JSON format, making it suitable for both interactive use and automated CI/CD pipelines.

## 2. Architecture and Design Choices

The script is designed with a focus on **modularity**, **separation of concerns**, and **extensibility**.

### Core Components

-   **`SystemDiagnostics` Class:** This class is the heart of the script, encapsulating all data-gathering logic. Each diagnostic check is implemented as a separate method (e.g., `get_python_env_details()`, `get_openssl_info()`) that returns a structured dictionary of data. This design isolates the data collection from the presentation.

-   **Separation of Concerns (Data vs. Presentation):** The script strictly separates the process of gathering data from displaying it. The `SystemDiagnostics` class only collects data. The `main` function then passes this data to one of two presentation functions:
    -   `print_text_report()`: Renders the data in a human-readable text format.
    -   `print_json_report()`: Renders the data as a single, structured JSON object.
    This architecture makes it easy to add new output formats (e.g., HTML, CSV) in the future without modifying the core data-gathering logic.

-   **Dispatch Table for Command-Line Control:** Instead of a long chain of `if` statements, the `main` function uses a dispatch table (a dictionary) to map command-line arguments (e.g., `--env`) to the corresponding methods in the `SystemDiagnostics` class. This makes the code cleaner, more efficient, and easier to extend with new diagnostic checks.

-   **Platform-Aware and Version-Safe:** The script safely handles platform-specific features (like the `resource` module on Unix) and includes a version check to ensure it runs on a compatible Python version (3.10+), which guarantees the availability of necessary features.

## 3. Command-Line Arguments

The script's behavior can be controlled via the following command-line arguments. If no specific check is requested, `--all` is assumed.

| Argument   | Description                                           |
| :--------- | :---------------------------------------------------- |
| `--json`     | Output results in JSON format instead of text.        |
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

### Example 1: Running a Full System Diagnostic (Human-Readable)

To get a complete report in the default text format, run the script with no arguments.

```bash
python python_systools/python_sysdiags.py
```

### Example 2: Getting a Full Report in JSON Format

To get all diagnostic data in a structured JSON format, use the `--json` flag. This is ideal for automation.

```bash
python python_systools/python_sysdiags.py --json
```
```json
{
  "env": {
    "executable": "/usr/bin/python3",
    "version": "3.10.12 ...",
    "...": "..."
  },
  "build": {
    "...": "..."
  }
}
```

### Example 3: Checking Specific Sections in JSON

You can combine the `--json` flag with any specific check to get a targeted JSON output.

```bash
python python_systools/python_sysdiags.py --ssl --tls13 --json
```
```json
{
  "ssl": {
    "openssl_version": "OpenSSL 3.0.2 15 Mar 2022",
    "...": "..."
  },
  "tls13": {
    "status": "OK",
    "details": "SSLContext created with minimum TLS 1.3 version."
  }
}
```