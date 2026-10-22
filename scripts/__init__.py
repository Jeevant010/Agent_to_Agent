"""
scripts package:
Autonomous Adversarial Verifier Synthesis (AAVS) engine:
  - scripts.mutator: AST mutation & unified diff manipulation
  - scripts.verifier: LLM synthesis, dual-sandbox execution & validation gate
  - scripts.runners: Interactive audits & benchmark task extractors
"""

from .mutator import (
    generate_mutants,
    generate_patch_mutants,
    parse_patch_modified_lines,
    apply_patch_to_text,
)
from .verifier import (
    LLMClient,
    load_env_file,
    extract_target_function_name,
    sanitize_code_output,
    execute_in_sandbox,
    validate_bi_directional_criteria,
    synthesize_hardened_test,
    configure_logging,
)

__all__ = [
    "generate_mutants",
    "generate_patch_mutants",
    "parse_patch_modified_lines",
    "apply_patch_to_text",
    "LLMClient",
    "load_env_file",
    "extract_target_function_name",
    "sanitize_code_output",
    "execute_in_sandbox",
    "validate_bi_directional_criteria",
    "synthesize_hardened_test",
    "configure_logging",
]
