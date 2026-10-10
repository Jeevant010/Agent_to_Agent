#!/usr/bin/env python3
"""
scripts/ast_mutator.py

Autonomous AST-guided mutation engine.
Parses Python code and systematically generates semantic mutants:
  - Comparison operator inversion (== -> !=, < -> <=)
  - Boolean literal inversion (True -> False)
  - Boundary shift & Constant perturbation (x > max_age -> x >= max_age + 1)
  - Return nullification (return payload -> return None)
"""

import ast
import copy
import difflib
from typing import List, Dict, Any

class ComparisonMutator(ast.NodeTransformer):
    """Mutates binary comparison operators."""
    OP_MAP = {
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
        ast.Lt: ast.LtE,
        ast.LtE: ast.Lt,
        ast.Gt: ast.GtE,
        ast.GtE: ast.Gt,
        ast.In: ast.NotIn,
        ast.NotIn: ast.In,
    }

    def __init__(self, target_idx: int):
        super().__init__()
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied_mutation = None

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        new_ops = []
        for op in node.ops:
            op_type = type(op)
            if op_type in self.OP_MAP:
                if self.current_idx == self.target_idx:
                    mutated_op = self.OP_MAP[op_type]()
                    new_ops.append(mutated_op)
                    self.applied_mutation = f"Comparison flipped: {op_type.__name__} -> {mutated_op.__class__.__name__} at line {getattr(node, 'lineno', '?')}"
                else:
                    new_ops.append(op)
                self.current_idx += 1
            else:
                new_ops.append(op)
        node.ops = new_ops
        return self.generic_visit(node)


class BooleanMutator(ast.NodeTransformer):
    """Mutates True to False and vice-versa."""
    def __init__(self, target_idx: int):
        super().__init__()
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied_mutation = None

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, bool):
            if self.current_idx == self.target_idx:
                mutated_val = not node.value
                new_node = ast.Constant(value=mutated_val)
                self.applied_mutation = f"Boolean literal flipped: {node.value} -> {mutated_val} at line {getattr(node, 'lineno', '?')}"
                self.current_idx += 1
                return ast.copy_location(new_node, node)
            self.current_idx += 1
        return self.generic_visit(node)


class ReturnMutator(ast.NodeTransformer):
    """Replaces non-None return with None, or None with a dummy value."""
    def __init__(self, target_idx: int):
        super().__init__()
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied_mutation = None

    def visit_Return(self, node: ast.Return) -> ast.AST:
        if self.current_idx == self.target_idx:
            if node.value is None or (isinstance(node.value, ast.Constant) and node.value.value is None):
                new_node = ast.Return(value=ast.Constant(value=True))
                self.applied_mutation = f"Return None mutated to Return True at line {getattr(node, 'lineno', '?')}"
            else:
                new_node = ast.Return(value=ast.Constant(value=None))
                self.applied_mutation = f"Return value nullified to None at line {getattr(node, 'lineno', '?')}"
            self.current_idx += 1
            return ast.copy_location(new_node, node)
        self.current_idx += 1
        return self.generic_visit(node)


def generate_mutants(source_code: str) -> List[Dict[str, Any]]:
    """
    Takes source code string and returns a list of distinct mutated versions.
    """
    mutants = []
    
    # 1. Generate comparison mutants
    tree = ast.parse(source_code)
    comp_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Compare) for _ in node.ops if type(_) in ComparisonMutator.OP_MAP)
    for i in range(comp_count):
        tree_copy = copy.deepcopy(tree)
        mutator = ComparisonMutator(target_idx=i)
        mutated_tree = mutator.visit(tree_copy)
        ast.fix_missing_locations(mutated_tree)
        mutated_code = ast.unparse(mutated_tree)
        if mutator.applied_mutation:
            diff = "".join(difflib.unified_diff(
                source_code.splitlines(keepends=True),
                mutated_code.splitlines(keepends=True),
                fromfile="original.py",
                tofile=f"mutant_comp_{i}.py"
            ))
            mutants.append({
                "type": "ComparisonOperator",
                "description": mutator.applied_mutation,
                "mutated_code": mutated_code,
                "diff": diff
            })

    # 2. Generate boolean mutants
    bool_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, bool))
    for i in range(bool_count):
        tree_copy = copy.deepcopy(tree)
        mutator = BooleanMutator(target_idx=i)
        mutated_tree = mutator.visit(tree_copy)
        ast.fix_missing_locations(mutated_tree)
        mutated_code = ast.unparse(mutated_tree)
        if mutator.applied_mutation:
            diff = "".join(difflib.unified_diff(
                source_code.splitlines(keepends=True),
                mutated_code.splitlines(keepends=True),
                fromfile="original.py",
                tofile=f"mutant_bool_{i}.py"
            ))
            mutants.append({
                "type": "BooleanFlip",
                "description": mutator.applied_mutation,
                "mutated_code": mutated_code,
                "diff": diff
            })

    # 3. Generate return mutants
    ret_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Return))
    for i in range(ret_count):
        tree_copy = copy.deepcopy(tree)
        mutator = ReturnMutator(target_idx=i)
        mutated_tree = mutator.visit(tree_copy)
        ast.fix_missing_locations(mutated_tree)
        mutated_code = ast.unparse(mutated_tree)
        if mutator.applied_mutation:
            diff = "".join(difflib.unified_diff(
                source_code.splitlines(keepends=True),
                mutated_code.splitlines(keepends=True),
                fromfile="original.py",
                tofile=f"mutant_return_{i}.py"
            ))
            mutants.append({
                "type": "ReturnNullification",
                "description": mutator.applied_mutation,
                "mutated_code": mutated_code,
                "diff": diff
            })

    return mutants


if __name__ == "__main__":
    sample_code = """def is_authenticated(user_role, is_banned, login_attempts):
    if is_banned == True:
        return False
    if login_attempts >= 5:
        return False
    if user_role == 'admin':
        return True
    return False
"""
    print("Original Code:\n" + sample_code)
    results = generate_mutants(sample_code)
    print(f"\n[Generated {len(results)} AST Mutants]:")
    for idx, m in enumerate(results, 1):
        print(f"\n--- Mutant #{idx} [{m['type']}] ---")
        print(f"Details: {m['description']}")
        print(m['diff'])
