#!/usr/bin/env python3
"""
scripts/sandbox.py

Subprocess execution sandbox for running pytest suites against target code in
clean, temporary directories.

This is a *process* sandbox, not a security boundary: generated tests still run
with the current user's permissions. Do not execute untrusted code here without
an OS/container-level isolation layer. For the research pipeline, treat this as
a reproducibility and accidental-damage control, not as protection against a
malicious agent.
"""

import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple


def execute_in_sandbox(code_content: str, test_content: str, timeout_sec: int = 5) -> Tuple[bool, str]:
    """
    Executes a test file against a code file in an isolated temporary directory.
    Returns (True, output) if tests PASS, or (False, output) if tests FAIL.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        target_file = tmp_path / "target.py"
        test_file = tmp_path / "test_synthesized.py"

        # Explicitly ensure target module is on sys.path for test execution.
        # repr() handles quotes/backslashes in the temporary path safely.
        import_wrapper = f"import sys\nsys.path.insert(0, {str(tmpdir)!r})\n\n" + test_content

        target_file.write_text(code_content, encoding="utf-8")
        test_file.write_text(import_wrapper, encoding="utf-8")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-q",
            "--no-header",
            "-o",
            "pythonpath=."
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=tmpdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec
            )
            passed = (proc.returncode == 0)
            combined_output = proc.stdout + proc.stderr
            return passed, combined_output
        except subprocess.TimeoutExpired:
            return False, "Execution timed out (possible infinite loop in mutant)."
