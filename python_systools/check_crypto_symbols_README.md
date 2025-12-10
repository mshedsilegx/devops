# Check Crypto Symbols

## Application Overview and Objectives

`check_crypto_symbols.py` is a specialized diagnostic utility designed to verify the presence of specific OpenSSL symbols within a custom `libcrypto` shared library. Its primary objective is to debug and validate the cryptographic capabilities of a Python environment, specifically focusing on the **BLAKE2b** hashing algorithm.

The tool addresses scenarios where custom OpenSSL builds are used and there is a need to confirm:
1.  Whether the `libcrypto` library properly exports the expected symbols (`EVP_blake2b` or `EVP_blake2b512`).
2.  How the Python `hashlib` module behaves when attempting to use the BLAKE2b algorithm in the current environment.

This is particularly useful for DevOps and System Administrators troubleshooting issues with Python's hashlib support on custom Linux distributions or environments with non-standard OpenSSL paths.

## Architecture and Design Choices

The script is built with a linear, procedural architecture focused on direct system introspection. Key design choices include:

*   **Low-Level Introspection via `ctypes`**: Instead of relying solely on high-level Python wrappers, the script uses `ctypes` to dynamically load the shared object (`.so`) file. This allows for a raw check of the symbol table, independent of Python's internal linking.
*   **Dual-Layer Verification**:
    *   *Layer 1 (Symbol Level)*: Direct check for exported C functions (`EVP_blake2b`, `EVP_blake2b512`) in the library.
    *   *Layer 2 (Application Level)*: Functional test using Python's `hashlib` to see if the high-level API can successfully bridge to the underlying implementation.
*   **Strict Environment Enforcement**: The script explicitly enforces a minimum Python version (3.10+) to ensure consistency with the environment where these issues are typically debugged.
*   **Resilient Error Handling**: The script uses comprehensive `try...except` blocks to handle loading failures (e.g., missing files, wrong permissions) and runtime errors during hash computation, ensuring the tool reports failure reasons without crashing.

## Command Line Arguments

The script utilizes `argparse` for robust argument handling.

| Argument | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `libcrypto_path` | String | Yes | N/A | The full absolute path to the custom `libcrypto` shared library file (e.g., `/var/opt/openssl36/lib64/libcrypto36`). |
| `--json` | Flag | No | False | Output results in JSON format instead of plain text. |

## Examples on How to Use

### Basic Usage
Run the script by providing the full path to your target `libcrypto` library:

```bash
python3 check_crypto_symbols.py /var/opt/openssl36/lib64/libcrypto36
```

### Expected Output (Success Scenario)
If the library is found and symbols are present:

```text
Python Linked OpenSSL: OpenSSL 3.0.8 7 Feb 2023

--- Checking for OpenSSL symbols ---
Attempting to load library: /var/opt/openssl36/lib64/libcrypto36
Library loaded successfully.
Detected Library Version: OpenSSL 3.0.8 7 Feb 2023
[PASS] Symbol 'EVP_blake2b' found in the library.
[PASS] Symbol 'EVP_blake2b512' found in the library.

--- Checking hashlib behavior ---
hashlib module loaded successfully.
[PASS] hashlib.blake2b() call succeeded.

All checks PASSED.
```

### Expected Output (Failure/Debug Scenario)
If the library is missing the standard symbol or hashlib fails (common in broken builds):

```text
Python Linked OpenSSL: OpenSSL 1.1.1k  25 Mar 2021

--- Checking for OpenSSL symbols ---
Attempting to load library: /usr/lib64/libcrypto.so.1.1
Library loaded successfully.
Detected Library Version: OpenSSL 1.1.1k  25 Mar 2021
[FAIL] Symbol 'EVP_blake2b' not found in the library.
[PASS] Symbol 'EVP_blake2b512' found in the library.

--- Checking hashlib behavior ---
hashlib module loaded successfully.
[FAIL] ValueError: [digital envelope routines] unsupported. This is also expected.

Some checks FAILED.
```

### Getting Help
To view the help message and available arguments:

```bash
python3 check_crypto_symbols.py --help
```
