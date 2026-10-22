"""
scripts/mutator package:
Adversarial AST mutation and diff-aware patch injection.
"""

from .ast_mutator import generate_mutants
from .diff_parser import parse_patch_modified_lines, apply_patch_to_text
from .ast_transformers import (
    DiffConstrainedComparisonMutator,
    DiffConstrainedBooleanMutator,
    DiffConstrainedReturnMutator
)
from .patch_mutator import generate_patch_mutants

__all__ = [
    "generate_mutants",
    "parse_patch_modified_lines",
    "apply_patch_to_text",
    "DiffConstrainedComparisonMutator",
    "DiffConstrainedBooleanMutator",
    "DiffConstrainedReturnMutator",
    "generate_patch_mutants",
]
