#!/usr/bin/env python3
"""Patch-aware AST mutation.

At repository scale, mutating an entire 3,000-line file produces hundreds of
irrelevant mutants. This module parses a unified diff and keeps only mutants
whose target line is an added line in the patch (optionally including context).

Usage:
    python scripts/patch_mutator.py --source fixed.py --patch fix.diff
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))

from ast_mutator import generate_mutants  # noqa: E402

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.M)
LINE_RE = re.compile(r"at line (\d+)")


def parse_added_lines(diff_text: str, target_path: str | None = None) -> set[int]:
    """Return post-patch line numbers of added lines for one file in a diff."""
    current_path = None
    added: set[int] = set()
    new_lineno = 0
    in_hunk = False

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ "):
            current_path = raw_line[4:].strip()
            if current_path.startswith("b/"):
                current_path = current_path[2:]
            in_hunk = False
            continue
        if raw_line.startswith("--- "):
            continue
        match = HUNK_RE.match(raw_line)
        if match:
            new_lineno = int(match.group(1))
            in_hunk = True
            continue
        if not in_hunk:
            continue

        if raw_line.startswith("+"):
            if _path_matches(current_path, target_path):
                added.add(new_lineno)
            new_lineno += 1
        elif raw_line.startswith("-"):
            continue  # deleted line: no post-patch number
        elif raw_line.startswith(" ") or raw_line == "":
            new_lineno += 1
        elif raw_line.startswith("\\"):
            continue
        else:
            # A new file header or end of hunk.
            in_hunk = False

    return added


def _path_matches(current: str | None, target: str | None) -> bool:
    if not target:
        return True
    if not current:
        return False
    current = current.lstrip("./")
    target = target.lstrip("./")
    return current == target or current.endswith("/" + target) or target.endswith("/" + current)


def mutant_line(mutant: dict) -> int | None:
    match = LINE_RE.search(mutant.get("description", ""))
    return int(match.group(1)) if match else None


def filter_mutants_by_lines(mutants: Iterable[dict], lines: set[int]) -> list[dict]:
    """Keep mutants whose mutated node is on a touched post-patch line."""
    kept = []
    for mutant in mutants:
        line = mutant_line(mutant)
        if line is None or line in lines:
            mutant = dict(mutant)
            mutant["patch_line"] = line
            kept.append(mutant)
    return kept


def mutate_patch(source_code: str, diff_text: str, target_path: str | None = None) -> list[dict]:
    """Generate mutants restricted to lines added by the patch."""
    added = parse_added_lines(diff_text, target_path)
    if not added:
        # Deletion-only / context-only patch: fall back to all mutants rather
        # than silently returning nothing.
        return generate_mutants(source_code)
    return filter_mutants_by_lines(generate_mutants(source_code), added)


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch-aware AST mutation")
    parser.add_argument("--source", required=True, help="Post-patch Python file")
    parser.add_argument("--patch", required=True, help="Unified diff for that file")
    parser.add_argument("--path", default=None, help="Path inside the diff to scope to")
    parser.add_argument("--output", default=None, help="Write mutants as JSONL")
    parser.add_argument("--show", action="store_true", help="Print mutant diffs")
    args = parser.parse_args()

    source = Path(args.source).read_text(encoding="utf-8")
    diff_text = Path(args.patch).read_text(encoding="utf-8")
    added = parse_added_lines(diff_text, args.path)
    mutants = mutate_patch(source, diff_text, args.path)

    print(f"touched lines: {sorted(added) if added else 'none (fallback: all)'}")
    print(f"mutants: {len(mutants)}")
    if args.output:
        Path(args.output).write_text(
            "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in mutants),
            encoding="utf-8",
        )
        print(f"wrote {args.output}")
    if args.show:
        for idx, mutant in enumerate(mutants, 1):
            print(f"\n--- #{idx} [{mutant['type']}] {mutant['description']}")
            print(mutant["diff"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
