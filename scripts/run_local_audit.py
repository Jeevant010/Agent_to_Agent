#!/usr/bin/env python3

import sys
import tempfile
import subprocess
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import our AST mutator and Verifier Synthesizer
sys.path.insert(0, str(Path(__file__).parent))
from ast_mutator import generate_mutants
from verifier_synthesizer import synthesize_hardened_test, configure_logging

console = Console()

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

WEAK_TEST_SUITE = """import pytest
from target import process_membership_discount

def test_basic_student():
    assert process_membership_discount('student', 100.0, False) == 90.0

def test_regular_user():
    assert process_membership_discount('guest', 50.0, False) == 50.0
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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    configure_logging()

    console.print(Panel.fit(
        "[bold cyan]Autonomous Adversarial Verifier Synthesis (AAVS)[/bold cyan]\n"
        "[dim]Local Mutation Testing & Verifier Audit Engine[/dim]",
        border_style="cyan"
    ))

    console.print("\n[bold yellow]Step 1: Baseline Verification[/bold yellow]")
    baseline_pass = execute_test(GOLD_CODE, WEAK_TEST_SUITE)
    if baseline_pass:
        console.print("[green] Baseline Test Suite PASSES on Reference Solution (Green Baseline).[/green]")
    else:
        console.print("[red] Baseline failed on reference code. Aborting.[/red]")
        sys.exit(1)

    console.print("\n[bold yellow]Step 2: Injecting AST Semantic Mutants into Reference Code[/bold yellow]")
    mutants = generate_mutants(GOLD_CODE)
    console.print(f"[cyan]Generated [bold]{len(mutants)}[/bold] distinct structural mutants via AST inspection.[/cyan]\n")

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
            status_text = "[bold green]PASS (0)[/bold green]"
            finding_text = "[bold red] SURVIVED (Weak Verifier)[/bold red]"
            surviving_mutants.append((idx, m))
        else:
            status_text = "[bold red]FAIL (1)[/bold red]"
            finding_text = "[green] KILLED (Caught by Test)[/green]"

        table.add_row(str(idx), m["type"], m["description"], status_text, finding_text)

    console.print(table)

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

    if surviving_mutants:
        console.print("\n[bold yellow]Step 5: Autonomous Verifier Hardening (Closing the Loop)[/bold yellow]")
        synthesis_result = None
        for mut_idx, target_mutant in surviving_mutants:
            console.print(f"[cyan]Dispatching surviving mutant #{mut_idx} to Verifier Synthesizer...[/cyan]")
            synthesis_result = synthesize_hardened_test(
                gold_code=GOLD_CODE,
                mutant_code=target_mutant["mutated_code"],
                mutation_description=target_mutant["description"],
                max_retries=3
            )
            if synthesis_result["success"]:
                break

        if synthesis_result and synthesis_result["success"]:
            synthesized_code = synthesis_result["test_code"]
            console.print(Panel(
                synthesized_code,
                title="[bold green]Synthesized Pytest Assertion (Bi-Directionally Verified)[/bold green]",
                border_style="green"
            ))
            hardened_suite = WEAK_TEST_SUITE + "\n\n" + synthesized_code
        else:
            err = synthesis_result.get("error") if synthesis_result else "No test synthesized."
            console.print(f"\n[bold red]Error:[/bold red] {err}")
            console.print("[bold yellow]Synthesizer could not verify a test. Ensure Ollama is running (`ollama serve`).[/bold yellow]")
            sys.exit(1)
        
        gold_still_passes = execute_test(GOLD_CODE, hardened_suite)
        now_killed = sum(
            1 for _, m in surviving_mutants
            if not execute_test(m["mutated_code"], hardened_suite)
        )

        hardened_smr = ((len(surviving_mutants) - now_killed) / len(mutants)) * 100
        console.print(Panel(
            f"[green] Soundness Verified:[/green] Hardened test suite PASSES on original reference code: {gold_still_passes}\n"
            f"[green] Loophole Closed:[/green] Killed {now_killed}/{len(surviving_mutants)} previously surviving mutants!\n"
            f"[bold green]New Hardened Surviving Mutant Rate:[/bold green] [bold]{hardened_smr:.1f}%[/bold] (Dropped from {smr:.1f}%)\n"
            f"[bold cyan]Result:[/bold cyan] Zero human grading required — verifiable RL signal established.",
            title="[bold green]Verifier Hardening Success[/bold green]",
            border_style="green"
        ))

if __name__ == "__main__":
    main()
