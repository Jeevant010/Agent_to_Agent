#!/usr/bin/env python3
"""
scripts/patch_mutator.py (Root Shim)

Delegates directly to scripts.mutator.patch_mutator.
Preserves existing CLI usage: `python scripts/patch_mutator.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mutator.patch_mutator import (
    generate_patch_mutants,
    parse_patch_modified_lines,
    apply_patch_to_text,
)

if __name__ == "__main__":
    sample_base = """def validate_user(user_role, is_banned, attempts):
    if is_banned == True:
        return False
    if attempts >= 5:
        return False
    return True
"""
    sample_patch = """--- a/target.py
+++ b/target.py
@@ -4,3 +4,4 @@
     if attempts >= 5:
         return False
+    if user_role == 'admin':
+        return True
     return True
"""
    print("[Testing scripts/patch_mutator.py via Root Shim]")
    lines = parse_patch_modified_lines(sample_patch)
    print(f"Detected Modified Lines in Patch: {lines}")
    
    results = generate_patch_mutants(sample_base, sample_patch)
    print(f"Generated {len(results)} patch-constrained mutants:")
    for idx, m in enumerate(results, 1):
        print(f"\n--- Mutant #{idx} [{m['type']}]: {m['description']} ---")
        print(m["mutated_patch"])
