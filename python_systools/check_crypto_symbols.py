#!/var/opt/python314/bin/python3.14
# ---------------------------------------------
# /var/opt/apps/system/check_crypto_symbols.py
# v1.0.0xg  2025/07/21  XdG / MIS Center
# ---------------------------------------------
# Requirements: Python 3.10 or newer.

import ctypes
import sys

# Define the full path to your custom libcrypto library
libcrypto_path = "/var/opt/openssl36/lib64/libcrypto36"

print("--- Checking for OpenSSL symbols ---")
print(f"Attempting to load library: {libcrypto_path}")

try:
    # Load the custom libcrypto library
    libcrypto = ctypes.CDLL(libcrypto_path)
    print("Library loaded successfully.")

    # Check for the blake2b symbol
    blake2b_symbol_name = "EVP_blake2b"
    blake2b512_symbol_name = "EVP_blake2b512"

    # Check for the symbol that Python's hashlib looks for
    if hasattr(libcrypto, blake2b_symbol_name):
        print(f"[PASS] Symbol '{blake2b_symbol_name}' found in the library.")
    else:
        print(f"[FAIL] Symbol '{blake2b_symbol_name}' not found in the library.")

    # Check for the specific symbol we found with `nm`
    if hasattr(libcrypto, blake2b512_symbol_name):
        print(f"[PASS] Symbol '{blake2b512_symbol_name}' found in the library.")
    else:
        print(f"[FAIL] Symbol '{blake2b512_symbol_name}' not found in the library.")

except OSError as e:
    print(f"[FAIL] Error loading library: {e}")
except Exception as e:
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
except Exception as e:
    print(f"[FAIL] An unexpected error occurred with hashlib: {e}")
