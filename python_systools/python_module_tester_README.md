# Python Module Tester

## 1. Application Overview and Objectives

The **Python Module Tester** is a command-line utility designed to perform a comprehensive "health check" on any installed Python module. Its primary objective is to provide developers and system administrators with a quick, detailed, and consistent way to assess a module's quality, structure, and basic performance characteristics without needing to dive deep into its source code.

The script runs a suite of 13 generic soundness checks, a performance test, and an environment check to generate a structured report covering:
-   Code structure and best practices (docstrings, versioning, API definition).
-   Code quality and encapsulation.
-   Metadata completeness (license, dependencies).
-   Import performance and potential bottlenecks.
-   The Python environment in which the test is run.

## 2. Architecture and Design Choices

The script is designed with a focus on **modularity** and **separation of concerns** to ensure it is maintainable and extensible.

### Core Components

-   **`ModuleAnalysis` Class:** This class is the heart of the script. It encapsulates all the data gathering and analysis logic. When instantiated with a module name, it imports the module, records performance metrics, and gathers all necessary information (e.g., members, metadata) for the checks. Each of the 13 soundness checks is implemented as a separate method within this class (e.g., `analyze_docstring()`, `analyze_version()`), ensuring that each check is a single, testable unit.

-   **Presentation Functions:** The script separates the *analysis* from the *presentation*. After the `ModuleAnalysis` class has run all its checks and collected the results, it passes them to a set of dedicated printing functions:
    -   `print_report()`: Formats and displays the main report for the 13 soundness checks.
    -   `print_performance_check()`: Displays the import performance results.
    -   `print_environment_check()`: Displays details about the Python environment.
    This separation makes it easy to change the output format without altering the underlying analysis logic. For example, the output could be changed to JSON or HTML by simply writing a new print function.

-   **`print_methodology_doc()`:** This standalone function prints the detailed methodology documentation and exits. It is kept separate to provide clear, on-demand help to the user without executing any analysis.

## 3. Command-Line Arguments

The script accepts the following command-line arguments:

| Argument               | Type   | Description                                                                                                                                |
| ---------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `module_name`          | string | **(Required)** The name of the Python module to be tested (e.g., `requests`, `numpy`, `pandas`). The script will attempt to import this module. |
| `--checks-methodology` | flag   | **(Optional)** If provided, the script will display a detailed explanation of all checks and their rating criteria, and then exit.       |

## 4. Examples

### Example 1: Running a Standard Check

To run a soundness check on a module (e.g., `requests`), provide its name as an argument.

```bash
python python_systools/python_module_tester.py requests
```

This will produce a full report, including the generic soundness checks, performance, and environment details.

### Example 2: Viewing the Checks Methodology

To view the detailed documentation for all the checks, use the `--checks-methodology` flag.

```bash
python python_systools/python_module_tester.py --checks-methodology
```

This will print the help text and exit without performing any analysis.

## 5. Checks Methodology

This section details the checks performed by the script to assess a module's soundness.

### Status Tags

The script uses the following status tags to summarize the outcome of each check:

| Status Tag | Meaning                                                                              |
| :--------- | :----------------------------------------------------------------------------------- |
| `[PASS]`   | The check met a quality standard or represents a desirable state.                    |
| `[WARN]`   | A potential issue was found that should be reviewed (e.g., a missing best practice). |
| `[INFO]`   | Provides neutral, contextual information about the module (e.g., dependencies).      |
| `[FAIL]`   | A critical failure occurred, such as the module failing to import.                   |
| `[OK]`     | The module was imported successfully.                                                |

### I. Generic Soundness Checks

These checks evaluate the module's structure, documentation, and adherence to common Python best practices.

| #  | Check                           | Purpose                                                                                | Criteria for `[PASS]`, `[WARN]`, `[INFO]`                                                                                                                                                            |
| :- | :------------------------------ | :------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | **File/Package Location**       | Identifies where the module's source code is located on the filesystem.                | **`[PASS]`**: The file or package path was successfully found.<br>**`[INFO]`**: The module is built-in or a C-extension with no visible path.                                                       |
| 2  | **Implementation Language**     | Determines if the module is written in Python, C, or a mix.                            | **`[PASS]`**: The language type (Pure Python, C-Extension, or Mixed) was identified.<br>**`[INFO]`**: The language type is unknown.                                                                 |
| 3  | **Documentation String**        | Checks for a descriptive `__doc__` string at the top of the module.                      | **`[PASS]`**: A docstring with a length > 10 characters was found.<br>**`[WARN]`**: The docstring is missing or too short.                                                                          |
| 4  | **Version Information**         | Checks for a `__version__` attribute for package versioning.                           | **`[PASS]`**: The `__version__` attribute was found.<br>**`[WARN]`**: The module does not define a `__version__`.                                                                                   |
| 5  | **Public API Definition**       | Checks for an `__all__` list, which explicitly defines the module's public API.          | **`[PASS]`**: `__all__` is present and non-empty.<br>**`[WARN]`**: `__all__` is defined but empty or invalid.<br>**`[INFO]`**: `__all__` is not defined (using default namespace).                      |
| 6  | **Encapsulation**               | Assesses the balance between public and private members.                               | **`[PASS]`**: Private member ratio is < 70% or there are >= 5 public members.<br>**`[WARN]`**: Private ratio is > 70% and public members are < 5.<br>**`[INFO]`**: The module namespace is empty.      |
| 7  | **API Surface Size**            | Checks if the module exposes an excessively large number of public members.              | **`[PASS]`**: The number of public members is <= 150.<br>**`[WARN]`**: The API is excessively large (> 150 members).                                                                               |
| 8  | **Callable Object Count**       | Ensures the module provides usable functionality (functions or classes).                 | **`[PASS]`**: At least one public function or class was found.<br>**`[INFO]`**: No top-level public functions or classes were found.                                                                |
| 9  | **Import Health**               | Captures any warnings (e.g., `DeprecationWarning`) that occur during import.             | **`[PASS]`**: The module imported cleanly with no warnings.<br>**`[WARN]`**: One or more unique warnings were detected.                                                                          |
| 10 | **Type Hint Coverage**          | Measures the percentage of public callables that have type annotations.                  | **`[PASS]`**: Excellent coverage (>= 75%).<br>**`[WARN]`**: Moderate coverage (>= 30% but < 75%).<br>**`[INFO]`**: Low coverage (< 30%) or no callables to check.                                    |
| 11 | **Metadata Status**             | Checks if the module is part of a distributed package with metadata.                     | **`[PASS]`**: Package metadata (name and version) was found.<br>**`[WARN]`**: Metadata was not found or is incomplete.                                                                           |
| 12 | **License Status**              | Checks for license information within the package metadata.                              | **`[PASS]`**: A license was detected.<br>**`[WARN]`**: The 'License' field is missing.<br>**`[INFO]`**: Could not retrieve package metadata.                                                        |
| 13 | **Dependencies**                | Lists the external packages required by this module.                                   | **`[PASS]`**: No external dependencies are listed.<br>**`[INFO]`**: External dependencies were found and are listed in the report.                                                                    |

### II. Performance & Environment Checks

These checks measure the module's import time and report details about the execution environment.

| Check                | Purpose                                                                    | Criteria for `[PASS]`, `[WARN]`, `[INFO]`                                                                                                                                                              |
| :------------------- | :------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Import Performance** | Measures the time it takes to import the module.                           | **`[PASS]`**: Excellent performance (< 0.1 seconds).<br>**`[INFO]`**: Acceptable performance (0.1 to 1.0 seconds).<br>**`[WARN]`**: Slow performance (> 1.0 seconds), indicating a potential bottleneck. |
| **Environment Check**  | Reports key details about the Python interpreter running the check.        | **`[INFO]`**: Reports the Python version, threading model (GIL status), and implementation (e.g., CPython).                                                                                            |
This will print the help text and exit without performing any analysis.
