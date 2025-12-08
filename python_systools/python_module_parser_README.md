# Python Module Parser (`python_module_parser.py`)

## 1. Application Overview and Objectives

The `python_module_parser.py` script is a command-line utility designed to analyze a directory of Python source code and identify all its external (third-party) dependencies. Its primary objective is to provide a clear and accurate list of non-standard-library modules that a project relies on.

This tool is particularly useful for:
- **Dependency Auditing:** Quickly understanding all third-party libraries used in a project.
- **Requirements Generation:** Assisting in the creation of `requirements.txt` files for project setup.
- **Codebase Analysis:** Gaining insights into the dependencies of an unfamiliar Python project.

The script scans all `.py` files within a specified directory, parses them to find import statements, filters out Python's standard library modules, and then attempts to determine the version of each external module found.

## 2. Architecture and Design Choices

The script is designed with safety, accuracy, and readability in mind. Key architectural choices include:

- **Abstract Syntax Tree (AST) Parsing:** The script uses Python's native `ast` module to parse source code. This approach is highly effective and secure, as it allows the script to analyze the code's structure without executing it, thus avoiding any potential side effects that could arise from direct module importation.
- **Standard Library Exclusion:** To differentiate between standard and third-party modules, the script leverages `sys.stdlib_module_names`, a feature available in Python 3.10 and newer. This provides a reliable and up-to-date list of standard library modules to exclude from the dependency analysis.
- **Robust Version Discovery:** The script employs a two-step process to find the version of each identified module:
    1.  **`importlib.metadata.version`**: This is the preferred method, as it retrieves version information from package metadata without needing to import the module itself.
    2.  **`__version__` attribute**: As a fallback, if the first method fails, the script will import the module and check for a `__version__` attribute.
- **Recursive File Discovery:** The use of `os.walk` ensures that the script performs a comprehensive scan, traversing the entire directory tree to find all `.py` files.
- **Structured Output:** The script generates two distinct, easy-to-read reports:
    - A summary list of all unique external modules with their versions.
    - A detailed, file-by-file breakdown of dependencies.

## 3. Command Line Arguments

The script requires a single command-line argument:

| Argument                  | Description                                       | Type   | Default |
| ------------------------- | ------------------------------------------------- | ------ | ------- |
| `<directory_to_scan>`     | The path to the directory you wish to scan for    | string | N/A     |
|                           | Python files. This argument is **required**.      |        |         |

## 4. Examples on How to Use

Here are a few examples of how to run the script from your terminal:

### Example 1: Scan a Specific Project Directory

To scan a project located at `/path/to/my_project`, you would run:
```bash
python3 python_module_parser.py /path/to/my_project
```

### Example 2: Scan the Current Directory

To scan the directory you are currently in, use `.` as the path:
```bash
python3 python_module_parser.py .
```

### Sample Output

When you run the script, the output will look something like this:

```
Scanning 42 Python files in '/path/to/my_project'...

--- Summary of All Unique Top-Level External/Third-Party Modules (with versions) ---
numpy==1.23.5
pandas==1.5.3
requests==2.28.1
scipy==N/A

--- File-by-File External/Third-Party Dependencies (with versions) ---

/path/to/my_project/data_analysis/core.py:
  - numpy==1.23.5
  - pandas==1.5.3

/path/to/my_project/data_analysis/special_tools.py:
  - numpy==1.23.5
  - scipy==N/A

/path/to/my_project/utils/api_client.py:
  - requests==2.28.1
```
