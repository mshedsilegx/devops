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

def print_report(results: List[Dict[str, Any]]):
    """
    Prints the analysis results in a structured, one-line-per-test format.

    Args:
        results: A list of dictionaries, where each dictionary is a check result.
    """
    print("\n--- Generic Soundness Checks (One Line Per Test) ---")
    
    for r in results:
        summary = f"({r['num']:>2}) {r['status_tag']:<6} {r['title']}: {r['detail']}"

        # Special handling for checks with sub-details
        if r['num'] == 6: # Encapsulation
            print(summary)
            sub_details = r.get('sub_details')
            if sub_details and len(sub_details) == 2:
                print(f"  - {sub_details[0].strip()} (rating: {sub_details[1].strip()}).")
        elif r['num'] == 13: # Dependencies
            print(summary)
            if r.get('sub_details'):
                for detail_line in r['sub_details']:
                    parts = detail_line.split(':', 1)
                    if len(parts) == 2:
                        prefix = parts[0].strip().title().replace("Optional/Conditional", "Optional")
                        print(f"  - {prefix}: {parts[1].strip()}")
        else:
            # General case for other checks with potential sub-details
            sub_details = r.get('sub_details')
            if sub_details:
                combined_subs = "; ".join([s.strip() for s in sub_details if s.strip()])
                if combined_subs:
                    summary += f" ({combined_subs})"
            print(summary)

def print_performance_check(analysis: 'ModuleAnalysis'):
    """Prints the import performance check results."""
    print("\n--- Performance Check ---")
    EXCELLENT_PERF_THRESHOLD = 0.1
    duration = analysis.import_duration
    
    if duration < EXCELLENT_PERF_THRESHOLD:
        tag, status, output = "[PASS]", "Excellent (Fast startup)", f"{duration:.4f} s < {EXCELLENT_PERF_THRESHOLD:.1f} s."
    elif duration < 1.0:
        tag, status, output = "[INFO]", "Acceptable", f"{duration:.4f} seconds."
    else:
        tag, status, output = "[WARN]", "Slow (Potential startup bottleneck)", f"{duration:.4f} seconds."
        
    print(f"   {tag} Import Performance: {status} - {output}")

def print_environment_check():
    """Prints the Python environment details."""
    print("\n--- Environment Check ---")
    try:
        py_version = sys.version.split()[0]
        impl_name = sys.implementation.name.capitalize()
        threading_model = "Varies (Non-CPython/Custom)"
        
        if impl_name == "Cpython":
            is_gil_active = hasattr(sys.flags, 'gil') and getattr(sys.flags, 'gil', 0) == 1
            threading_model = "Global Interpreter Lock (GIL) Active" if is_gil_active else "Free-Threading Active (GIL Absent)"
        elif impl_name == "Pypy":
            threading_model = "Software Transactional Memory (No GIL)"
        elif impl_name == "Jython":
            threading_model = "OS Threads (No GIL)"

        print(f"   [INFO] Python Version: {py_version}")
        print(f"   [INFO] Threading Model: {threading_model}")
        print(f"   [INFO] Interpreter Implementation: {impl_name}")
    except Exception:
        print("   [WARN] Environment Info: Failed to retrieve interpreter version or details.")

class ModuleAnalysis:
    """
    A class to perform a comprehensive analysis of a Python module's soundness.
    It separates the analysis logic from the presentation (printing) logic.
    """
    def __init__(self, module_name: str):
        """
        Initializes the analysis by importing the module and gathering key data.
        
        Args:
            module_name (str): The name of the module to analyze.

        Raises:
            ImportError: If the module cannot be imported.
            Exception: For other unexpected errors during import.
        """
        self.module_name = module_name
        self.module_object = None
        self.import_duration = 0.0
        self.captured_warnings = []
        self.package_metadata = None
        self.public_members = []
        self.private_members = []
        self.all_members = []
        self.callables_to_analyze = []

        self._import_module()
        self._gather_members()
        self._gather_metadata()

    def _import_module(self):
        """Imports the module, records duration, and captures warnings."""
        start_time = time.perf_counter()
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                self.module_object = importlib.import_module(self.module_name)
                self.captured_warnings = list(w)
        finally:
            self.import_duration = time.perf_counter() - start_time

    def _gather_members(self):
        """Gathers and categorizes all members of the module."""
        if not self.module_object:
            return

        all_dir_members = dir(self.module_object)
        member_names = [m for m in all_dir_members if not m.startswith('__') or m == '__all__']
        
        self.public_members = [m for m in member_names if not m.startswith('_')]
        self.private_members = [m for m in member_names if m.startswith('_') and m != '__all__']
        self.all_members = self.public_members + self.private_members

        for name in self.public_members:
            attr = getattr(self.module_object, name)
            if inspect.isfunction(attr) or inspect.isclass(attr):
                self.callables_to_analyze.append(attr)

    def _gather_metadata(self):
        """Retrieves package metadata if available."""
        try:
            self.package_metadata = importlib.metadata.metadata(self.module_name)
        except importlib.metadata.PackageNotFoundError:
            self.package_metadata = None

    def analyze_location(self) -> Dict[str, Any]:
        """Check 1: Determines the module's file or package location."""
        file_path = getattr(self.module_object, '__file__', 'N/A')
        module_path = getattr(self.module_object, '__path__', None)
        
        detail, status = "", ""
        if file_path != 'N/A':
            detail = f"File Path: {file_path}"
            status = "[PASS]"
        elif module_path:
            detail = f"Is Package (Path): {module_path}"
            status = "[PASS]"
        else:
            detail = "Built-in or C-Extension (No explicit file path found)."
            status = "[INFO]"

        return {"title": "Module File/Package Location", "status_tag": status, "detail": detail}

    def analyze_language_type(self) -> Dict[str, Any]:
        """Check 2: Determines the implementation language (Python, C-extension, etc.)."""
        file_path = getattr(self.module_object, '__file__', 'N/A')
        module_path = getattr(self.module_object, '__path__', None)
        module_type = "Built-in/Unknown"
        
        file_path_lower = file_path.lower()
        if file_path_lower.endswith(('.so', '.pyd', '.dll', '.dylib')):
            module_type = "C-Extension"
        elif file_path_lower.endswith(('.py', '__init__.py')):
            module_type = "Pure Python"
        elif module_path:
            module_type = "Pure Python (Namespace)"

        # Check for mixed-language packages
        dirs_to_check = [os.path.dirname(file_path)] if '__init__.py' in file_path_lower else (list(module_path) if module_path else [])
        has_c_extensions_in_package = False
        if dirs_to_check and "Pure Python" in module_type:
            for d in dirs_to_check:
                if os.path.exists(d):
                    try:
                        for filename in os.listdir(d):
                            if filename.lower().endswith(('.so', '.pyd', '.dll', '.dylib')):
                                has_c_extensions_in_package = True
                                break
                        if has_c_extensions_in_package: break
                    except PermissionError: pass

        if has_c_extensions_in_package:
            module_type = "Mixed (Python entry, uses C-extensions)"
            
        status = "[PASS]" if "C-Extension" in module_type or "Pure Python" in module_type or "Mixed" in module_type else "[INFO]"
        return {"title": "Implementation Language Type", "status_tag": status, "detail": f"Identified as: {module_type}."}

    def analyze_docstring(self) -> Dict[str, Any]:
        """Check 3: Checks for the presence and length of the module's docstring."""
        docstring = getattr(self.module_object, '__doc__', None)
        if docstring and len(docstring.strip()) > 10:
            status = "[PASS]"
            detail = f"Found (Length: {len(docstring.strip())} characters)."
        else:
            status = "[WARN]"
            detail = "Not found or too short. Module lacks descriptive text."
        return {"title": "Documentation String (__doc__)", "status_tag": status, "detail": detail}

    def analyze_version(self) -> Dict[str, Any]:
        """Check 4: Checks for the __version__ attribute."""
        version = getattr(self.module_object, '__version__', None)
        if version:
            status = "[PASS]"
            detail = f"Found (v{version})."
        else:
            status = "[WARN]"
            detail = "Not found. Version tracking is absent (Recommended)."
        return {"title": "Version Information (__version__)", "status_tag": status, "detail": detail}

    def analyze_public_api(self) -> Dict[str, Any]:
        """Check 5: Checks for the __all__ attribute to define a public API."""
        all_list = getattr(self.module_object, '__all__', None)
        if all_list is not None and isinstance(all_list, list) and all_list:
            status = "[PASS]"
            detail = f"Found (Defines {len(all_list)} public objects)."
        elif all_list is None:
            status = "[INFO]"
            detail = "Not explicitly defined. Using default namespace."
        else:
            status = "[WARN]"
            detail = "Defined but empty or not a list. Check package configuration."
        return {"title": "Public API Definition (__all__)", "status_tag": status, "detail": detail}

    def analyze_encapsulation(self) -> Dict[str, Any]:
        """Check 6: Analyzes the ratio of private to public members."""
        total_members = len(self.all_members)
        sub_details = []
        if total_members > 0:
            private_ratio = len(self.private_members) / total_members * 100
            detail = f"Total Members: {total_members} (Public: {len(self.public_members)}, Private: {len(self.private_members)})"
            
            if private_ratio > 70 and len(self.public_members) < 5:
                status = "[WARN]"
                rating_string_full = "alert, >= 70% and <5 public members"
            else:
                status = "[PASS]"
                rating_string_full = "reasonable, < 70% or >= 5 public members"
            
            sub_details.append(f"Private member ratio: {private_ratio:.1f}%")
            sub_details.append(rating_string_full)
        else:
            status = "[INFO]"
            detail = "Module namespace is empty (Only built-in attributes found)."
            
        return {"title": "Object Definition Quality/Encapsulation", "status_tag": status, "detail": detail, "sub_details": sub_details}

    def analyze_api_surface_size(self) -> Dict[str, Any]:
        """Check 7: Checks if the public API surface is excessively large."""
        PUBLIC_API_THRESHOLD = 150
        if len(self.public_members) > PUBLIC_API_THRESHOLD:
            status = "[WARN]"
            detail = f"Excessive size detected ({len(self.public_members)} members). Consider segmenting."
        else:
            status = "[PASS]"
            detail = f"Reasonable size ({len(self.public_members)} members)."
        return {"title": "Public API Surface Size", "status_tag": status, "detail": detail}

    def analyze_callable_count(self) -> Dict[str, Any]:
        """Check 8: Counts the number of public callable objects (functions/classes)."""
        if self.callables_to_analyze:
            status = "[PASS]"
            detail = f"Found {len(self.callables_to_analyze)} public functions/classes, indicating functionality."
        else:
            status = "[INFO]"
            detail = "No top-level public functions/classes found."
        return {"title": "Callable Object Count", "status_tag": status, "detail": detail}

    def analyze_import_health(self) -> Dict[str, Any]:
        """Check 9: Checks for warnings raised during module import."""
        sub_details = []
        if self.captured_warnings:
            unique_warnings = set(str(warn.message) for warn in self.captured_warnings)
            status = "[WARN]"
            detail = f"{len(unique_warnings)} unique warnings detected during import."
            for warn in self.captured_warnings[:3]:
                sub_details.append(f"({type(warn.message).__name__}) {str(warn.message)[:60]}...")
        else:
            status = "[PASS]"
            detail = "No warnings or deprecations detected."
        return {"title": "Import Health (Warnings/Deprecations)", "status_tag": status, "detail": detail, "sub_details": sub_details}

    def analyze_type_hint_coverage(self) -> Dict[str, Any]:
        """Check 10: Calculates the percentage of public callables with type hints."""
        total_callables = len(self.callables_to_analyze)
        if not total_callables:
            return {"title": "Type Hint Coverage", "status_tag": "[INFO]", "detail": "No public functions or classes available for analysis."}

        annotated_callables = 0
        for attr in self.callables_to_analyze:
            try:
                signature = inspect.signature(attr)
                if signature.return_annotation is not inspect.Signature.empty:
                    annotated_callables += 1
                    continue
                for param in signature.parameters.values():
                    if param.annotation is not inspect.Parameter.empty:
                        annotated_callables += 1
                        break
            except (ValueError, TypeError):
                pass
        
        coverage = (annotated_callables / total_callables) * 100
        if coverage >= 75:
            status, detail = "[PASS]", f"Excellent ({coverage:.0f}% of public callables annotated)."
        elif coverage >= 30:
            status, detail = "[WARN]", f"Moderate ({coverage:.0f}% of public callables annotated). Aim higher."
        else:
            status, detail = "[INFO]", f"Low ({coverage:.0f}% of public callables annotated). Recommended for public APIs."
            
        return {"title": "Type Hint Coverage", "status_tag": status, "detail": detail}

    def analyze_metadata_status(self) -> Dict[str, Any]:
        """Check 11: Checks for package distribution metadata."""
        if self.package_metadata:
            name = self.package_metadata.get('Name')
            version = self.package_metadata.get('Version')
            if name and version:
                status, detail = "[PASS]", f"Found package '{name}' (v{version}) via importlib.metadata."
            else:
                status, detail = "[WARN]", "Metadata found, but name/version information is incomplete."
        else:
            status, detail = "[WARN]", "Package not found in distribution database (May be standalone/built-in)."
        return {"title": "Distribution Metadata Status", "status_tag": status, "detail": detail}

    def analyze_license_status(self) -> Dict[str, Any]:
        """Check 12: Checks for license information in package metadata."""
        if not self.package_metadata:
            return {"title": "License Status", "status_tag": "[INFO]", "detail": "Could not retrieve package metadata."}

        license_text = self.package_metadata.get('License')
        if license_text:
            match = re.search(r'(MIT|BSD|Apache|GPL|LGPL|Public Domain)', license_text, re.IGNORECASE)
            detail = f"{match.group(1).upper()} License detected." if match else "Custom/Complex License detected."
            status = "[PASS]"
        else:
            status, detail = "[WARN]", "'License' field missing in package metadata."
            
        return {"title": "License Status", "status_tag": status, "detail": detail}

    def analyze_dependencies(self) -> Dict[str, Any]:
        """Check 13: Analyzes mandatory and optional dependencies from metadata."""
        if not self.package_metadata:
            return {"title": "Required Dependencies", "status_tag": "[INFO]", "detail": "Could not retrieve package metadata."}

        requires_dist = self.package_metadata.get_all('Requires-Dist')
        if not requires_dist:
            return {"title": "Required Dependencies", "status_tag": "[PASS]", "detail": "No external package dependencies listed (Self-contained)."}

        mandatory = set()
        optional = set()
        for req in requires_dist:
            match = re.match(r'([A-Za-z0-9._-]+)', req)
            if match:
                dep_name = match.group(1)
                if ';' in req:
                    optional.add(dep_name)
                else:
                    mandatory.add(dep_name)
        
        truly_optional = optional.difference(mandatory)
        num_mandatory, num_optional = len(mandatory), len(truly_optional)
        total_deps = num_mandatory + num_optional

        if total_deps == 0:
            return {"title": "Required Dependencies", "status_tag": "[PASS]", "detail": "No external package dependencies listed (Self-contained)."}

        detail = f"Found {total_deps} unique external packages ({num_mandatory} mandatory, {num_optional} optional/conditional)."
        sub_details = []
        if mandatory:
            sub_details.append(f"MANDATORY: {'; '.join(sorted(list(mandatory)))}")
        if truly_optional:
            sub_details.append(f"OPTIONAL/CONDITIONAL: {'; '.join(sorted(list(truly_optional)))}")
            
        return {"title": "Required Dependencies", "status_tag": "[INFO]", "detail": detail, "sub_details": sub_details}

    def run_all_checks(self) -> List[Dict[str, Any]]:
        """
        Runs all the analysis checks in sequence and returns the collected results.
        
        Returns:
            A list of dictionaries, where each dictionary represents the result of a check.
        """
        results = [
            self.analyze_location(),
            self.analyze_language_type(),
            self.analyze_docstring(),
            self.analyze_version(),
            self.analyze_public_api(),
            self.analyze_encapsulation(),
            self.analyze_api_surface_size(),
            self.analyze_callable_count(),
            self.analyze_import_health(),
            self.analyze_type_hint_coverage(),
            self.analyze_metadata_status(),
            self.analyze_license_status(),
            self.analyze_dependencies(),
        ]
        # Add a number to each result for presentation purposes
        for i, result in enumerate(results):
            result['num'] = i + 1

        return results

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
        description="Check if a specified Python module can be imported successfully and assess its generic soundness.",
        epilog="Example usage: python python_module_tester.py requests"
    )
    
    parser.add_argument(
        "module_name",
        type=str,
        nargs='?',
        help="The name of the module to test (e.g., 'requests', 'numpy')."
    )
    
    parser.add_argument(
        "--checks-methodology",
        action='store_true',
        help="Display the methodology and rating explanations for all checks, then exit."
    )
    
    args = parser.parse_args()

    if args.checks_methodology:
        print_methodology_doc()

    if not args.module_name:
        if not args.checks_methodology:
            parser.print_help()
        sys.exit(0)

    print("=" * 40)
    print("PYTHON MODULE LOADING TEST UTILITY")
    print("=" * 40)

    try:
        print(f"Testing import of '{args.module_name}'...")
        analysis = ModuleAnalysis(args.module_name)
        print(f"[OK] SUCCESS: Module '{args.module_name}' imported correctly.")
        
        results = analysis.run_all_checks()
        
        print_report(results)
        print_performance_check(analysis)
        print_environment_check()

    except ImportError as e:
        print("\n--- Import Failure ---")
        print(f"[FAIL] FAILURE: Module '{args.module_name}' could not be imported.")
        print(f"   Error: {e}")
        print(f"   Suggestion: Ensure the package is installed (e.g., 'pip install {args.module_name}')")
    except Exception as e:
        print("\n--- Unexpected Failure ---")
        print(f"[FAIL] FAILURE: An unexpected error occurred while loading '{args.module_name}'.")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Details: {e}")
    finally:
        print("=" * 40)
