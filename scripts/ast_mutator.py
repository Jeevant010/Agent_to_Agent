#!/usr/bin/env python3
"""AST-guided semantic mutation engine (the AAVS "attacker").

The mutator is intentionally conservative: every operator below produces a
semantically different program while remaining syntactically valid. The
families map directly to the Layer-1 taxonomy in docs/RELATED_WORK_ACADEMIC.md:

  * ComparisonOperator   - boundary/relational flips  (< -> <=, == -> !=)
  * BooleanFlip          - True <-> False literals
  * ReturnNullification  - returns replaced with None/True
  * ArithmeticOperator   - + <-> -, * <-> /, // -> /
  * BooleanOperator      - and <-> or
  * IfNegation           - negates an if-condition
  * AugmentedAssignment  - += <-> -=, *= <-> /=
  * ExceptionSwallow     - wraps a function body in try/except: pass

Equivalent mutants are not removed here; that is the job of the semantic
pre-filter described in the research plan.
"""

from __future__ import annotations

import ast
import copy
import difflib
from typing import Any, Dict, List


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
        ast.Is: ast.IsNot,
        ast.IsNot: ast.Is,
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
                    self.applied_mutation = (
                        f"Comparison flipped: {op_type.__name__} -> "
                        f"{type(mutated_op).__name__} at line {getattr(node, 'lineno', '?')}"
                    )
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
                self.applied_mutation = (
                    f"Boolean literal flipped: {node.value} -> {mutated_val} "
                    f"at line {getattr(node, 'lineno', '?')}"
                )
                self.current_idx += 1
                return ast.copy_location(new_node, node)
            self.current_idx += 1
        return self.generic_visit(node)


class ReturnMutator(ast.NodeTransformer):
    """Replaces non-None returns with None, or None with True."""

    def __init__(self, target_idx: int):
        super().__init__()
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied_mutation = None

    def visit_Return(self, node: ast.Return) -> ast.AST:
        if self.current_idx == self.target_idx:
            if node.value is None or (
                isinstance(node.value, ast.Constant) and node.value.value is None
            ):
                new_node = ast.Return(value=ast.Constant(value=True))
                self.applied_mutation = (
                    f"Return None mutated to Return True at line "
                    f"{getattr(node, 'lineno', '?')}"
                )
            else:
                new_node = ast.Return(value=ast.Constant(value=None))
                self.applied_mutation = (
                    f"Return value nullified to None at line "
                    f"{getattr(node, 'lineno', '?')}"
                )
            self.current_idx += 1
            return ast.copy_location(new_node, node)
        self.current_idx += 1
        return self.generic_visit(node)


class ArithmeticMutator(ast.NodeTransformer):
    """Mutates arithmetic binary operators."""

    OP_MAP = {
        ast.Add: ast.Sub,
        ast.Sub: ast.Add,
        ast.Mult: ast.Div,
        ast.Div: ast.Mult,
        ast.FloorDiv: ast.Div,
        ast.Mod: ast.Mult,
    }

    def __init__(self, target_idx: int):
        super().__init__()
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied_mutation = None

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        op_type = type(node.op)
        if op_type in self.OP_MAP:
            if self.current_idx == self.target_idx:
                mutated_op = self.OP_MAP[op_type]()
                node.op = mutated_op
                self.applied_mutation = (
                    f"Arithmetic operator flipped: {op_type.__name__} -> "
                    f"{type(mutated_op).__name__} at line {getattr(node, 'lineno', '?')}"
                )
            self.current_idx += 1
        return self.generic_visit(node)


class BooleanOperatorMutator(ast.NodeTransformer):
    """Swaps `and` and `or` in boolean expressions."""

    def __init__(self, target_idx: int):
        super().__init__()
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied_mutation = None

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        if self.current_idx == self.target_idx:
            if isinstance(node.op, ast.And):
                node.op = ast.Or()
            else:
                node.op = ast.And()
            self.applied_mutation = (
                f"Boolean operator flipped at line {getattr(node, 'lineno', '?')}"
            )
        self.current_idx += 1
        return self.generic_visit(node)


class IfNegationMutator(ast.NodeTransformer):
    """Negates an `if` condition (`if x:` -> `if not x:`)."""

    def __init__(self, target_idx: int):
        super().__init__()
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied_mutation = None

    def visit_If(self, node: ast.If) -> ast.AST:
        if self.current_idx == self.target_idx:
            node.test = ast.copy_location(
                ast.UnaryOp(op=ast.Not(), operand=node.test), node.test
            )
            self.applied_mutation = (
                f"If-condition negated at line {getattr(node, 'lineno', '?')}"
            )
        self.current_idx += 1
        return self.generic_visit(node)


class AugmentedAssignmentMutator(ast.NodeTransformer):
    """Mutates `+=`, `-=`, `*=`, `/=` operators."""

    OP_MAP = {
        ast.Add: ast.Sub,
        ast.Sub: ast.Add,
        ast.Mult: ast.Div,
        ast.Div: ast.Mult,
    }

    def __init__(self, target_idx: int):
        super().__init__()
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied_mutation = None

    def visit_AugAssign(self, node: ast.AugAssign) -> ast.AST:
        op_type = type(node.op)
        if op_type in self.OP_MAP:
            if self.current_idx == self.target_idx:
                mutated_op = self.OP_MAP[op_type]()
                node.op = mutated_op
                self.applied_mutation = (
                    f"Augmented assignment flipped: {op_type.__name__} -> "
                    f"{type(mutated_op).__name__} at line {getattr(node, 'lineno', '?')}"
                )
            self.current_idx += 1
        return self.generic_visit(node)


class ExceptionSwallowMutator(ast.NodeTransformer):
    """Wraps a function body in `try: ... except Exception: pass`."""

    def __init__(self, target_idx: int):
        super().__init__()
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied_mutation = None

    def _mutate_function(self, node):
        if self.current_idx == self.target_idx:
            body = list(node.body)
            docstring: List[ast.stmt] = []
            if body and isinstance(body[0], ast.Expr) and isinstance(
                body[0].value, ast.Constant
            ) and isinstance(body[0].value.value, str):
                docstring = [body[0]]
                body = body[1:]
            if body:
                handler = ast.ExceptHandler(
                    type=ast.Name(id="Exception", ctx=ast.Load()),
                    name=None,
                    body=[ast.Pass()],
                )
                try_node = ast.Try(body=body, handlers=[handler],
                                   orelse=[], finalbody=[])
                node.body = docstring + [try_node]
                self.applied_mutation = (
                    f"Function '{getattr(node, 'name', '?')}' body wrapped in "
                    f"try/except Exception: pass at line {getattr(node, 'lineno', '?')}"
                )
        self.current_idx += 1
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return self._mutate_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self._mutate_function(node)


def _family(
    tree: ast.AST,
    source_code: str,
    mutator_cls,
    count: int,
    family_name: str,
    prefix: str,
) -> List[Dict[str, Any]]:
    """Generate all mutants for one operator family."""
    out: List[Dict[str, Any]] = []
    for idx in range(count):
        tree_copy = copy.deepcopy(tree)
        mutator = mutator_cls(target_idx=idx)
        mutated_tree = mutator.visit(tree_copy)
        ast.fix_missing_locations(mutated_tree)
        try:
            mutated_code = ast.unparse(mutated_tree)
        except Exception:
            continue
        if not mutator.applied_mutation:
            continue
        diff = "".join(difflib.unified_diff(
            source_code.splitlines(keepends=True),
            mutated_code.splitlines(keepends=True),
            fromfile="original.py",
            tofile=f"mutant_{prefix}_{idx}.py",
        ))
        out.append({
            "type": family_name,
            "description": mutator.applied_mutation,
            "mutated_code": mutated_code,
            "diff": diff,
        })
    return out


def _count_comparisons(tree: ast.AST) -> int:
    return sum(len(node.ops) for node in ast.walk(tree)
               if isinstance(node, ast.Compare))


def _count_bool_constants(tree: ast.AST) -> int:
    return sum(1 for node in ast.walk(tree)
               if isinstance(node, ast.Constant) and isinstance(node.value, bool))


def _count_returns(tree: ast.AST) -> int:
    return sum(1 for node in ast.walk(tree) if isinstance(node, ast.Return))


def _count_arithmetic(tree: ast.AST) -> int:
    return sum(1 for node in ast.walk(tree)
               if isinstance(node, ast.BinOp)
               and type(node.op) in ArithmeticMutator.OP_MAP)


def _count_bool_ops(tree: ast.AST) -> int:
    return sum(1 for node in ast.walk(tree) if isinstance(node, ast.BoolOp))


def _count_ifs(tree: ast.AST) -> int:
    return sum(1 for node in ast.walk(tree) if isinstance(node, ast.If))


def _count_augassigns(tree: ast.AST) -> int:
    return sum(1 for node in ast.walk(tree)
               if isinstance(node, ast.AugAssign)
               and type(node.op) in AugmentedAssignmentMutator.OP_MAP)


def _count_functions(tree: ast.AST) -> int:
    return sum(1 for node in ast.walk(tree)
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
               and len(node.body) > 0)


def generate_mutants(source_code: str) -> List[Dict[str, Any]]:
    """Return distinct, syntactically valid mutated versions of source_code."""
    tree = ast.parse(source_code)

    families = [
        (ComparisonMutator, _count_comparisons(tree), "ComparisonOperator", "comp"),
        (BooleanMutator, _count_bool_constants(tree), "BooleanFlip", "bool"),
        (ReturnMutator, _count_returns(tree), "ReturnNullification", "return"),
        (ArithmeticMutator, _count_arithmetic(tree), "ArithmeticOperator", "arith"),
        (BooleanOperatorMutator, _count_bool_ops(tree), "BooleanOperator", "boolop"),
        (IfNegationMutator, _count_ifs(tree), "IfNegation", "ifneg"),
        (AugmentedAssignmentMutator, _count_augassigns(tree),
         "AugmentedAssignment", "augassign"),
        (ExceptionSwallowMutator, _count_functions(tree), "ExceptionSwallow", "swallow"),
    ]

    mutants: List[Dict[str, Any]] = []
    for mutator_cls, count, name, prefix in families:
        mutants.extend(_family(tree, source_code, mutator_cls, count, name, prefix))

    # Deduplicate identical mutated programs while preserving family order.
    unique: List[Dict[str, Any]] = []
    seen = set()
    for mutant in mutants:
        key = mutant["mutated_code"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(mutant)
    return unique


if __name__ == "__main__":
    sample_code = """def is_authenticated(user_role, is_banned, login_attempts):
    if is_banned == True:
        return False
    if login_attempts >= 5:
        return False
    if user_role == 'admin' and login_attempts > 0:
        return True
    return False
"""
    print("Original Code:\n" + sample_code)
    results = generate_mutants(sample_code)
    print(f"\n[Generated {len(results)} AST Mutants]:")
    for idx, m in enumerate(results, 1):
        print(f"\n--- Mutant #{idx} [{m['type']}] ---")
        print(f"Details: {m['description']}")
        print(m["diff"])
