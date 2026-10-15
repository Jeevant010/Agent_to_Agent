#!/usr/bin/env python3
"""
scripts/verifier_gate.py

The Dual-Execution Judge for Bi-Directional Verifier Validation:
  1. Soundness: Candidate test must strictly PASS on reference gold implementation.
  2. Completeness: Candidate test must strictly FAIL on the mutated implementation.
"""

from typing import Dict, Any
from sandbox import execute_in_sandbox


def validate_bi_directional_criteria(
    gold_code: str,
    mutant_code: str,
    test_code: str
) -> Dict[str, Any]:
    """
    The Dual-Execution Judge.
    Strictly verifies that:
      1. test_code passes on gold_code (Soundness)
      2. test_code fails on mutant_code (Completeness / Mutant Killed)
    """
    gold_pass, gold_log = execute_in_sandbox(gold_code, test_code)
    mutant_pass, mutant_log = execute_in_sandbox(mutant_code, test_code)

    is_sound = gold_pass
    killed_mutant = not mutant_pass
    is_valid = is_sound and killed_mutant

    return {
        "is_valid": is_valid,
        "is_sound": is_sound,
        "killed_mutant": killed_mutant,
        "gold_log": gold_log.strip(),
        "mutant_log": mutant_log.strip()
    }
