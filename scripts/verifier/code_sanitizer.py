#!/usr/bin/env python3
"""
scripts/code_sanitizer.py

AST-based code extraction, sanitization, and verification:
  - Extracts target function names from reference code via Python AST
  - Strips markdown code fences and chain-of-thought (<think>) blocks
  - Deduplicates repetitive import statements
  - Validates syntactic correctness using ast.parse
"""

import re
import ast


def extract_target_function_name(code: str) -> str:
    """Extracts the first top-level function identifier from Python source code via AST."""
    try:
        parsed = ast.parse(code)
        for node in parsed.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return node.name
    except Exception:
        pass
    return "target_function"


def sanitize_code_output(raw_output: str) -> str:
    """
    Extracts executable Python code from markdown code fences or raw output,
    validating syntactic correctness via Python AST.
    """
    code = raw_output.strip()

    # Strip <think>...</think> reasoning blocks if emitted by reasoning models
    code = re.sub(r"<think>[\s\S]*?</think>", "", code).strip()

    match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", code)
    if match:
        code = match.group(1).strip()
    elif "def test_" in code:
        import_match = re.search(r"((?:from\s+\S+\s+import|import\s+\S+|def\s+test_)[\s\S]*)", code)
        if import_match:
            code = import_match.group(1).strip()

    if not code or "def test_" not in code:
        raise ValueError("Model output did not contain a valid test function (`def test_...`).")

    # Deduplicate repeated identical import statements emitted by models
    deduped_lines = []
    seen_imports = set()
    for line in code.splitlines():
        trimmed = line.strip()
        if re.match(r"^(?:from\s+\S+\s+import|import\s+\S+)", trimmed):
            if trimmed in seen_imports:
                continue
            seen_imports.add(trimmed)
        deduped_lines.append(line)
    code = "\n".join(deduped_lines).strip()

    try:
        ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Synthesized code contains invalid Python syntax: {e}")

    return code
