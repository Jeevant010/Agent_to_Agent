"""
scripts/verifier package:
Defender module containing LLM test synthesis, sanitization, sandboxing, and validation gate.
"""

from .llm_client import LLMClient, load_env_file
from .code_sanitizer import extract_target_function_name, sanitize_code_output
from .sandbox import execute_in_sandbox
from .verifier_gate import validate_bi_directional_criteria
from .verifier_synthesizer import synthesize_hardened_test, configure_logging

__all__ = [
    "LLMClient",
    "load_env_file",
    "extract_target_function_name",
    "sanitize_code_output",
    "execute_in_sandbox",
    "validate_bi_directional_criteria",
    "synthesize_hardened_test",
    "configure_logging",
]
