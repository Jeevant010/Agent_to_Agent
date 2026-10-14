#!/usr/bin/env python3
"""
scripts/verifier_synthesizer.py

Orchestrates Autonomous Verifier Synthesis (AAVS):
Prompts an LLM to generate targeted assertions for surviving AST mutants,
enforcing bi-directional validity through an isolated dual-sandbox judge.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure scripts directory is in sys.path for internal imports
sys.path.insert(0, str(Path(__file__).parent))

from llm_client import LLMClient, load_env_file
from code_sanitizer import extract_target_function_name, sanitize_code_output
from sandbox import execute_in_sandbox
from verifier_gate import validate_bi_directional_criteria

logger = logging.getLogger("aavs.verifier_synthesizer")


def configure_logging(level: Optional[str] = None) -> None:
    """Configures structured console logging across the verifier synthesizer."""
    log_level_str = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


SYNTHESIS_PROMPT_TEMPLATE = """You are an automated verification engineer hardening a benchmark test suite.
A semantic bug was injected into the reference implementation, but the existing test suite failed to catch it.

### Target Reference Implementation (Correct Logic):
```python
{gold_code}
```

### Mutated Implementation (Contains Injected Bug):
Bug Description: {mutation_description}
```python
{mutant_code}
```

### Your Objective:
Write a single, standalone pytest function that:
1. Imports the target function: `from target import {func_name}`
2. PASSES when executed against the Reference Implementation.
3. FAILS (raises an AssertionError) when executed against the Mutated Implementation by asserting the specific boundary or logical condition that was corrupted.

### Format Requirements:
- Return ONLY valid Python code starting with `def test_...():`.
- Do NOT include any markdown explanations, commentary, or extra prose.
- Make the test minimal and deterministic (no random data, no external network calls).
"""


def synthesize_hardened_test(
    gold_code: str,
    mutant_code: str,
    mutation_description: str,
    func_name: Optional[str] = None,
    client: Optional[LLMClient] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Main entry point for verifier synthesis.
    Iteratively prompts the LLM and validates output until a valid test is synthesized
    or retry budget is exhausted.
    """
    target_func = func_name or extract_target_function_name(gold_code)
    client = client or LLMClient()
    prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
        gold_code=gold_code.strip(),
        mutant_code=mutant_code.strip(),
        mutation_description=mutation_description,
        func_name=target_func
    )

    logger.info("Initiating verifier synthesis: func='%s', model='%s' (%s)", target_func, client.model, client.provider)
    logger.debug("Target Mutation: %s", mutation_description)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Attempt %d/%d: Querying model '%s'...", attempt, max_retries, client.model)
            raw_output = client.generate(prompt)
            logger.debug("Attempt %d - Raw model output:\n%s", attempt, raw_output.strip())

            clean_test = sanitize_code_output(raw_output)
            logger.debug("Attempt %d - Sanitized pytest code:\n%s", attempt, clean_test.strip())

            validation = validate_bi_directional_criteria(gold_code, mutant_code, clean_test)

            soundness_status = "PASS" if validation["is_sound"] else "FAIL"
            completeness_status = "KILLED" if validation["killed_mutant"] else "SURVIVED"
            logger.info(
                "Attempt %d - Sandbox validation: Soundness=%s, Completeness=%s",
                attempt,
                soundness_status,
                completeness_status
            )

            if validation["is_valid"]:
                logger.info("Attempt %d: Test verified and accepted by dual sandbox.", attempt)
                return {
                    "success": True,
                    "attempt": attempt,
                    "test_code": clean_test,
                    "validation": validation
                }

            if not validation["is_sound"]:
                logger.warning("Attempt %d: Generated test failed soundness on reference implementation.", attempt)
                logger.debug("Attempt %d - Reference failure log:\n%s", attempt, validation["gold_log"].strip())
                prompt += f"\n\n[Attempt {attempt} Failed]: Your generated test FAILED on the reference gold implementation. Log:\n{validation['gold_log']}\nFix the test so it strictly passes on the reference code."
            elif not validation["killed_mutant"]:
                logger.warning("Attempt %d: Generated test failed completeness; mutant survived.", attempt)
                logger.debug("Attempt %d - Mutant failure log:\n%s", attempt, validation["mutant_log"].strip())
                prompt += f"\n\n[Attempt {attempt} Failed]: Your generated test PASSED on the mutated implementation (it failed to kill the mutant). Assert the specific corrupted condition."

        except RuntimeError as e:
            logger.error("Attempt %d backend error: %s", attempt, e)
            return {
                "success": False,
                "attempt": attempt,
                "error": str(e),
                "test_code": None
            }
        except Exception as e:
            logger.error("Attempt %d syntax or execution error: %s", attempt, e)
            prompt += f"\n\n[Attempt {attempt} Error]: {str(e)}. Provide clean, valid Python pytest code."

    logger.error("Failed to synthesize a valid test within retry budget of %d attempts.", max_retries)
    return {
        "success": False,
        "attempt": max_retries,
        "error": "Failed to synthesize a valid test within retry budget.",
        "test_code": None
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous Verifier Synthesizer")
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO, or set via LOG_LEVEL env var)"
    )
    args = parser.parse_args()
    configure_logging(args.log_level)

    logger.info("Starting Verifier Synthesizer on sample mutant...")

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

    if result["success"]:
        logger.info("Synthesis Succeeded on Attempt %d:\n%s", result["attempt"], result["test_code"])
        logger.info(
            "Bi-Directional Validation: Soundness=%s, Completeness=%s",
            result["validation"]["is_sound"],
            result["validation"]["killed_mutant"]
        )
    else:
        err = result.get("error", "")
        logger.error("Synthesis Failed: %s", err)
        if "No LLM backend available" in err:
            logger.error("Ensure Ollama is running (`ollama serve`) or configure GROQ_KEY / OPENAI_API_KEY in .env.")
        else:
            logger.error("The model responded, but its generated assertions failed the validation gate.")
        sys.exit(1)
