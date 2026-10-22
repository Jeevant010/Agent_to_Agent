#!/usr/bin/env python3
"""
scripts/diff_parser.py

Unified diff parser and in-memory text patch applier:
  - Extracts modified line numbers from unified diff hunks (@@ -start,len +start,len @@)
  - Reconstructs post-patch source code from base text and patch diff in memory
"""

import re
from typing import Dict, Set, Optional


def parse_patch_modified_lines(patch_diff: str) -> Dict[str, Set[int]]:
    """
    Parses a unified diff string and returns a mapping:
      { filename: set_of_added_or_modified_line_numbers_in_post_patch_file }
    """
    files_modified_lines: Dict[str, Set[int]] = {}
    current_file: Optional[str] = None
    current_line = 0

    hunk_regex = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

    for line in patch_diff.splitlines():
        if line.startswith("+++ "):
            raw_path = line[4:].strip()
            if raw_path.startswith("b/"):
                raw_path = raw_path[2:]
            elif raw_path.startswith("a/"):
                raw_path = raw_path[2:]
            current_file = raw_path
            if current_file not in files_modified_lines:
                files_modified_lines[current_file] = set()
            continue

        match = hunk_regex.match(line)
        if match:
            current_line = int(match.group(1))
            continue

        if current_file is not None:
            if line.startswith("+") and not line.startswith("+++"):
                files_modified_lines[current_file].add(current_line)
                current_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                pass
            else:
                current_line += 1

    return files_modified_lines


def apply_patch_to_text(original_text: str, patch_diff: str) -> str:
    """
    Applies a single-file unified diff to an original source text string.
    Reconstructs the post-patch source code.
    """
    original_lines = original_text.splitlines()
    patch_lines = patch_diff.splitlines()

    result_lines = []
    orig_idx = 0
    i = 0
    n = len(patch_lines)

    hunk_header_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    while i < n:
        line = patch_lines[i]
        match = hunk_header_re.match(line)
        if match:
            start_orig = int(match.group(1))
            target_idx = start_orig - 1

            while orig_idx < target_idx and orig_idx < len(original_lines):
                result_lines.append(original_lines[orig_idx])
                orig_idx += 1

            i += 1
            while i < n and not patch_lines[i].startswith("@@"):
                h_line = patch_lines[i]
                if h_line.startswith("+") and not h_line.startswith("+++"):
                    result_lines.append(h_line[1:])
                elif h_line.startswith("-") and not h_line.startswith("---"):
                    orig_idx += 1
                elif h_line.startswith(" "):
                    result_lines.append(original_lines[orig_idx])
                    orig_idx += 1
                i += 1
            continue
        i += 1

    while orig_idx < len(original_lines):
        result_lines.append(original_lines[orig_idx])
        orig_idx += 1

    return "\n".join(result_lines) + ("\n" if original_text.endswith("\n") else "")
