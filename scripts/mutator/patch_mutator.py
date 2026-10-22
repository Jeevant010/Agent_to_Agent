#!/usr/bin/env python3
"""
scripts/mutator/patch_mutator.py

Diff-Aware AST Mutation Orchestrator:
Coordinates diff parsing, patch application, and line-constrained AST mutations.
"""

import ast
import copy
import difflib
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional

try:
    from .diff_parser import parse_patch_modified_lines, apply_patch_to_text
    from .ast_transformers import (
        DiffConstrainedComparisonMutator,
        DiffConstrainedBooleanMutator,
        DiffConstrainedReturnMutator
    )
except ImportError:
    # Direct script invocation support
    sys.path.insert(0, str(Path(__file__).parent))
    from diff_parser import parse_patch_modified_lines, apply_patch_to_text
    from ast_transformers import (
        DiffConstrainedComparisonMutator,
        DiffConstrainedBooleanMutator,
        DiffConstrainedReturnMutator
    )


def generate_patch_mutants(
    base_code: str,
    patch_diff: str,
    target_filename: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Takes base code and a patch diff, applies the patch, identifies modified lines,
    and returns mutants generated strictly within those modified lines.
    Each mutant includes the mutated post-patch code and a synthesized mutated patch diff.
    """
    mod_lines_map = parse_patch_modified_lines(patch_diff)

    if target_filename and target_filename in mod_lines_map:
        allowed_lines = mod_lines_map[target_filename]
    elif len(mod_lines_map) == 1:
        allowed_lines = next(iter(mod_lines_map.values()))
    else:
        allowed_lines = set().union(*mod_lines_map.values()) if mod_lines_map else None

    # Post-patch code
    post_patch_code = apply_patch_to_text(base_code, patch_diff) if "@@" in patch_diff else base_code

    mutants: List[Dict[str, Any]] = []
    tree = ast.parse(post_patch_code)

    # 1. Comparison mutations on patch lines
    comp_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            lineno = getattr(node, "lineno", None)
            if allowed_lines is None or (lineno and lineno in allowed_lines):
                comp_count += sum(1 for op in node.ops if type(op) in DiffConstrainedComparisonMutator.OP_MAP)

    for i in range(comp_count):
        tree_copy = copy.deepcopy(tree)
        mutator = DiffConstrainedComparisonMutator(target_idx=i, allowed_lines=allowed_lines)
        mutated_tree = mutator.visit(tree_copy)
        ast.fix_missing_locations(mutated_tree)
        mutated_code = ast.unparse(mutated_tree)
        if mutator.applied_mutation:
            mutated_patch = "".join(difflib.unified_diff(
                base_code.splitlines(keepends=True),
                mutated_code.splitlines(keepends=True),
                fromfile="a/target.py",
                tofile="b/target.py"
            ))
            mutants.append({
                "type": "ComparisonOperator",
                "description": mutator.applied_mutation,
                "mutated_code": mutated_code,
                "mutated_patch": mutated_patch
            })

    # 2. Boolean mutations on patch lines
    bool_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            lineno = getattr(node, "lineno", None)
            if allowed_lines is None or (lineno and lineno in allowed_lines):
                bool_count += 1

    for i in range(bool_count):
        tree_copy = copy.deepcopy(tree)
        mutator = DiffConstrainedBooleanMutator(target_idx=i, allowed_lines=allowed_lines)
        mutated_tree = mutator.visit(tree_copy)
        ast.fix_missing_locations(mutated_tree)
        mutated_code = ast.unparse(mutated_tree)
        if mutator.applied_mutation:
            mutated_patch = "".join(difflib.unified_diff(
                base_code.splitlines(keepends=True),
                mutated_code.splitlines(keepends=True),
                fromfile="a/target.py",
                tofile="b/target.py"
            ))
            mutants.append({
                "type": "BooleanFlip",
                "description": mutator.applied_mutation,
                "mutated_code": mutated_code,
                "mutated_patch": mutated_patch
            })

    # 3. Return mutations on patch lines
    ret_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            lineno = getattr(node, "lineno", None)
            if allowed_lines is None or (lineno and lineno in allowed_lines):
                ret_count += 1

    for i in range(ret_count):
        tree_copy = copy.deepcopy(tree)
        mutator = DiffConstrainedReturnMutator(target_idx=i, allowed_lines=allowed_lines)
        mutated_tree = mutator.visit(tree_copy)
        ast.fix_missing_locations(mutated_tree)
        mutated_code = ast.unparse(mutated_tree)
        if mutator.applied_mutation:
            mutated_patch = "".join(difflib.unified_diff(
                base_code.splitlines(keepends=True),
                mutated_code.splitlines(keepends=True),
                fromfile="a/target.py",
                tofile="b/target.py"
            ))
            mutants.append({
                "type": "ReturnNullification",
                "description": mutator.applied_mutation,
                "mutated_code": mutated_code,
                "mutated_patch": mutated_patch
            })

    return mutants


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
        return True
     return True
"""
    print("[Testing scripts/mutator/patch_mutator.py]")
    lines = parse_patch_modified_lines(sample_patch)
    print(f"Detected Modified Lines in Patch: {lines}")
    
    results = generate_patch_mutants(sample_base, sample_patch)
    print(f"Generated {len(results)} patch-constrained mutants:")
    for idx, m in enumerate(results, 1):
        print(f"\n--- Mutant #{idx} [{m['type']}]: {m['description']} ---")
        print(m["mutated_patch"])
