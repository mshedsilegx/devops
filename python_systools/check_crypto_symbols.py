#!/var/opt/python314/bin/python3.14
# ---------------------------------------------
# /var/opt/apps/system/check_crypto_symbols.py
# v1.0.0xg  2025/07/21  XdG / MIS Center
# ---------------------------------------------
# Requirements: Python 3.10 or newer.

"""
Script to check for specific OpenSSL symbols in a custom libcrypto library
and verify hashlib functionality.
"""

import ctypes

# Define the full path to your custom libcrypto library
LIBCRYPTO_PATH = "/var/opt/openssl36/lib64/libcrypto36"

print("--- Checking for OpenSSL symbols ---")
print(f"Attempting to load library: {LIBCRYPTO_PATH}")

try:
    # Load the custom libcrypto library
    libcrypto = ctypes.CDLL(LIBCRYPTO_PATH)
    print("Library loaded successfully.")

    # Check for the blake2b symbol
    BLAKE2B_SYMBOL_NAME = "EVP_blake2b"
    BLAKE2B512_SYMBOL_NAME = "EVP_blake2b512"

    # Check for the symbol that Python's hashlib looks for
    if hasattr(libcrypto, BLAKE2B_SYMBOL_NAME):
        print(f"[PASS] Symbol '{BLAKE2B_SYMBOL_NAME}' found in the library.")
    else:
        print(f"[FAIL] Symbol '{BLAKE2B_SYMBOL_NAME}' not found in the library.")

    # Check for the specific symbol we found with `nm`
    if hasattr(libcrypto, BLAKE2B512_SYMBOL_NAME):
        print(f"[PASS] Symbol '{BLAKE2B512_SYMBOL_NAME}' found in the library.")
    else:
        print(f"[FAIL] Symbol '{BLAKE2B512_SYMBOL_NAME}' not found in the library.")

except OSError as e:
    print(f"[FAIL] Error loading library: {e}")
except Exception as e:  # pylint: disable=broad-exception-caught
    print(f"[FAIL] An unexpected error occurred: {e}")

# This part will attempt to import and use hashlib, which is expected to fail
print("\n--- Checking hashlib behavior ---")
try:
    import hashlib
    print("hashlib module loaded successfully.")

    # This line is expected to fail in your current state
    hashlib.blake2b(b"test")
    print("[PASS] hashlib.blake2b() call succeeded.")

except AttributeError:
    print("[FAIL] AttributeError: hashlib.blake2b() failed. This is expected.")
except ValueError as e:
    print(f"[FAIL] ValueError: {e}. This is also expected.")
except Exception as e:  # pylint: disable=broad-exception-caught
    print(f"[FAIL] An unexpected error occurred with hashlib: {e}")
