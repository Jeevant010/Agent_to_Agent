"""End-to-end tests for the local AAVS mutation/verification pipeline.

These tests deliberately avoid any LLM/network dependency: they exercise the
attacker (AST mutator), the sanitizer, the sandbox, and the dual-execution
gate that the synthesizer relies on.
"""

import ast
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ast_mutator import generate_mutants  # noqa: E402
from code_sanitizer import (  # noqa: E402
    extract_target_function_name,
    sanitize_code_output,
)
from sandbox import execute_in_sandbox  # noqa: E402
from verifier_gate import validate_bi_directional_criteria  # noqa: E402
from patch_mutator import (  # noqa: E402
    filter_mutants_by_lines,
    mutate_patch,
    parse_added_lines,
)


GOLD = """def discount(role: str, total: float, vip: bool) -> float:
    if total < 0:
        return 0.0
    rate = 0.0
    if vip == True:
        rate += 0.15
    if role == 'student':
        rate += 0.10
    elif role == 'senior':
        rate += 0.20
    if rate > 0.30:
        rate = 0.30
    return total * (1.0 - rate)
"""

WEAK_TEST = """from target import discount

def test_student():
    assert discount('student', 100.0, False) == 90.0
"""

MUTANT = GOLD.replace("if vip == True:", "if vip == False:")
# A boundary mutation the weak test never exercises: the test only uses
# total=100, so changing `< 0` to `<= 0` survives.
SURVIVING_MUTANT = GOLD.replace("if total < 0:", "if total <= 0:")


class TestAstMutator:
    def test_generates_multiple_mutant_families(self):
        mutants = generate_mutants(GOLD)
        assert len(mutants) >= 4
        kinds = {m["type"] for m in mutants}
        assert {"ComparisonOperator", "BooleanFlip", "ReturnNullification"} <= kinds

    def test_every_mutant_parses_and_differs(self):
        mutants = generate_mutants(GOLD)
        assert mutants
        for mutant in mutants:
            ast.parse(mutant["mutated_code"])
            assert mutant["mutated_code"] != GOLD
            assert mutant["diff"]
            assert mutant["description"]

    def test_no_mutants_for_inert_function(self):
        assert generate_mutants("x = 1\n") == []

    def test_mutants_are_distinct(self):
        mutants = generate_mutants(GOLD)
        codes = [m["mutated_code"] for m in mutants]
        assert len(codes) == len(set(codes))

    def test_comparison_mutation_targets_boundary(self):
        mutants = generate_mutants(GOLD)
        comparisons = [m for m in mutants if m["type"] == "ComparisonOperator"]
        assert comparisons
        descriptions = " ".join(m["description"] for m in comparisons)
        assert "Lt" in descriptions or "Gt" in descriptions


class TestCodeSanitizer:
    def test_extracts_first_top_level_function(self):
        assert extract_target_function_name(GOLD) == "discount"
        assert extract_target_function_name("x = 1") == "target_function"

    def test_strips_markdown_fences(self):
        raw = "Here you go:\n```python\ndef test_x():\n    assert True\n```"
        assert sanitize_code_output(raw).startswith("def test_x")

    def test_strips_think_blocks(self):
        raw = "<think>secret</think>\n```python\ndef test_x():\n    assert True\n```"
        cleaned = sanitize_code_output(raw)
        assert "secret" not in cleaned
        assert "def test_x" in cleaned

    def test_deduplicates_imports(self):
        raw = (
            "```python\nimport os\nimport os\nfrom target import f\n"
            "def test_x():\n    assert True\n```"
        )
        cleaned = sanitize_code_output(raw)
        assert cleaned.count("import os") == 1

    def test_rejects_output_without_test(self):
        with pytest.raises(ValueError):
            sanitize_code_output("def discount():\n    return 1")

    def test_rejects_invalid_syntax(self):
        with pytest.raises(ValueError):
            sanitize_code_output("def test_x(:\n    pass")


class TestSandbox:
    def test_passing_suite_returns_true(self):
        ok, log = execute_in_sandbox(GOLD, WEAK_TEST)
        assert ok, log

    def test_failing_suite_returns_false(self):
        bad = "from target import discount\n\ndef test_bad():\n    assert discount('student', 100.0, False) == 1.0\n"
        ok, log = execute_in_sandbox(GOLD, bad)
        assert not ok
        assert log

    def test_timeout_is_reported(self):
        code = "def f():\n    while True:\n        pass\n"
        test = "from target import f\n\ndef test_hang():\n    f()\n"
        ok, log = execute_in_sandbox(code, test, timeout_sec=1)
        assert not ok
        assert "timed out" in log.lower()


class TestVerifierGate:
    def test_valid_test_passes_gold_and_kills_mutant(self):
        # This test only checks the boolean-vip path, so it passes gold and
        # fails on the mutant where the vip branch is inverted.
        test = (
            "from target import discount\n\n"
            "def test_vip_gets_discount():\n"
            "    assert discount('guest', 100.0, True) == 85.0\n"
        )
        result = validate_bi_directional_criteria(GOLD, MUTANT, test)
        assert result["is_sound"] is True
        assert result["killed_mutant"] is True
        assert result["is_valid"] is True

    def test_weak_test_is_rejected(self):
        # Weak test passes on both versions -> not complete.
        result = validate_bi_directional_criteria(GOLD, SURVIVING_MUTANT, WEAK_TEST)
        assert result["is_sound"] is True
        assert result["killed_mutant"] is False
        assert result["is_valid"] is False

    def test_unsound_test_is_rejected(self):
        bad = "from target import discount\n\ndef test_bad():\n    assert discount('student', 100.0, False) == 1.0\n"
        result = validate_bi_directional_criteria(GOLD, MUTANT, bad)
        assert result["is_sound"] is False
        assert result["is_valid"] is False


PATCH_DIFF = """--- a/target.py
+++ b/target.py
@@ -1,3 +1,5 @@
 def discount(role: str, total: float, vip: bool) -> float:
+    if total < 0:
+        return 0.0
     rate = 0.0
     if vip == True:
"""


class TestPatchMutator:
    def test_parse_added_lines(self):
        added = parse_added_lines(PATCH_DIFF, "target.py")
        assert added == {2, 3}

    def test_path_scoping(self):
        assert parse_added_lines(PATCH_DIFF, "other.py") == set()

    def test_filters_to_touched_lines(self):
        mutants = mutate_patch(GOLD, PATCH_DIFF, "target.py")
        assert mutants
        assert {m["patch_line"] for m in mutants} <= {2, 3}
        assert all(m["patch_line"] in {2, 3} for m in mutants)

    def test_deletion_only_patch_falls_back(self):
        diff = "--- a/target.py\n+++ b/target.py\n@@ -1,2 +1,1 @@\n-x = 1\n y = 2\n"
        mutants = mutate_patch(GOLD, diff, "target.py")
        assert mutants  # fallback to all mutants rather than silent empty

    def test_filter_helper(self):
        mutants = generate_mutants(GOLD)
        kept = filter_mutants_by_lines(mutants, {5})
        assert all(m["patch_line"] == 5 for m in kept)
