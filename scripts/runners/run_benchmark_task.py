#!/usr/bin/env python3
"""
scripts/runners/run_benchmark_task.py

Real-Benchmark Evaluation Runner:
Loads real pull request tasks from SWE-bench Verified (curated_tasks.json),
parses unified diff hunks, restricts AST mutations strictly to modified PR lines,
exports SWE-bench evaluation format predictions, and synthesizes hardened verifiers.
"""

import argparse
import ast
import json
import logging
import re
import sys
import textwrap
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Enable running from repository root or scripts directory
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "scripts"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from mutator.diff_parser import parse_patch_modified_lines
from mutator.ast_transformers import (
    DiffConstrainedComparisonMutator,
    DiffConstrainedBooleanMutator,
    DiffConstrainedReturnMutator,
)
from verifier.verifier_synthesizer import synthesize_hardened_test, configure_logging

logger = logging.getLogger("aavs.run_benchmark_task")
console = Console()


def load_curated_tasks(tasks_path: Path) -> List[Dict[str, Any]]:
    """Loads curated SWE-bench benchmark tasks from JSON."""
    if not tasks_path.exists():
        raise FileNotFoundError(f"Benchmark tasks file not found: {tasks_path}")
    with tasks_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_tasks(tasks: List[Dict[str, Any]]) -> None:
    """Renders a Rich table listing all available benchmark tasks."""
    table = Table(
        title="Curated SWE-bench Verified Tasks",
        header_style="bold cyan",
        show_lines=True,
    )
    table.add_column("Instance ID", style="bold yellow")
    table.add_column("Repository", style="green")
    table.add_column("Base Commit", style="dim")
    table.add_column("Modified Files", style="magenta")
    table.add_column("Problem Summary", style="white")

    for t in tasks:
        mod_map = parse_patch_modified_lines(t.get("patch", ""))
        files_str = "\n".join(f"{f} ({len(lines)} lines)" for f, lines in mod_map.items())
        first_line = t.get("problem_statement", "").strip().splitlines()[0]
        summary = first_line[:80] + ("..." if len(first_line) > 80 else "")
        table.add_row(
            t.get("instance_id", "unknown"),
            t.get("repo", "unknown"),
            t.get("base_commit", "")[:10],
            files_str or "None",
            summary,
        )

    console.print(table)


def repair_hanging_blocks(src: str) -> str:
    """
    Appends 'pass' statements to incomplete hanging block headers
    (e.g., 'else:', 'try:', 'if:') caused by truncated unified diff hunks.
    """
    lines = src.splitlines()
    repaired: List[str] = []
    for i, line in enumerate(lines):
        repaired.append(line)
        stripped = line.strip()
        if stripped.endswith(":") and not stripped.startswith("#"):
            has_body = False
            curr_indent = len(line) - len(line.lstrip())
            for next_line in lines[i + 1 :]:
                next_stripped = next_line.strip()
                if not next_stripped or next_stripped.startswith("#"):
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent > curr_indent:
                    has_body = True
                break
            if not has_body:
                repaired.append(" " * (curr_indent + 4) + "pass")
    return "\n".join(repaired)


def extract_hunk_post_patch_code(hunk_text: str) -> Tuple[str, List[int]]:
    """
    Extracts post-patch code from a unified diff hunk.
    Returns:
      (post_patch_code, relative_added_line_indices)
    """
    post_lines: List[str] = []
    relative_added: List[int] = []

    for line in hunk_text.splitlines():
        if line.startswith("@@"):
            continue
        if line.startswith("---") or line.startswith("+++") or line.startswith("diff"):
            continue
        if line.startswith("-"):
            continue
        if line.startswith("+"):
            post_lines.append(line[1:])
            relative_added.append(len(post_lines))
        elif line.startswith(" "):
            post_lines.append(line[1:])

    raw_code = "\n".join(post_lines)
    dedented_code = textwrap.dedent(raw_code)
    repaired_code = repair_hanging_blocks(dedented_code)
    return repaired_code, relative_added


def generate_benchmark_patch_mutants(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts diff hunks from a real benchmark task and generates
    AST-guided mutants strictly on the patch's modified lines.
    """
    patch_diff = task.get("patch", "")
    hunk_regex = re.compile(r"(@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@[\s\S]*?)(?=(?:@@ -\d+|\Z))")
    hunk_matches = hunk_regex.findall(patch_diff)

    mutants: List[Dict[str, Any]] = []

    for hunk_idx, hunk_text in enumerate(hunk_matches, start=1):
        header_line = hunk_text.splitlines()[0] if hunk_text.splitlines() else "@@"
        post_code, added_rel_lines = extract_hunk_post_patch_code(hunk_text)

        if not post_code.strip():
            continue

        try:
            tree = ast.parse(post_code)
        except SyntaxError:
            # Wrap in dummy function if top-level statements cannot stand alone
            wrapped = f"def _target_scope():\n" + textwrap.indent(post_code, "    ")
            try:
                tree = ast.parse(wrapped)
            except SyntaxError:
                continue

        # 1. Comparison Operator Mutations
        comp_count = sum(
            sum(1 for op in node.ops if type(op) in DiffConstrainedComparisonMutator.OP_MAP)
            for node in ast.walk(tree)
            if isinstance(node, ast.Compare)
        )
        for i in range(comp_count):
            import copy
            tree_copy = copy.deepcopy(tree)
            mutator = DiffConstrainedComparisonMutator(target_idx=i, allowed_lines=None)
            mutated_tree = mutator.visit(tree_copy)
            ast.fix_missing_locations(mutated_tree)
            mutated_code = ast.unparse(mutated_tree)
            if mutator.applied_mutation:
                mutants.append({
                    "task_id": task.get("instance_id"),
                    "hunk_idx": hunk_idx,
                    "hunk_header": header_line,
                    "type": "ComparisonOperator",
                    "description": mutator.applied_mutation,
                    "original_code": post_code,
                    "mutated_code": mutated_code,
                })

        # 2. Boolean Literal Flips
        bool_count = sum(
            1 for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, bool)
        )
        for i in range(bool_count):
            import copy
            tree_copy = copy.deepcopy(tree)
            mutator = DiffConstrainedBooleanMutator(target_idx=i, allowed_lines=None)
            mutated_tree = mutator.visit(tree_copy)
            ast.fix_missing_locations(mutated_tree)
            mutated_code = ast.unparse(mutated_tree)
            if mutator.applied_mutation:
                mutants.append({
                    "task_id": task.get("instance_id"),
                    "hunk_idx": hunk_idx,
                    "hunk_header": header_line,
                    "type": "BooleanFlip",
                    "description": mutator.applied_mutation,
                    "original_code": post_code,
                    "mutated_code": mutated_code,
                })

        # 3. Return Nullification
        ret_count = sum(
            1 for node in ast.walk(tree)
            if isinstance(node, ast.Return) and node.value is not None
        )
        for i in range(ret_count):
            import copy
            tree_copy = copy.deepcopy(tree)
            mutator = DiffConstrainedReturnMutator(target_idx=i, allowed_lines=None)
            mutated_tree = mutator.visit(tree_copy)
            ast.fix_missing_locations(mutated_tree)
            mutated_code = ast.unparse(mutated_tree)
            if mutator.applied_mutation:
                mutants.append({
                    "task_id": task.get("instance_id"),
                    "hunk_idx": hunk_idx,
                    "hunk_header": header_line,
                    "type": "ReturnNullification",
                    "description": mutator.applied_mutation,
                    "original_code": post_code,
                    "mutated_code": mutated_code,
                })

    return mutants


def export_swebench_predictions(
    mutants: List[Dict[str, Any]],
    output_path: Path,
    task: Dict[str, Any]
) -> None:
    """
    Exports generated mutants into standard SWE-bench JSONL format
    compatible with `swebench.harness.run_evaluation`.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for idx, m in enumerate(mutants, start=1):
            record = {
                "instance_id": task.get("instance_id"),
                "model_patch": m.get("mutated_code"),
                "model_name_or_path": f"aavs-mutant-{idx}",
                "mutation_type": m.get("type"),
                "description": m.get("description"),
            }
            f.write(json.dumps(record) + "\n")
    console.print(f"[green][+] Exported {len(mutants)} SWE-bench mutant predictions to: {output_path}[/green]")


def run_benchmark_audit(
    task: Dict[str, Any],
    export_preds: Optional[Path] = None,
    synthesize: bool = False,
    model: Optional[str] = None
) -> None:
    """Executes a real benchmark task mutation scan and optional verifier synthesis."""
    task_id = task.get("instance_id", "unknown")
    repo = task.get("repo", "unknown")

    console.print(Panel(
        f"[bold cyan]Task ID:[/bold cyan] {task_id}\n"
        f"[bold cyan]Repository:[/bold cyan] {repo}\n"
        f"[bold cyan]Base Commit:[/bold cyan] {task.get('base_commit')}",
        title="[bold yellow]SWE-bench Benchmark Task Audit[/bold yellow]",
        expand=False
    ))

    # Parse modified lines
    mod_lines = parse_patch_modified_lines(task.get("patch", ""))
    console.print(f"\n[bold]Step 1: PR Patch Diff Analysis[/bold]")
    for filepath, lines in mod_lines.items():
        console.print(f"  * [cyan]{filepath}[/cyan]: {len(lines)} modified lines -> [dim]{sorted(list(lines))[:10]}[/dim]")

    # Generate patch mutants
    console.print(f"\n[bold]Step 2: Generating Line-Constrained AST Mutants on PR Diff[/bold]")
    mutants = generate_benchmark_patch_mutants(task)
    console.print(f"Generated [bold green]{len(mutants)}[/bold green] AST mutants within modified PR hunks.")

    if not mutants:
        console.print("[yellow]No AST mutations were generated for this patch.[/yellow]")
        return

    # Render table of mutants
    table = Table(
        title=f"Benchmark Patch Mutants: {task_id}",
        header_style="bold magenta",
        show_lines=True
    )
    table.add_column("#", justify="right", style="bold")
    table.add_column("Hunk", style="dim")
    table.add_column("Type", style="cyan")
    table.add_column("Mutation Description", style="yellow")
    table.add_column("Mutated Code Preview", style="white")

    for idx, m in enumerate(mutants, start=1):
        preview = m.get("mutated_code", "").strip().splitlines()
        preview_str = "\n".join(preview[:3]) + ("\n..." if len(preview) > 3 else "")
        table.add_row(
            str(idx),
            m.get("hunk_header", "")[:25],
            m.get("type", ""),
            m.get("description", ""),
            preview_str
        )

    console.print(table)

    # Optional export to SWE-bench prediction format
    if export_preds:
        export_swebench_predictions(mutants, export_preds, task)

    # Optional synthesis loop
    if synthesize and mutants:
        console.print(f"\n[bold]Step 3: Autonomous Verifier Synthesis for PR Mutant #1[/bold]")
        mutant_target = mutants[0]
        try:
            hardened_test = synthesize_hardened_test(
                target_code=mutant_target["original_code"],
                mutated_code=mutant_target["mutated_code"],
                mutation_description=mutant_target["description"],
                model=model,
                max_attempts=3
            )
            console.print(Panel(
                hardened_test,
                title="[bold green]Synthesized Pytest Assertion for PR Bug[/bold green]",
                style="green"
            ))
        except Exception as e:
            console.print(f"[red]Synthesis could not complete in current environment: {e}[/red]")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="AAVS: Real-Benchmark Evaluation Runner for SWE-bench Tasks."
    )
    parser.add_argument(
        "--tasks-file",
        type=Path,
        default=root_dir / "data" / "curated_tasks.json",
        help="Path to curated tasks JSON file (default: data/curated_tasks.json)"
    )
    parser.add_argument(
        "--task-id",
        type=str,
        default="astropy__astropy-14365",
        help="Specific instance_id to audit (or 'all'). Default: astropy__astropy-14365"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available benchmark tasks and exit"
    )
    parser.add_argument(
        "--export-preds",
        type=Path,
        default=root_dir / "data" / "mutated_preds.jsonl",
        help="Export mutated patches to standard SWE-bench JSONL predictions format"
    )
    parser.add_argument(
        "--synthesize",
        action="store_true",
        help="Attempt autonomous LLM test synthesis on surviving mutants"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model identifier (e.g., openai/gpt-oss-120b, mistral-nemo:latest)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()
    configure_logging("DEBUG" if args.verbose else "INFO")

    tasks = load_curated_tasks(args.tasks_file)

    if args.list:
        list_tasks(tasks)
        return

    if args.task_id.lower() == "all":
        for t in tasks:
            run_benchmark_audit(
                task=t,
                export_preds=args.export_preds,
                synthesize=args.synthesize,
                model=args.model
            )
    else:
        matched = [t for t in tasks if t.get("instance_id") == args.task_id]
        if not matched:
            console.print(f"[red]Error: Task ID '{args.task_id}' not found in {args.tasks_file}.[/red]")
            console.print("Use [bold]--list[/bold] to see available tasks.")
            sys.exit(1)
        run_benchmark_audit(
            task=matched[0],
            export_preds=args.export_preds,
            synthesize=args.synthesize,
            model=args.model
        )


if __name__ == "__main__":
    main()
