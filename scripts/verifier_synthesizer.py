#!/usr/bin/env python3
"""
scripts/verifier_synthesizer.py (Root Shim)

Delegates directly to scripts.verifier.verifier_synthesizer.
Preserves existing CLI usage: `python scripts/verifier_synthesizer.py`
"""

import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from verifier.verifier_synthesizer import (
    synthesize_hardened_test,
    configure_logging,
    SYNTHESIS_PROMPT_TEMPLATE,
)
from verifier.llm_client import LLMClient, load_env_file
from verifier.code_sanitizer import extract_target_function_name, sanitize_code_output
from verifier.sandbox import execute_in_sandbox
from verifier.verifier_gate import validate_bi_directional_criteria

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Verifier Synthesizer")
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    args = parser.parse_args()
    configure_logging(args.log_level)

    sample_gold = """def process_membership_discount(user_role: str, cart_total: float, is_vip: bool) -> float:
    if cart_total < 0:
        return 0.0
    discount = 0.0
    if is_vip == True:
        discount += 0.15
    if user_role == 'student':
        discount += 0.10
    elif user_role == 'senior':
        discount += 0.20
    if discount > 0.30:
        discount = 0.30
    return cart_total * (1.0 - discount)
"""
    sample_mutant = sample_gold.replace("if is_vip == True:", "if is_vip == False:")
    sample_desc = "Boolean condition inverted: is_vip == True changed to is_vip == False at line 6"

    result = synthesize_hardened_test(
        gold_code=sample_gold,
        mutant_code=sample_mutant,
        mutation_description=sample_desc
    )
    print("Synthesis result:", result["success"])
