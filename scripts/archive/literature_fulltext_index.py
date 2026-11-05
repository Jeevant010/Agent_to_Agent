#!/usr/bin/env python3
"""Scan extracted full texts for AAVS signal terms.

Outputs:
  papers/metadata/fulltext_index.csv  - one row per paper with signal counts
  docs/FULLTEXT_SIGNAL_INDEX.md       - corpus-level term coverage + top papers

This is a lexical index, not a semantic reading. It is designed to make the
1,112 extracted texts navigable and to show which papers actually discuss the
mechanisms AAVS depends on.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "papers" / "metadata" / "papers_corpus.jsonl"
OUT_CSV = ROOT / "papers" / "metadata" / "fulltext_index.csv"
OUT_MD = ROOT / "docs" / "archive" / "FULLTEXT_SIGNAL_INDEX.md"

GROUPS = {
    "benchmarks": ["swe-bench", "swebench", "humaneval", "mbpp", "livecodebench",
                   "bigcodebench", "terminal-bench", "deepswe", "multi-swe-bench"],
    "mutation": ["mutation testing", "mutation score", "mutant", "equivalent mutant",
                 "mutation operator", "coupling effect"],
    "oracles": ["test oracle", "oracle problem", "assertion generation",
                "test generation", "property-based", "differential testing",
                "metamorphic testing"],
    "failure_modes": ["reward hacking", "specification gaming", "false positive",
                      "overfitting", "data contamination", "flaky test",
                      "shortcut"],
    "agents": ["coding agent", "swe-agent", "agentless", "openhands", "llm agent",
               "software engineering agent", "autonomous agent"],
    "security": ["vulnerability", "cwe", "secure code", "insecure code",
                 "security patch", "memory safety"],
    "verification": ["verifier", "soundness", "completeness", "dual execution",
                     "execution feedback", "sandbox", "reward model"],
}

GROUP_RE = {name: re.compile("|".join(re.escape(t) for t in terms), re.I)
            for name, terms in GROUPS.items()}
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\s?%")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'])")


def load_corpus() -> list[dict]:
    return [json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()]


def best_sentence(text: str) -> str:
    sentences = SENTENCE_RE.split(re.sub(r"\s+", " ", text))
    scored = []
    for sent in sentences:
        if not (80 <= len(sent) <= 420):
            continue
        score = sum(len(rx.findall(sent)) for rx in GROUP_RE.values())
        if score:
            scored.append((score, sent))
    if not scored:
        return ""
    return max(scored, key=lambda pair: pair[0])[1][:360]


def main() -> None:
    rows = load_corpus()
    out = []
    totals = Counter()
    coverage = Counter()
    for rec in rows:
        text_path = rec.get("text_path")
        if rec.get("text_status") != "ok" or not text_path:
            continue
        path = ROOT / text_path
        if not path.exists():
            continue
        text = path.read_text(errors="ignore")
        counts = {name: len(rx.findall(text)) for name, rx in GROUP_RE.items()}
        total = sum(counts.values())
        for name, value in counts.items():
            if value:
                coverage[name] += 1
            totals[name] += value
        out.append({
            "corpus_id": rec.get("corpus_id"),
            "title": rec.get("title"),
            "year": rec.get("year"),
            "tier": rec.get("tier"),
            "score": rec.get("score"),
            "cluster": rec.get("cluster"),
            "chars": len(text),
            "percent_claims": len(NUMBER_RE.findall(text)),
            "total_signals": total,
            **{f"n_{k}": v for k, v in counts.items()},
            "best_sentence": best_sentence(text),
        })

    out.sort(key=lambda r: (r["total_signals"], r["score"] or 0), reverse=True)
    fields = ["corpus_id", "title", "year", "tier", "score", "cluster", "chars",
              "percent_claims", "total_signals",
              *[f"n_{k}" for k in GROUPS], "best_sentence"]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)

    lines = [
        "# Full-Text Signal Index",
        "",
        f"**Scope:** {len(out)} papers with extracted text (of {len(rows)} corpus records).  ",
        "**Method:** case-insensitive lexical counts over `papers/text/*.txt`, plus the "
        "highest-signal sentence per paper. This is a navigation aid, not a semantic "
        "judgement.",
        "",
        "## Term coverage",
        "",
        "| Signal group | Papers mentioning it | Total mentions |",
        "| :--- | ---: | ---: |",
    ]
    for name in GROUPS:
        lines.append(f"| {name} | {coverage[name]} | {totals[name]} |")
    lines += [
        "",
        "## Top 100 by signal density",
        "",
        "| # | ID | Tier | Year | Signals | % claims | Paper | Best sentence |",
        "| ---: | :--- | :--- | ---: | ---: | ---: | :--- | :--- |",
    ]
    for idx, row in enumerate(out[:100], 1):
        title = (row["title"] or "").replace("|", "\\|")
        sentence = (row["best_sentence"] or "").replace("|", "\\|")
        lines.append(
            f"| {idx} | {row['corpus_id']} | {row['tier']} | {row['year']} | "
            f"{row['total_signals']} | {row['percent_claims']} | {title} | {sentence} |")
    lines += [
        "",
        "## Notes",
        "",
        "- Signal counts are inflated by bibliographies and related-work sections; use them "
        "to rank, then read the PDF.",
        "- `percent_claims` counts percentage tokens, not verified results.",
        "- The complete per-paper index is `papers/metadata/fulltext_index.csv`.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"scanned {len(out)} texts")
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_MD}")
    print("coverage:", dict(coverage))


if __name__ == "__main__":
    main()
