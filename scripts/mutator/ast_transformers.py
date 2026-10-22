#!/usr/bin/env python3
"""
scripts/ast_transformers.py

Diff-constrained AST node transformers:
Applies targeted semantic mutations strictly to AST nodes whose lineno
belongs to an allowed line number set.
"""

import ast
from typing import Optional, Set


class DiffConstrainedComparisonMutator(ast.NodeTransformer):
    """Mutates binary comparison operators strictly on target line numbers."""
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

    def __init__(self, target_idx: int, allowed_lines: Optional[Set[int]] = None):
        super().__init__()
        self.target_idx = target_idx
        self.allowed_lines = allowed_lines
        self.current_idx = 0
        self.applied_mutation = None

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        lineno = getattr(node, "lineno", None)
        if self.allowed_lines is not None and (lineno is None or lineno not in self.allowed_lines):
            return self.generic_visit(node)

        new_ops = []
        for op in node.ops:
            op_type = type(op)
            if op_type in self.OP_MAP:
                if self.current_idx == self.target_idx:
                    mutated_op = self.OP_MAP[op_type]()
                    new_ops.append(mutated_op)
                    self.applied_mutation = (
                        f"Comparison flipped: {op_type.__name__} -> {mutated_op.__class__.__name__} "
                        f"at patch line {lineno}"
                    )
                else:
                    new_ops.append(op)
                self.current_idx += 1
            else:
                new_ops.append(op)
        node.ops = new_ops
        return self.generic_visit(node)


class DiffConstrainedBooleanMutator(ast.NodeTransformer):
    """Mutates True/False literals strictly on target line numbers."""
    def __init__(self, target_idx: int, allowed_lines: Optional[Set[int]] = None):
        super().__init__()
        self.target_idx = target_idx
        self.allowed_lines = allowed_lines
        self.current_idx = 0
        self.applied_mutation = None

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        lineno = getattr(node, "lineno", None)
        if self.allowed_lines is not None and (lineno is None or lineno not in self.allowed_lines):
            return self.generic_visit(node)

        if isinstance(node.value, bool):
            if self.current_idx == self.target_idx:
                mutated_val = not node.value
                new_node = ast.Constant(value=mutated_val)
                self.applied_mutation = (
                    f"Boolean literal flipped: {node.value} -> {mutated_val} "
                    f"at patch line {lineno}"
                )
                self.current_idx += 1
                return ast.copy_location(new_node, node)
            self.current_idx += 1
        return self.generic_visit(node)


class DiffConstrainedReturnMutator(ast.NodeTransformer):
    """Mutates return statements strictly on target line numbers."""
    def __init__(self, target_idx: int, allowed_lines: Optional[Set[int]] = None):
        super().__init__()
        self.target_idx = target_idx
        self.allowed_lines = allowed_lines
        self.current_idx = 0
        self.applied_mutation = None

    def visit_Return(self, node: ast.Return) -> ast.AST:
        lineno = getattr(node, "lineno", None)
        if self.allowed_lines is not None and (lineno is None or lineno not in self.allowed_lines):
            return self.generic_visit(node)

        if self.current_idx == self.target_idx:
            if node.value is None or (isinstance(node.value, ast.Constant) and node.value.value is None):
                new_node = ast.Return(value=ast.Constant(value=True))
                self.applied_mutation = f"Return None mutated to Return True at patch line {lineno}"
            else:
                new_node = ast.Return(value=ast.Constant(value=None))
                self.applied_mutation = f"Return value nullified to None at patch line {lineno}"
            self.current_idx += 1
            return ast.copy_location(new_node, node)
        self.current_idx += 1
        return self.generic_visit(node)
