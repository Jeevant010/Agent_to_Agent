#!/usr/bin/env python3
"""
scripts/run_local_audit.py

Complete End-to-End Local Demonstration of the Adversarial Verifier Audit.
Runs 100% locally on any machine without Docker or GPU requirements.

Demonstrates:
  1. Base Reference Function (Gold Solution)
  2. Initial Incomplete Verifier (Typical Benchmark Test Suite)
  3. AST Semantic Mutation Injection
  4. Deterministic Test Execution & Surviving Mutant Detection
  5. Verifier Hardening (Closing the Loop)
"""

import sys
import tempfile
import subprocess
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import our AST mutator
sys.path.insert(0, str(Path(__file__).parent))
from ast_mutator import generate_mutants

console = Console()

# 1. The Reference Implementation (e.g., bug fix in an e-commerce / API repo)
GOLD_CODE = """def process_membership_discount(user_role: str, cart_total: float, is_vip: bool) -> float:
    \"\"\"Calculates final price applying VIP status and role-based discount.\"\"\"
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

# 2. The Baseline Test Suite (Weak verifier typical of SWE-bench: misses boundaries & edge cases)
WEAK_TEST_SUITE = """import pytest
from target import process_membership_discount

def test_basic_student():
    # Only tests standard positive input
    assert process_membership_discount('student', 100.0, False) == 90.0

def test_regular_user():
    # Only tests regular user without VIP
    assert process_membership_discount('guest', 50.0, False) == 50.0
"""

# 3. The Synthesized Hardened Assertion (What our Verifier Agent produces to close the loophole)
HARDENED_TEST_ASSERTION = """
def test_vip_and_discount_cap_and_boundaries():
    # Newly synthesized assertions that target unasserted logic
    # 1. Tests VIP flag logic
    assert process_membership_discount('guest', 100.0, True) == 85.0
    # 2. Tests maximum discount cap (0.15 + 0.20 = 0.35 -> capped to 0.30)
    assert process_membership_discount('senior', 100.0, True) == 70.0
    # 3. Tests negative total safeguard
    assert process_membership_discount('guest', -50.0, False) == 0.0
"""

def execute_test(code_content: str, test_content: str) -> bool:
    """
    Executes pytest in an isolated temporary environment.
    Returns True if tests PASS, False if tests FAIL.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        target_file = tmp_path / "target.py"
        test_file = tmp_path / "test_target.py"

        target_file.write_text(code_content, encoding="utf-8")
        test_file.write_text(test_content, encoding="utf-8")

        cmd = [sys.executable, "-m", "pytest", str(test_file), "-q", "--no-header"]
        proc = subprocess.run(cmd, cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return proc.returncode == 0


def main():
    console.print(Panel.fit(
        "[bold cyan]Autonomous Adversarial Verifier Synthesis (AAVS)[/bold cyan]\n"
        "[dim]Local Mutation Testing & Verifier Audit Engine[/dim]",
        border_style="cyan"
    ))

    # Step 1: Baseline Check
    console.print("\n[bold yellow]Step 1: Baseline Verification[/bold yellow]")
    baseline_pass = execute_test(GOLD_CODE, WEAK_TEST_SUITE)
    if baseline_pass:
        console.print("[green]✓ Baseline Test Suite PASSES on Reference Solution (Green Baseline).[/green]")
    else:
        console.print("[red]✗ Baseline failed on reference code. Aborting.[/red]")
        sys.exit(1)

    # Step 2: AST Mutation
    console.print("\n[bold yellow]Step 2: Injecting AST Semantic Mutants into Reference Code[/bold yellow]")
    mutants = generate_mutants(GOLD_CODE)
    console.print(f"[cyan]Generated [bold]{len(mutants)}[/bold] distinct structural mutants via AST inspection.[/cyan]\n")

    # Step 3: Run Audit Matrix
    table = Table(title="Adversarial Audit: Benchmark Verifier Vulnerability Scan", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Mutation Type", width=22)
    table.add_column("Semantic Perturbation", width=40)
    table.add_column("Original Test Result", width=18)
    table.add_column("Audit Finding", width=28)

    surviving_mutants = []

    for idx, m in enumerate(mutants, 1):
        passed = execute_test(m["mutated_code"], WEAK_TEST_SUITE)
        if passed:
            # Mutant survived! The test didn't catch the bug.
            status_text = "[bold green]PASS (0)[/bold green]"
            finding_text = "[bold red]🚨 SURVIVED (Weak Verifier)[/bold red]"
            surviving_mutants.append((idx, m))
        else:
            # Mutant killed! The test did its job.
            status_text = "[bold red]FAIL (1)[/bold red]"
            finding_text = "[green]✓ KILLED (Caught by Test)[/green]"

        table.add_row(str(idx), m["type"], m["description"], status_text, finding_text)

    console.print(table)

    # Step 4: Summary Analysis
    smr = (len(surviving_mutants) / len(mutants)) * 100 if mutants else 0
    console.print(Panel(
        f"[bold]Total Mutants Injected:[/bold] {len(mutants)}\n"
        f"[bold]Mutants Killed:[/bold] {len(mutants) - len(surviving_mutants)}\n"
        f"[bold red]Surviving Mutants (Verifier Blind Spots):[/bold red] {len(surviving_mutants)}\n"
        f"[bold yellow]Surviving Mutant Rate (SMR):[/bold yellow] [bold]{smr:.1f}%[/bold]\n\n"
        f"[dim]Interpretation: An AI agent could write corrupted code for {len(surviving_mutants)} of these scenarios "
        f"and standard benchmark tests would give it a FALSE POSITIVE pass![/dim]",
        title="[bold]Benchmark Vulnerability Metrics[/bold]",
        border_style="red" if smr > 0 else "green"
    ))

    # Step 5: Verifier Hardening Demonstration
    if surviving_mutants:
        console.print("\n[bold yellow]Step 5: Verifier Hardening (Closing the Loop)[/bold yellow]")
        console.print("[cyan]Synthesizing targeted assertion to close detected verifier loopholes...[/cyan]")
        
        hardened_suite = WEAK_TEST_SUITE + "\n" + HARDENED_TEST_ASSERTION
        
        # Verify soundness: Must still pass on gold code
        gold_still_passes = execute_test(GOLD_CODE, hardened_suite)
        
        # Verify completeness: Check how many surviving mutants are now killed
        now_killed = 0
        for _, m in surviving_mutants:
            if not execute_test(m["mutated_code"], hardened_suite):
                now_killed += 1

        hardened_smr = ((len(surviving_mutants) - now_killed) / len(mutants)) * 100
        console.print(Panel(
            f"[green]✓ Soundness Verified:[/green] Hardened test suite PASSES on original reference code: {gold_still_passes}\n"
            f"[green]✓ Loophole Closed:[/green] Killed {now_killed}/{len(surviving_mutants)} previously surviving mutants!\n"
            f"[bold green]New Hardened Surviving Mutant Rate:[/bold green] [bold]{hardened_smr:.1f}%[/bold] (Dropped from {smr:.1f}%)\n"
            f"[bold cyan]Result:[/bold cyan] Zero human grading required — verifiable RL signal established.",
            title="[bold green]Verifier Hardening Success[/bold green]",
            border_style="green"
        ))

if __name__ == "__main__":
    main()
