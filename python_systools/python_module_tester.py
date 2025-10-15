#!/var/opt/python314/bin/python3.14
# ----------------------------------------------
# /var/opt/apps/system/python_module_tester.py
# v1.0.0xg  2025/10/14  XdG / MIS Center
# ----------------------------------------------

# -*- coding: utf-8 -*-
# This script defines a function to test the load status and generic soundness of a Python module.

import sys
import argparse
import inspect
import warnings
import time
from typing import Optional, List, Dict, Any
import importlib.metadata
import importlib.util
import importlib
import re
import os

def print_methodology_doc():
    """Prints the comprehensive documentation for the soundness checks and rating systems."""
    # Using r""" for a raw string literal to prevent SyntaxWarning
    # about invalid escape sequences like "\l" in the LaTeX math symbols ($\le, \gt$).
    doc = r"""
========================================
MODULE SOUNDNESS CHECK METHODOLOGY
========================================

The script uses four main status tags to quickly summarize the module's health
across several dimensions: [PASS], [WARN], [INFO], and [FAIL].

| Status Tag | Meaning |
| :--- | :--- |
| [PASS] | The check passed the quality standard or represents a desirable state. |
| [WARN] | A potential issue was found that you should review (e.g., missing best practice). |
| [INFO] | A neutral finding, providing context about the module's nature (e.g., built-in, dependencies). |
| [FAIL]/[OK] | Used for the global import status (OK for success, FAIL for import failure). |

---
EXPLANATIONS FOR GENERIC SOUNDNESS CHECKS (1-13)
---
| Check | What It Measures | [PASS] Criteria | [WARN] Criteria | [INFO] Criteria |
| :--- | :--- | :--- | :--- | :--- |
| 1. File/Package Location | Where the module resides. | File or package path found. | N/A | Built-in or C-Extension. |
| 2. Language Type | Pure Python, C-Extension, or Mixed. | Specific type (Pure, C, or Mixed) identified. | N/A | Built-in or Unknown. |
| 3. Documentation String | Presence of top-level `__doc__`. | Docstring found (length > 10). | Docstring missing or too short. | N/A |
| 4. Version Information | Presence of top-level `__version__`. | `__version__` attribute found. | `__version__` is missing. | N/A |
| 5. Public API (`__all__`) | Explicit control over the public interface. | `__all__` list is present and non-empty. | `__all__` is defined but empty or invalid. | `__all__` is not defined (default namespace). |
| 6. Encapsulation | Balance of private vs. public members. | Private member ratio is **reasonable** (< 70% or >= 5 public members). | Private ratio **> 70%** AND public members **< 5**. | Module namespace is empty. |
| 7. API Surface Size | Whether the public API exposes too many members. | Public members $\le 150$. | Public members $\gt 150$ (Excessive size). | N/A |
| 8. Callable Object Count | Existence of functions or classes in the public API. | At least one public function or class found. | N/A | No top-level public functions or classes found. |
| 9. Import Health | Warnings caught during import (e.g., DeprecationWarning). | No warnings or deprecations detected. | One or more unique warnings detected. | N/A |
| 10. Type Hint Coverage | Proportion of public callables with type hints. | **Excellent** ($\ge 75\%$ coverage). | **Moderate** ($\ge 30\%$ but $< 75\%$ coverage). | **Low** ($< 30\%$ coverage) or no callables to check. |
| 11. Metadata Status | Package information via `importlib.metadata`. | Name and Version metadata found. | Metadata missing or incomplete. | N/A |
| 12. License Status | License information in package metadata. | License information detected. | 'License' field missing in metadata. | Could not retrieve package metadata. |
| 13. Dependencies | External packages required by the module. | No external package dependencies listed. | N/A | External dependencies found and listed. |

---
PERFORMANCE AND ENVIRONMENT CHECKS
---
| Check | What It Measures | [PASS] Criteria | [INFO] Criteria | [WARN] Criteria |
| :--- | :--- | :--- | :--- | :--- |
| Import Performance | Time to load the module (in seconds). | **Excellent** ($< 0.1$ s). | **Acceptable** ($0.1$ s to $1.0$ s). | **Slow** ($> 1.0$ s - Potential bottleneck). |
| Environment Check | Python version and interpreter details. | N/A | Reports Version, Threading Model, and Implementation. | Failed to retrieve details. |
"""
    print(doc)
    sys.exit(0)

def check_module_loads(module_name: str) -> bool:
    """
    Attempts to import a module and performs comprehensive generic soundness checks
    and presents the results in a structured format.
    """
    print(f"Testing import of '{module_name}'...")
    
    start_time = time.perf_counter()
    
    try:
        captured_warnings = []
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            module_object = importlib.import_module(module_name)
            captured_warnings = list(w)
        
        import_duration = time.perf_counter() - start_time

        print(f"[OK] SUCCESS: Module '{module_name}' imported correctly.")

        # List to store results for the final output
        results = []
        check_num = 1

        # Prepare metadata for reuse
        package_metadata = None
        try:
            package_metadata = importlib.metadata.metadata(module_name)
        except Exception:
            pass

        # Variables needed for both location and type checks
        file_path = getattr(module_object, '__file__', 'N/A')
        module_path = getattr(module_object, '__path__', None)
        dirs_to_check = []

        # --- Check 1: Module File/Package Location ---
        title = "Module File/Package Location"
        
        if file_path != 'N/A':
            detail_finding = f"File Path: {file_path}"
            status = "[PASS]"
            if file_path.lower().endswith('__init__.py'):
                dirs_to_check = [os.path.dirname(file_path)]
        elif module_path:
             detail_finding = f"Is Package (Path): {module_path}"
             dirs_to_check = list(module_path)
             status = "[PASS]"
        else:
            detail_finding = "Built-in or C-Extension (No explicit file path found)."
            status = "[INFO]"

        results.append({
            "num": check_num,
            "title": title,
            "status_tag": status,
            "detail": detail_finding,
            "sub_details": []
        })
        check_num += 1

        # --- Check 2: Implementation Language Type ---
        title = "Implementation Language Type"
        module_type = "Built-in/Unknown"
        
        file_path_lower = file_path.lower()
        if file_path_lower.endswith(('.so', '.pyd', '.dll', '.dylib')):
            module_type = "C-Extension"
        elif file_path_lower.endswith(('.py', '__init__.py')):
            module_type = "Pure Python"
        elif module_path:
            module_type = "Pure Python (Namespace)"

        has_c_extensions_in_package = False
        if dirs_to_check and ("Pure Python" in module_type or module_type == "Pure Python (Namespace)"):
            for d in dirs_to_check:
                if os.path.exists(d):
                    try:
                        for filename in os.listdir(d):
                            if filename.lower().endswith(('.so', '.pyd', '.dll', '.dylib')):
                                has_c_extensions_in_package = True
                                break
                        if has_c_extensions_in_package:
                            break
                    except PermissionError:
                        pass

        if has_c_extensions_in_package and "Pure Python" in module_type:
            module_type = "Mixed (Python entry, uses C-extensions)"
            

        detail = f"Identified as: {module_type}."
        if "C-Extension" in module_type or "Pure Python" in module_type or "Mixed" in module_type:
             status = "[PASS]"
        else:
             status = "[INFO]" # Built-in/Unknown

        results.append({
            "num": check_num,
            "title": title,
            "status_tag": status,
            "detail": detail,
            "sub_details": []
        })
        check_num += 1

        # 3. Check for Documentation String (__doc__)
        title = "Documentation String (__doc__)"
        docstring = getattr(module_object, '__doc__', None)
        if docstring and len(docstring.strip()) > 10:
            status = "[PASS]"
            detail = f"Found (Length: {len(docstring.strip())} characters)."
        else:
            status = "[WARN]"
            detail = "Not found or too short. Module lacks descriptive text."

        results.append({"num": check_num, "title": title, "status_tag": status, "detail": detail})
        check_num += 1

        # 4. Check for Version Information (__version__)
        title = "Version Information (__version__)"
        version = getattr(module_object, '__version__', None)
        if version:
            status = "[PASS]"
            detail = f"Found (v{version})."
        else:
            status = "[WARN]"
            detail = "Not found. Version tracking is absent (Recommended)."

        results.append({"num": check_num, "title": title, "status_tag": status, "detail": detail})
        check_num += 1

        # 5. Check for Public API Definition (__all__)
        title = "Public API Definition (__all__)"
        all_list = getattr(module_object, '__all__', None)
        if all_list is not None and isinstance(all_list, list) and all_list:
            status = "[PASS]"
            detail = f"Found (Defines {len(all_list)} public objects)."
        elif all_list is None:
            status = "[INFO]"
            detail = "Not explicitly defined. Using default namespace."
        else:
            status = "[WARN]"
            detail = "Defined but empty or not a list. Check package configuration."

        results.append({"num": check_num, "title": title, "status_tag": status, "detail": detail})
        check_num += 1

        # 6. Check Object Definition Quality and Encapsulation
        title = "Object Definition Quality/Encapsulation"
        all_members = dir(module_object)
        member_names = [m for m in all_members if not m.startswith('__') or m == '__all__']
        public_members = [m for m in member_names if not m.startswith('_')]
        private_members = [m for m in member_names if m.startswith('_') and m != '__all__']
        total_members = len(public_members) + len(private_members)

        sub_details = []
        if total_members > 0:
            private_ratio = len(private_members) / total_members * 100
            
            detail = f"Total Members: {total_members} (Public: {len(public_members)}, Private: {len(private_members)})"

            # Define rating details
            ratio_string = f"Private member ratio: {private_ratio:.1f}%"

            # Define concise criteria
            PASS_CRITERIA = "< 70% or >= 5 public members"
            WARN_CRITERIA = "alert, >= 70% and <5 public members"

            if private_ratio > 70 and len(public_members) < 5:
                 status = "[WARN]"
                 # Store the concise WARN criteria
                 rating_string_full = f"{WARN_CRITERIA}"
            else:
                 status = "[PASS]"
                 # Store the concise PASS criteria
                 rating_string_full = f"reasonable, {PASS_CRITERIA}"
            
            sub_details.append(ratio_string)
            sub_details.append(rating_string_full)

        else:
            status = "[INFO]"
            detail = "Module namespace is empty (Only built-in attributes found)."
            
        results.append({"num": check_num, "title": title, "status_tag": status, "detail": detail, "sub_details": sub_details})
        check_num += 1

        # 7. Check for Excessively Large Public API Surface
        title = "Public API Surface Size"
        PUBLIC_API_THRESHOLD = 150
        if len(public_members) > PUBLIC_API_THRESHOLD:
            status = "[WARN]"
            detail = f"Excessive size detected ({len(public_members)} members). Consider segmenting."
        else:
            status = "[PASS]"
            detail = f"Reasonable size ({len(public_members)} members)."

        results.append({"num": check_num, "title": title, "status_tag": status, "detail": detail})
        check_num += 1

        # 8. Check: Callable Object Count (Functions and Classes)
        title = "Callable Object Count"
        public_callables = 0
        callables_to_analyze = []

        for name in public_members:
            attr = getattr(module_object, name)
            if inspect.isfunction(attr) or inspect.isclass(attr):
                public_callables += 1
                callables_to_analyze.append(attr)

        if public_callables > 0:
            status = "[PASS]"
            detail = f"Found {public_callables} public functions/classes, indicating functionality."
        else:
            status = "[INFO]"
            detail = "No top-level public functions/classes found."

        results.append({"num": check_num, "title": title, "status_tag": status, "detail": detail})
        check_num += 1

        # 9. Check: Import Warnings
        title = "Import Health (Warnings/Deprecations)"
        sub_details = []
        if captured_warnings:
            unique_warnings = set(str(warn.message) for warn in captured_warnings)
            status = "[WARN]"
            detail = f"{len(unique_warnings)} unique warnings detected during import."

            for warn in captured_warnings[:3]:
                 sub_details.append(f"({type(warn.message).__name__}) {str(warn.message)[:60]}...")
        else:
            status = "[PASS]"
            detail = "No warnings or deprecations detected."

        results.append({"num": check_num, "title": title, "status_tag": status, "detail": detail, "sub_details": sub_details})
        check_num += 1

        # 10. Check: Type Hint Coverage
        title = "Type Hint Coverage"
        annotated_callables = 0
        total_callables_to_check = len(callables_to_analyze)
        
        if total_callables_to_check > 0:
            for attr in callables_to_analyze:
                try:
                    signature = inspect.signature(attr)
                    has_annotation = False
                    if signature.return_annotation is not inspect.Signature.empty: has_annotation = True
                    for param in signature.parameters.values():
                        if param.annotation is not inspect.Parameter.empty:
                            has_annotation = True
                            break
                    if has_annotation: annotated_callables += 1
                except (ValueError, TypeError):
                    pass

            coverage_percentage = (annotated_callables / total_callables_to_check) * 100
            
            if coverage_percentage >= 75:
                status = "[PASS]"
                detail = f"Excellent ({coverage_percentage:.0f}% of public callables annotated)."
            elif coverage_percentage >= 30:
                status = "[WARN]"
                detail = f"Moderate ({coverage_percentage:.0f}% of public callables annotated). Aim higher."
            else:
                status = "[INFO]"
                detail = f"Low ({coverage_percentage:.0f}% of public callables annotated). Recommended for public APIs."
        else:
            status = "[INFO]"
            detail = "No public functions or classes available for analysis."

        results.append({"num": check_num, "title": title, "status_tag": status, "detail": detail})
        check_num += 1

        # 11. Check: Distribution Metadata Status
        title = "Distribution Metadata Status"
        if package_metadata:
            name = package_metadata.get('Name')
            version_meta = package_metadata.get('Version')

            if name and version_meta:
                status = "[PASS]"
                detail = f"Found package '{name}' (v{version_meta}) via importlib.metadata."
            else:
                status = "[WARN]"
                detail = "Metadata found, but name/version information is incomplete."
        else:
             status = "[WARN]"
             detail = "Package not found in distribution database (May be standalone/built-in)."

        results.append({"num": check_num, "title": title, "status_tag": status, "detail": detail})
        check_num += 1

        # 12. Check: License Status
        title = "License Status"
        if package_metadata:
            license_text = package_metadata.get('License')
            
            if license_text:
                match = re.search(r'(MIT|BSD|Apache|GPL|LGPL|Public Domain)', license_text, re.IGNORECASE)
                if match:
                    status = "[PASS]"
                    detail = f"{match.group(1).upper()} License detected."
                else:
                    status = "[PASS]"
                    detail = "Custom/Complex License detected."
            else:
                status = "[WARN]"
                detail = "'License' field missing in package metadata."

        else:
            status = "[INFO]"
            detail = "Could not retrieve package metadata."

        results.append({"num": check_num, "title": title, "status_tag": status, "detail": detail})
        check_num += 1

        # 13. Check: Required Dependencies (MANDATORY VS OPTIONAL)
        title = "Required Dependencies"
        sub_details = []

        if package_metadata:
            requires_dist = package_metadata.get_all('Requires-Dist')

            if requires_dist:
                mandatory_dependencies = set()
                optional_dependencies = set()

                for req in requires_dist:
                    match = re.match(r'([A-Za-z0-9._-]+)', req)
                    if not match:
                        continue
                    dep_name = match.group(1)

                    if ';' in req:
                        optional_dependencies.add(dep_name)
                    else:
                        mandatory_dependencies.add(dep_name)

                sorted_mandatory = sorted(list(mandatory_dependencies))
                truly_optional_set = optional_dependencies.difference(mandatory_dependencies)
                sorted_optional = sorted(list(truly_optional_set))

                num_mandatory = len(sorted_mandatory)
                num_optional = len(sorted_optional)
                total_deps = num_mandatory + num_optional

                if total_deps > 0:
                    status = "[INFO]"
                    detail = f"Found {total_deps} unique external packages ({num_mandatory} mandatory, {num_optional} optional/conditional)."

                    if num_mandatory > 0:
                        sub_details.append(f"MANDATORY: {'; '.join(sorted_mandatory)}")
                    if num_optional > 0:
                        sub_details.append(f"OPTIONAL/CONDITIONAL: {'; '.join(sorted_optional)}")
                else:
                    status = "[PASS]"
                    detail = "No external package dependencies listed (Self-contained)."
            else:
                status = "[PASS]"
                detail = "No external package dependencies listed (Self-contained)."
        else:
            status = "[INFO]"
            detail = "Could not retrieve package metadata."
            
        results.append({"num": check_num, "title": title, "status_tag": status, "detail": detail, "sub_details": sub_details})
        check_num += 1

        # --- Output: Compact Single-Line Display ---
        print("\n--- Generic Soundness Checks (One Line Per Test) ---")

        for r in results:
            summary = f"({r['num']:>2}) {r['status_tag']:<6} {r['title']}: {r['detail']}"

            if r['num'] == 6:
                # Print the main summary line first
                print(summary)

                sub_details = r.get('sub_details')
                if sub_details and len(sub_details) == 2:
                    ratio_part = sub_details[0].strip()
                    # rating_part now contains the full, concise rating and criteria:
                    # e.g., "reasonable, < 70% or >= 5 public members"
                    # or "alert, >= 70% and <5 public members"
                    rating_part = sub_details[1].strip()

                    # Use the combined rating string directly
                    output_line = f"  - {ratio_part} (rating: {rating_part})."

                    print(output_line)
                elif sub_details:
                    # Fallback for unexpected number of sub_details
                    combined_subs = "; ".join([s.strip() for s in sub_details if s.strip()])
                    print(f"  - {combined_subs}")

            elif r['num'] == 13:

                print(summary)

                if r.get('sub_details'):

                    for detail_line in r['sub_details']:
                        parts = detail_line.split(':', 1)
                        if len(parts) == 2:
                            prefix = parts[0].strip().title().replace("Optional/Conditional", "Optional")
                            content = parts[1].strip()
                            print(f"  - {prefix}: {content}")

            else:
                if r.get('sub_details'):
                    combined_subs = "; ".join([s.strip() for s in r['sub_details'] if s.strip()])
                    if combined_subs:
                        summary += f" ({combined_subs})"

                print(summary)

        
        # --- Performance Check (Separate output) ---
        print("\n--- Performance Check ---")
        EXCELLENT_PERF_THRESHOLD = 0.1 # Threshold for "Excellent (Fast startup)" in seconds

        if import_duration < EXCELLENT_PERF_THRESHOLD:
            perf_status_tag = "[PASS]"
            perf_status = "Excellent (Fast startup)"
            # Applied fix: replaced ", " with " - " and removed trailing ")" for a period "."
            perf_output = f"{perf_status} - {import_duration:.4f} s < {EXCELLENT_PERF_THRESHOLD:.1f} s."
        elif import_duration < 1.0:
            perf_status_tag = "[INFO]"
            perf_status = "Acceptable"
            # Applied fix: replaced " ({...})." with " - {...}."
            perf_output = f"{perf_status} - {import_duration:.4f} seconds."
        else:
            perf_status_tag = "[WARN]"
            perf_status = "Slow (Potential startup bottleneck)"
            # Applied fix: replaced " ({...})." with " - {...}."
            perf_output = f"{perf_status} - {import_duration:.4f} seconds."

        # The final print statement for the performance check
        print(f"   {perf_status_tag} Import Performance: {perf_output}")


        # --- Environment Check (Separate output) ---
        print("\n--- Environment Check ---")
        try:
            py_version = sys.version.split()[0]
            print(f"   [INFO] Python Version: {py_version}")

            # --- Dedicated GIL/Free-Threaded Check (Simplified Logic) ---
            impl_name = sys.implementation.name.capitalize()
            threading_model = "Varies (Non-CPython/Custom)"

            if impl_name == "Cpython":

                # Check based on user's definitive finding: presence of sys.flags.gil == 1 means GIL
                is_gil_active = hasattr(sys.flags, 'gil') and getattr(sys.flags, 'gil', 0) == 1

                if is_gil_active:
                    threading_model = "Global Interpreter Lock (GIL) Active"
                else:
                    threading_model = "Free-Threading Active (GIL Absent)"

            elif impl_name == "Pypy":
                threading_model = "Software Transactional Memory (No GIL)"
            elif impl_name == "Jython":
                threading_model = "OS Threads (No GIL)"

            print(f"   [INFO] Threading Model: {threading_model}")
            print(f"   [INFO] Interpreter Implementation: {impl_name}")

        except Exception:
             print("   [WARN] Environment Info: Failed to retrieve interpreter version or details.")

        return True

    except ImportError as e:
        print("\n--- Import Failure ---")
        print(f"[FAIL] FAILURE: Module '{module_name}' could could not be imported.")
        print(f"   Error: {e}")
        print(f"   Suggestion: Ensure the package is installed (e.g., 'pip install {module_name}')")
        return False

    except Exception as e:
        print("\n--- Unexpected Failure ---")
        print(f"[FAIL] FAILURE: An unexpected error occurred while loading '{module_name}'.")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Details: {e}")
        return False

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
        description="Check if a specified Python module can be imported successfully and assess its generic soundness.",
        epilog="Example usage: python check_module_load_status.py requests"
    )
    
    parser.add_argument(
        "module_name",
        type=str,
        nargs='?', # Makes the module name optional
        help="The name of the module to test (e.g., 'requests', 'numpy')."
    )
    
    parser.add_argument(
        "--checks-methodology",
        action='store_true',
        help="Display the methodology and rating explanations for all checks, then exit."
    )
    
    args = parser.parse_args()

    # Check for methodology flag first
    if args.checks_methodology:
        print_methodology_doc()
        # Note: print_methodology_doc calls sys.exit(0)

    # Only run the test logic if a module name was actually provided.
    if args.module_name:
        print("=" * 40)
        print("PYTHON MODULE LOADING TEST UTILITY")
        print("=" * 40)
        
        check_module_loads(args.module_name)
        
        print("=" * 40)
