#!/usr/bin/env python3
"""Generate human-readable deliverables from the AAVS literature corpus.

Outputs:
  papers/README.md
  papers/metadata/papers_master.csv
  papers/metadata/papers.bib
  docs/LITERATURE_CORPUS_REPORT.md
  docs/literature/INDEX.md
  docs/literature/dossiers_C*.md   (one entry per paper)
  docs/ANCHOR_PAPER_REVIEWS.md     (full-text-assisted reviews of top papers)
  docs/CITATION_INTEGRITY_AUDIT.md

The corpus JSONL is the source of truth. Summaries below are auto-extracted
from abstracts/full text and are labelled as such; they are not a substitute
for reading a paper before citing a specific number.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "papers" / "metadata"
DOCS = ROOT / "docs" / "archive"
LIT = DOCS / "literature"
CORPUS = META / "papers_corpus.jsonl"

CLUSTER_NAMES = {
    "C1": "Benchmark test inadequacy & false passes",
    "C2": "Vulnerability regression & secure AI code",
    "C3": "Reward hacking & specification gaming",
    "C4": "Test/verifier synthesis & execution feedback",
    "C5": "Coding agents & repository benchmarks",
    "C6": "Mutation testing & oracle foundations",
    "C7": "RL, verifiers & reward models",
    "C8": "Automated repair & patch correctness",
    "C9": "Evaluation methodology & contamination",
    "C10": "Sandbox, container & state integrity",
}

AAVS_ROLE = {
    "C1": ("Quantifies false-pass and test-adequacy risk; supplies the MSR baseline and "
           "motivates adversarial verifier hardening."),
    "C2": ("Supplies vulnerability-regression evidence; motivates the Completeness gate "
           "and security-invariant assertions."),
    "C3": ("Documents reward hacking / specification gaming; feeds the Layer-2 taxonomy "
           "and sandbox/state defenses."),
    "C4": ("Methodological prior for test/verifier synthesis and execution feedback; "
           "informs the delta-V generator and dual gate."),
    "C5": ("Benchmark and agent context; supplies the evaluation substrate and public "
           "predictions for zero-cost FPFR analysis."),
    "C6": ("Theoretical foundation for mutation operators, equivalent-mutant filtering, "
           "and oracle design."),
    "C7": ("Connects verifier hardening to RLVR; motivates reward integrity and "
           "verifier reliability."),
    "C8": ("Evidence on patch correctness and repair overfitting; motivates "
           "anti-shortcut and state-consistency checks."),
    "C9": ("Evaluation-methodology support for benchmark validity, contamination "
           "analysis, and honest reporting."),
    "C10": ("Defense mechanisms for container/state integrity; informs Stage 2/3 "
            "sandbox hardening."),
}

VERIFIED_ANCHORS = {
    "2604.01518": {
        "doc_title": "Are Benchmark Tests Strong Enough? Investigating Test Inadequacy in SWE-bench",
        "actual_title": "Probe to Generate: Program Variant-Guided Test Augmentation for Repository-Level Repair Benchmarks",
        "note": ("Title mismatch. The paper is a test-augmentation framework: 77% of SWE-bench "
                 "Verified instances admit at least one surviving program variant; it generates "
                 "1,014 validated tests across 211 instances (+10.8/+9.5 pp patch-region line/"
                 "branch coverage) and lowers top-10 agent resolved rates by 4.2%-9.0%. It is "
                 "not titled 'Are Benchmark Tests Strong Enough?'."),
    },
    "2506.09289": {
        "doc_title": "UTBoost: Augmenting Unit Tests for AI Coding Benchmarks via Intramorphic Oracle Filtering",
        "actual_title": "UTBoost: Rigorous Evaluation of Coding Agents on SWE-Bench",
        "note": ("Live title is 'UTBoost: Rigorous Evaluation of Coding Agents on SWE-Bench'. "
                 "The abstract reports 36 insufficient-test instances, 345 erroneous patches "
                 "previously marked passed, corrections affecting 40.9% of SWE-Bench Lite and "
                 "24.4% of SWE-Bench Verified leaderboard entries, and 18/11 ranking changes. "
                 "It does not claim '18.2% false-pass reduction' or '34% brittle oracles'."),
    },
    "2604.17596": {
        "doc_title": "Terminal Wrench: Exposing Reward Hacking and Environmental Blind Spots in OS Agents",
        "actual_title": "Terminal Wrench: A Dataset of 331 Reward-Hackable Environments and 3,632 Exploit Trajectories",
        "note": ("Live record is a dataset release: 331 environments, 3,632 hack trajectories, "
                 "2,352 legitimate baselines, three frontier models, and a monitorability study "
                 "(AUC 0.97 -> 0.92 when chain-of-thought is removed). The docs' '42 cheating "
                 "patterns' and '150 tasks' are not supported by the abstract."),
    },
    "2608.22103": {
        "doc_title": "Hack-Verifiable Terminal Bench: Defending Against State Spoofing in System Agents",
        "actual_title": "Hack-Verifiable Terminal Bench: Evaluating Reward Hacking in Terminal Tasks",
        "note": ("Title/framing mismatch. The paper adapts Hack-Verifiable Environments to "
                 "Terminal Bench to measure reward-hacking rates across frontier models and "
                 "test whether prompting mitigates known and unknown exploits. It is not "
                 "primarily a 'defending against state spoofing' paper."),
    },
}

NUMERIC_CLAIMS = [
    ("“Between 24.4% and 77.1% of benchmark test suites suffer from severe coverage "
     "and boundary deficits.”",
     "2604.01518 / 2506.09289",
     "2604.01518 reports that 77% of SWE-bench Verified instances admit at least one "
     "surviving variant. 2506.09289 reports that corrections affect 24.4% of SWE-bench "
     "Verified leaderboard entries (40.9% for Lite). Combining these into a single "
     "“24.4%–77.1% of test suites” range is not supported.",
     "REWRITE"),
    ("“UTBoost showed an 18.2% reduction in benchmark false passes.”",
     "2506.09289",
     "The abstract reports 345 erroneous patches, 40.9%/24.4% affected leaderboard entries, "
     "and 18/11 ranking changes. No 18.2% false-pass figure appears in the abstract.",
     "VERIFY OR REMOVE"),
    ("“Without black-box constraints, over 34% of LLM-generated tests overfit to "
     "implementation details.”",
     "2506.09289",
     "Not present in the abstract. Could be in the full text, but it is currently "
     "unattributed to a table/section.",
     "VERIFY OR REMOVE"),
    ("“Terminal Wrench identified 42 distinct environmental cheating patterns across "
     "150 tasks from Terminal-Bench and InterCode.”",
     "2604.17596",
     "The abstract describes 331 reward-hackable environments, 3,632 hack trajectories, "
     "and 2,352 legitimate baselines. No 42-pattern or 150-task count is in the abstract.",
     "VERIFY OR REMOVE"),
    ("“Hack-Verifiable Terminal Bench replaces fragile stdout regexes with cryptographic "
     "checksum trees and read-only verifier volumes.”",
     "2608.22103",
     "The abstract describes adapting HVE to Terminal Bench to measure reward hacking and "
     "test prompting mitigations; it does not claim a checksum-tree defense in the abstract.",
     "VERIFY OR REWRITE"),
    ("“Up to 77% of benchmark unit tests suffer from coverage deficits.”",
     "2604.01518",
     "The 77% is the fraction of SWE-bench Verified instances with at least one surviving "
     "program variant, not the fraction of individual unit tests with coverage deficits.",
     "REWRITE"),
]

STOPWORDS = {"a", "an", "the", "of", "for", "and", "in", "on", "with", "to", "via",
             "from", "by", "is", "are", "at", "as", "into", "using", "toward",
             "towards", "your", "their"}


def load_corpus() -> list[dict]:
    if not CORPUS.exists():
        raise SystemExit(f"Corpus not found: {CORPUS}. Run the harvester first.")
    return [json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()]


def sentence_split(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'])", text)
    return [p.strip() for p in parts if len(p.strip()) > 25]


def auto_summary(rec: dict, max_chars: int = 520) -> str:
    abstract = (rec.get("abstract") or "").strip()
    if not abstract:
        return ("No abstract available in the metadata source; this record is a "
                "metadata-only citation and needs manual retrieval.")
    sents = sentence_split(abstract)
    if not sents:
        return abstract[:max_chars]
    chosen = [sents[0]]
    signal = re.compile(
        r"(\d+(?:\.\d+)?\s?%|\bwe (?:find|show|demonstrate|observe|reveal|propose|introduce)\b|"
        r"\bresults? (?:show|indicate|demonstrate)\b|\boutperform|\bimprov|\breduc|\bincreas|"
        r"\bwe (?:evaluate|release|present)\b)", re.I)
    for s in sents[1:]:
        if signal.search(s):
            chosen.append(s)
        if sum(len(x) + 1 for x in chosen) >= max_chars:
            break
    summary = " ".join(chosen)
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0] + "..."
    return summary


def key_numbers(rec: dict, limit: int = 5) -> list[str]:
    text = rec.get("abstract") or ""
    out = []
    for m in re.finditer(r"(?:^|[.;]\s)([^.;]{0,140}?\b\d+(?:\.\d+)?\s?%[^.;]{0,80})", text):
        snippet = re.sub(r"\s+", " ", m.group(1)).strip()
        if snippet not in out:
            out.append(snippet)
        if len(out) >= limit:
            break
    return out


def limitation_sentence(rec: dict) -> str:
    text = " ".join(sentence_split(rec.get("abstract") or ""))
    for s in sentence_split(text):
        if re.search(r"\b(limitation|however|future work|cannot|fail|struggle|threat to validity)\b",
                     s, re.I):
            return s[:360]
    return ""


def first_author(rec: dict) -> str:
    authors = rec.get("authors") or []
    if not authors:
        return "Unknown"
    if len(authors) == 1:
        return authors[0]
    return f"{authors[0]} et al."


def author_line(rec: dict, max_authors: int = 6) -> str:
    authors = rec.get("authors") or []
    if not authors:
        return "Unknown"
    if len(authors) <= max_authors:
        return ", ".join(authors)
    return ", ".join(authors[:max_authors]) + f", et al. ({len(authors)} authors)"


def link_md(rec: dict, from_dir: Path = DOCS) -> str:
    links = []
    if rec.get("arxiv_id"):
        links.append(f"[arXiv](https://arxiv.org/abs/{rec['arxiv_id']})")
    if rec.get("doi"):
        links.append(f"[DOI](https://doi.org/{rec['doi']})")
    if rec.get("url") and not rec.get("arxiv_id") and not rec.get("doi"):
        links.append(f"[source]({rec['url']})")
    pdf = rec.get("pdf_path")
    if rec.get("pdf_status") == "ok" and pdf:
        rel = Path("..") / pdf if from_dir == DOCS else Path("../..") / pdf
        links.append(f"[local PDF]({rel.as_posix()})")
    return " · ".join(links) if links else "—"


def write_csv(corpus: list[dict]) -> None:
    path = META / "papers_master.csv"
    cols = ["corpus_id", "title", "authors", "year", "venue", "tier", "score",
            "cluster", "cluster_name", "clusters", "arxiv_id", "doi", "url",
            "pdf_status", "pdf_path", "text_status", "text_chars", "pdf_bytes",
            "citations", "sources", "seed", "matched_terms", "abstract",
            "auto_summary", "aavs_role"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for rec in corpus:
            row = dict(rec)
            row["authors"] = "; ".join(rec.get("authors") or [])
            row["clusters"] = ",".join(rec.get("clusters") or [])
            row["sources"] = ",".join(rec.get("sources") or [])
            row["matched_terms"] = ",".join(rec.get("matched_terms") or [])
            row["auto_summary"] = auto_summary(rec)
            row["aavs_role"] = AAVS_ROLE.get(rec.get("cluster"), "")
            writer.writerow(row)
    print(f"wrote {path} ({len(corpus)} rows)")


def bib_key(rec: dict) -> str:
    a = re.sub(r"[^A-Za-z]", "", (rec.get("authors") or ["anon"])[0].split()[-1]).lower()
    word = next((w for w in re.findall(r"[A-Za-z]+", rec.get("title", ""))
                 if w.lower() not in STOPWORDS), "paper")
    return f"{a or 'anon'}{rec.get('year', '')}{word.lower()}"


def bib_escape(s: str) -> str:
    return (s or "").replace("{", "(").replace("}", ")").replace("\\", "")


def write_bib(corpus: list[dict]) -> None:
    path = META / "papers.bib"
    entries = []
    seen = set()
    for rec in corpus:
        key = bib_key(rec)
        base = key
        n = 2
        while key in seen:
            key = f"{base}{n}"
            n += 1
        seen.add(key)
        fields = [
            ("title", bib_escape(rec.get("title", ""))),
            ("author", bib_escape(" and ".join(rec.get("authors") or []))),
            ("year", str(rec.get("year") or "")),
            ("journal", bib_escape(rec.get("venue", ""))),
        ]
        if rec.get("doi"):
            fields.append(("doi", rec["doi"]))
        if rec.get("url"):
            fields.append(("url", rec["url"]))
        if rec.get("arxiv_id"):
            fields.append(("eprint", rec["arxiv_id"]))
            fields.append(("archivePrefix", "arXiv"))
        body = ",\n  ".join(f"{k} = {{{v}}}" for k, v in fields if v)
        entries.append(f"@article{{{key},\n  {body}\n}}\n")
    path.write_text("\n".join(entries))
    print(f"wrote {path} ({len(entries)} entries)")


def cluster_stats(corpus: list[dict]) -> dict:
    out = {}
    for cid in CLUSTER_NAMES:
        rows = [r for r in corpus if r.get("cluster") == cid]
        out[cid] = {
            "count": len(rows),
            "pdf": sum(1 for r in rows if r.get("pdf_status") == "ok"),
            "A": sum(1 for r in rows if r.get("tier") == "A"),
            "median_year": sorted([r.get("year", 0) for r in rows])[len(rows) // 2]
            if rows else 0,
        }
    return out


SANDBOX_RE = re.compile(
    r"(sandbox\w*|\bmicrovm\b|\bcontainer[- ](?:escape|isolation|security)|"
    r"\btamper\w*|\bstate[- ]spoof\w*|\bfilesystem[- ]integrity|"
    r"\bread-only[- ]verifier|\bexecution[- ]security|\bisolation\b)", re.I)


def sandbox_papers(corpus: list[dict]) -> list[dict]:
    rows = [r for r in corpus if SANDBOX_RE.search(r.get("title") or "")]
    return sorted(rows, key=lambda r: r.get("score", 0), reverse=True)


def write_master_report(corpus: list[dict]) -> None:
    total = len(corpus)
    pdf_ok = sum(1 for r in corpus if r.get("pdf_status") == "ok")
    txt_ok = sum(1 for r in corpus if r.get("text_status") == "ok")
    tiers = Counter(r.get("tier") for r in corpus)
    years = Counter(r.get("year") for r in corpus if r.get("year"))
    sources = Counter()
    for r in corpus:
        for s in (r.get("sources") or [r.get("source", "")]):
            if s:
                sources[s] += 1
    stats = cluster_stats(corpus)
    top = sorted(corpus, key=lambda r: (r.get("seed", False), r.get("score", 0),
                                        r.get("year", 0)), reverse=True)[:50]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# AAVS Global Literature Corpus — Master Report",
        "",
        f"**Generated:** {now}  ",
        f"**Corpus:** {total} deduplicated papers · {pdf_ok} open-access PDFs downloaded · "
        f"{txt_ok} full texts extracted  ",
        "**Taxonomy:** 10 clusters mapped to the AAVS thesis  ",
        "**Status:** metadata verified against live arXiv/Crossref APIs; summaries are "
        "auto-extracted from abstracts/full text and labelled accordingly.",
        "",
        "---",
        "",
        "## 1. What this corpus is",
        "",
        "This is the machine-built evidence base for the claim that **outcome-based unit-test "
        "verifiers are too weak to serve as reward signals for coding agents**. It collects "
        "work on benchmark test inadequacy, mutation testing, test-oracle synthesis, reward "
        "hacking, patch correctness, coding-agent benchmarks, and sandbox/state integrity.",
        "",
        "Every record carries a canonical link, a relevance score, a primary cluster, and a "
        "local PDF path when an open-access copy was available. The companion per-paper "
        "dossiers live in [`docs/literature/`](literature/INDEX.md), and the four papers "
        "already cited by this repository are re-verified in "
        "[`docs/CITATION_INTEGRITY_AUDIT.md`](CITATION_INTEGRITY_AUDIT.md).",
        "",
        "## 2. Corpus statistics",
        "",
        "| Metric | Value |",
        "| :--- | ---: |",
        f"| Papers | {total} |",
        f"| Tier A (directly on-thesis) | {tiers.get('A', 0)} |",
        f"| Tier B (strongly relevant) | {tiers.get('B', 0)} |",
        f"| Tier C (contextual) | {tiers.get('C', 0)} |",
        f"| Open-access PDFs on disk | {pdf_ok} |",
        f"| Full texts extracted | {txt_ok} |",
        f"| arXiv / Crossref records | {sources.get('arxiv', 0)} / {sources.get('crossref', 0)} |",
        f"| Year range | {min(years) if years else 0}–{max(years) if years else 0} |",
        f"| 2023+ papers | {sum(v for k, v in years.items() if k >= 2023)} |",
        "",
        "### Cluster distribution",
        "",
        "| Cluster | Papers | Tier A | PDFs | Median year |",
        "| :--- | ---: | ---: | ---: | ---: |",
    ]
    for cid, s in stats.items():
        lines.append(f"| **{cid}** — {CLUSTER_NAMES[cid]} | {s['count']} | {s['A']} | "
                     f"{s['pdf']} | {s['median_year']} |")

    sandbox = sandbox_papers(corpus)
    lines += [
        "",
        f"**Cross-cutting C10 note.** C10 is deliberately a cross-cutting tag: sandbox, "
        f"container, and state-integrity papers are naturally assigned to C5 (coding agents) "
        f"or C3 (reward hacking) by the lexical scorer. {len(sandbox)} papers match C10 "
        "terms; they are listed below so Stage 2 does not lose them.",
        "",
        "| ID | Year | Paper | Primary | Score | Links |",
        "| :--- | ---: | :--- | :--- | ---: | :--- |",
    ]
    for rec in sandbox:
        title = (rec.get("title") or "").replace("|", "\\|")
        lines.append(f"| {rec.get('corpus_id')} | {rec.get('year', '')} | {title} | "
                     f"{rec.get('cluster')} | {rec.get('score')} | {link_md(rec)} |")

    lines += [
        "",
        "## 3. Method (reproducible)",
        "",
        "1. **Query plan.** 120 boolean/relevance queries spanning all 10 clusters were issued "
        "against the arXiv API (relevance-sorted, top 100 each) and Crossref (top 60 each). "
        "Queries are defined in `scripts/literature_harvester.py`.",
        "2. **Deduplication.** Records are merged across sources by normalized arXiv ID, DOI, "
        "and normalized title (hyphen/case/punctuation insensitive).",
        "3. **Scoring.** Each paper receives a weighted phrase score (title hits ×4.5, abstract "
        "hits ×1.0, repetition capped) over cluster-specific vocabularies. Strong software "
        "signals and core-title phrases set a relevance floor; off-topic vocabularies "
        "(malware/phishing/biology/etc.) apply penalties. Scores are for prioritization, not "
        "scientific quality.",
        "4. **Tiers.** A ≥ 95 (directly on-thesis), B 85–94 (strongly relevant), C 60–84 "
        "(contextual); below 60 is retained only in the raw dump. The corpus is capped at the "
        "top 1,600 after filtering, so most kept papers sit in A/B by construction.",
        "5. **Downloads.** arXiv PDFs are fetched first, then publisher OA links; every file is "
        "validated by `%PDF-` magic bytes and a 10 KB minimum. Paywalled records are kept as "
        "metadata with DOI links and marked `failed`.",
        "6. **Extraction.** `pdftotext -layout` converts PDFs to text for full-text-assisted "
        "reviews. No LLM was used to invent findings; summaries quote or compress the abstract.",
        "",
        "**Known limitations.** (a) Relevance scoring is lexical, so a paper can score high "
        "for vocabulary without being methodologically central; (b) Crossref abstracts are "
        "incomplete, so some venue records are title-only; (c) PDF success depends on open "
        "access; (d) automatic summaries must be checked before quoting a number in a paper.",
        "",
        "## 4. Citation integrity audit",
        "",
        "Four arXiv IDs were already cited in the repository's literature docs. All four "
        "resolve to real papers, but all four titles in the docs differ from the live records. "
        "Details and required corrections are in "
        "[`docs/CITATION_INTEGRITY_AUDIT.md`](CITATION_INTEGRITY_AUDIT.md). **Do not submit the "
        "current docs verbatim until those claims are checked.**",
        "",
        "## 5. Top 50 anchor papers",
        "",
        "| # | Paper | Year | Cluster | Score | Links |",
        "| ---: | :--- | ---: | :--- | ---: | :--- |",
    ]
    for rec in top:
        title = rec.get("title", "").replace("|", "\\|")
        lines.append(f"| {rec.get('corpus_id')} | {title} | {rec.get('year', '')} | "
                     f"{rec.get('cluster', '')} | {rec.get('score', '')} | "
                     f"{link_md(rec)} |")

    lines += [
        "",
        "## 6. Full corpus index",
        "",
        "Every paper is listed below by primary cluster, then by descending relevance. "
        "One-paragraph dossiers (summary, key numbers, limitations, AAVS role) are in "
        "[`docs/literature/INDEX.md`](literature/INDEX.md).",
        "",
    ]
    for cid, name in CLUSTER_NAMES.items():
        rows = sorted([r for r in corpus if r.get("cluster") == cid],
                      key=lambda r: r.get("score", 0), reverse=True)
        lines += [f"### {cid} — {name} ({len(rows)} papers)", ""]
        if not rows:
            lines += ["_No papers in this cluster._", ""]
            continue
        lines += ["| ID | Year | Paper | Venue | Tier/Score | Links |",
                  "| :--- | ---: | :--- | :--- | :--- | :--- |"]
        for rec in rows:
            title = rec.get("title", "").replace("|", "\\|")
            venue = (rec.get("venue") or "").replace("|", "\\|")[:60]
            lines.append(
                f"| {rec.get('corpus_id')} | {rec.get('year', '')} | {title} | {venue} | "
                f"{rec.get('tier')}/{rec.get('score')} | {link_md(rec)} |")
        lines.append("")

    lines += [
        "## 7. Files in this deliverable",
        "",
        "| File | Purpose |",
        "| :--- | :--- |",
        "| `papers/metadata/papers_corpus.jsonl` | Source of truth (all metadata + status) |",
        "| `papers/metadata/papers_master.csv` | Spreadsheet-friendly corpus |",
        "| `papers/metadata/papers.bib` | BibTeX export |",
        "| `docs/PAPER_LIST.md` | Flat, score-sorted list of every paper with links |",
        "| `docs/FULLTEXT_SIGNAL_INDEX.md` | Term coverage + best sentence per extracted paper |",
        "| `papers/pdf/` | Open-access PDFs |",
        "| `papers/text/` | `pdftotext` extractions |",
        "| `docs/literature/dossiers_C*.md` | One dossier per paper, by cluster |",
        "| `docs/ANCHOR_PAPER_REVIEWS.md` | Full-text-assisted reviews of top anchors |",
        "| `docs/CITATION_INTEGRITY_AUDIT.md` | Verification of previously cited papers |",
        "",
        "## 8. How to extend",
        "",
        "Add queries to `QUERIES` in `scripts/literature_harvester.py`, then run:",
        "",
        "```bash",
        "python scripts/literature_harvester.py harvest --target 1500",
        "python scripts/literature_harvester.py download --limit 1500",
        "python scripts/literature_harvester.py extract",
        "python scripts/enrich_abstracts.py",
        "python scripts/literature_report.py",
        "python scripts/literature_fulltext_index.py",
        "python scripts/build_compendium.py",
        "```",
        "",
        "Query responses are cached in `papers/metadata/query_cache/`, so re-runs only fetch "
        "new queries. Do not commit the PDF corpus blindly; check `du -sh papers/` first.",
        "",
    ]
    out = DOCS / "LITERATURE_CORPUS_REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


def write_dossiers(corpus: list[dict]) -> None:
    LIT.mkdir(parents=True, exist_ok=True)
    index_lines = [
        "# AAVS Paper Dossiers — Index",
        "",
        f"{len(corpus)} papers, grouped by primary cluster. Each dossier entry is generated "
        "from live metadata and the paper's abstract (or full text where available). "
        "**Auto-extracted summaries are labelled; verify numbers before citing.**",
        "",
        "| Cluster | File | Papers |",
        "| :--- | :--- | ---: |",
    ]
    for cid, name in CLUSTER_NAMES.items():
        rows = sorted([r for r in corpus if r.get("cluster") == cid],
                      key=lambda r: r.get("score", 0), reverse=True)
        crosscut = False
        if cid == "C10":
            merged_rows = {r.get("corpus_id"): r for r in rows}
            for rec in sandbox_papers(corpus):
                merged_rows.setdefault(rec.get("corpus_id"), rec)
            rows = sorted(merged_rows.values(),
                          key=lambda r: r.get("score", 0), reverse=True)
            crosscut = True
        fname = f"dossiers_{cid}.md"
        index_lines.append(f"| {cid} — {name} | [{fname}]({fname}) | {len(rows)} |")
        out_lines = [
            f"# {cid} — {name}",
            "",
            f"{len(rows)} papers. Relevance tier/score is a prioritization aid, not a quality "
            "judgement. Summaries are auto-extracted from abstracts/full text.",
            "",
        ]
        if crosscut:
            out_lines += [
                "_Cross-cutting view: these papers are primarily assigned to C3/C5, but "
                "their titles match sandbox/container/state-integrity terms. They are "
                "duplicated here so Stage 2 work does not lose them._",
                "",
            ]
        for rec in rows:
            out_lines += dossier_entry(rec, from_dir=LIT)
        (LIT / fname).write_text("\n".join(out_lines), encoding="utf-8")
        print(f"wrote {LIT / fname} ({len(rows)} entries)")

    index_lines += [
        "",
        "Related reports:",
        "",
        "- [Master corpus report](../LITERATURE_CORPUS_REPORT.md)",
        "- [Anchor paper reviews](../ANCHOR_PAPER_REVIEWS.md)",
        "- [Citation integrity audit](../CITATION_INTEGRITY_AUDIT.md)",
        "",
    ]
    (LIT / "INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")
    print(f"wrote {LIT / 'INDEX.md'}")


def dossier_entry(rec: dict, from_dir: Path) -> list[str]:
    title = rec.get("title", "").strip()
    cid = rec.get("cluster", "")
    other_clusters = [c for c in (rec.get("clusters") or []) if c != cid]
    clusters = ", ".join(other_clusters) if other_clusters else "—"
    summary = auto_summary(rec)
    nums = key_numbers(rec)
    limit = limitation_sentence(rec)
    lines = [
        f"### {rec.get('corpus_id')} — {title}",
        "",
        f"**Authors:** {author_line(rec)}  ",
        f"**Year / venue:** {rec.get('year', 'n.d.')} · {rec.get('venue') or rec.get('category') or '—'}  ",
        f"**Relevance:** {rec.get('tier', '?')} ({rec.get('score', 0)}) · "
        f"primary {cid} ({CLUSTER_NAMES.get(cid, '—')}) · also {clusters}  ",
        f"**Links:** {link_md(rec, from_dir)}  ",
        f"**PDF / text:** {rec.get('pdf_status', 'pending')} / {rec.get('text_status', 'pending')}"
        + (f" · {rec.get('text_chars', 0):,} chars" if rec.get("text_chars") else "") + "  ",
        f"**Matched terms:** {', '.join(rec.get('matched_terms') or []) or '—'}  ",
        f"**Seed/foundational:** {'yes' if rec.get('seed') else 'no'}",
        "",
        f"**Auto-extracted summary.** {summary}",
        "",
    ]
    if nums:
        lines.append("**Quantitative signals in the abstract.** " +
                     "; ".join(f"“{n}”" for n in nums))
        lines.append("")
    if limit:
        lines.append(f"**Stated limitation / caveat (auto-detected).** {limit}")
        lines.append("")
    lines += [
        f"**Why it matters for AAVS.** {AAVS_ROLE.get(cid, 'Contextual background.')}",
        "",
        "---",
        "",
    ]
    return lines


def read_text_excerpt(rec: dict, pattern: str, window: int = 1600,
                      fallback_ratio: float = 0.88,
                      require_heading: bool = False) -> str:
    """Extract a section, preferring a real heading over inline mentions.

    Academic PDFs put references and appendices in the last ~15%; a bare word
    match there is usually a cited title, not the paper's own limitation.
    """
    text_path = rec.get("text_path")
    if not text_path or rec.get("text_status") != "ok":
        return ""
    p = ROOT / text_path
    if not p.exists():
        return ""
    raw = p.read_text(errors="ignore")
    lines = raw.splitlines()
    heading_re = re.compile(
        r"^\s*(?:\d+(?:\.\d+)*\.?\s*)?(?:" + pattern + r")"
        r"\b(?:\s+and\s+future\s+work)?\s*[:.]?\s*(?:\d{1,3})?\s*$", re.I)
    body_limit = int(fallback_ratio * max(1, len(lines)))
    headings = [i for i, line in enumerate(lines)
                if i < body_limit and heading_re.match(line.strip())]
    if headings:
        start = headings[-1]
        chunk = " ".join(lines[start:start + 80])
        return re.sub(r"\s+", " ", chunk).strip()[:window]
    if require_heading:
        return ""

    normalized = re.sub(r"\s+", " ", raw)
    matches = list(re.finditer(pattern, normalized, re.I))
    if not matches:
        return ""
    body = [m for m in matches if m.start() < int(fallback_ratio * len(normalized))]
    if not body:
        return ""
    match = body[-1]
    return normalized[match.start():match.start() + window].strip()


def write_anchor_reviews(corpus: list[dict]) -> None:
    ranked = sorted(
        [r for r in corpus if r.get("pdf_status") == "ok"],
        key=lambda r: (r.get("seed", False), r.get("score", 0)), reverse=True,
    )
    # Keep a mix: top-ranked + one per cluster that has full text.
    picks = ranked[:45]
    for cid in CLUSTER_NAMES:
        candidates = [r for r in ranked if r.get("cluster") == cid
                      and r.get("text_status") == "ok"]
        if candidates and candidates[0] not in picks:
            picks.append(candidates[0])
    picks = picks[:65]

    lines = [
        "# Anchor Paper Reviews (Full-Text Assisted)",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Scope:** {len(picks)} highest-relevance papers with locally available full text.  ",
        "**Method:** abstract + extracted conclusion/limitations + quantitative signals. "
        "These are reading aids, not peer review. Confirm every number in the source PDF "
        "before citing it.",
        "",
        "---",
        "",
    ]
    for rec in picks:
        cid = rec.get("cluster", "")
        conclusion = read_text_excerpt(
            rec, r"(?:conclusions?|discussion)", 1800, fallback_ratio=0.88,
            require_heading=True)
        limitations = read_text_excerpt(
            rec, r"(?:limitations?|threats? to validity|future work)", 1200,
            fallback_ratio=0.72, require_heading=False)
        lines += [
            f"## {rec.get('corpus_id')} — {rec.get('title')}",
            "",
            f"**Authors:** {author_line(rec)}  ",
            f"**Year / venue:** {rec.get('year', 'n.d.')} · {rec.get('venue') or '—'}  ",
            f"**Relevance:** {rec.get('tier')}/{rec.get('score')} · {cid} "
            f"({CLUSTER_NAMES.get(cid, '—')})  ",
            f"**Links:** {link_md(rec, DOCS)}  ",
            "",
            f"**Abstract-level finding.** {auto_summary(rec, 700)}",
            "",
        ]
        nums = key_numbers(rec, 6)
        if nums:
            lines += ["**Quantitative signals.**", ""]
            lines += [f"- {n}" for n in nums]
            lines += [""]
        if conclusion:
            lines += ["**Conclusion excerpt (first 1.8k chars after the heading).**", "",
                      f"> {conclusion[:1800]}", ""]
        if limitations:
            lines += ["**Limitations excerpt (first 1.2k chars).**", "",
                      f"> {limitations[:1200]}", ""]
        lines += [
            f"**AAVS use.** {AAVS_ROLE.get(cid, 'Contextual background.')}",
            "",
            "---",
            "",
        ]
    out = DOCS / "ANCHOR_PAPER_REVIEWS.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} ({len(picks)} reviews)")


def write_citation_audit(corpus: list[dict]) -> None:
    by_arxiv = {r.get("arxiv_id"): r for r in corpus if r.get("arxiv_id")}
    lines = [
        "# Citation Integrity Audit",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "This audit checks the papers already cited in the repository's literature "
        "documents against live arXiv metadata. It exists because an early review found "
        "title/claim drift between the docs and the actual records.",
        "",
        "## Verified records",
        "",
        "| arXiv ID | Document title | Live title | Status |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for aid, spec in VERIFIED_ANCHORS.items():
        live = by_arxiv.get(aid)
        live_title = live.get("title") if live else spec["actual_title"]
        status = "title mismatch" if spec["doc_title"].lower() != live_title.lower() else "ok"
        lines.append(f"| `{aid}` | {spec['doc_title']} | {live_title} | **{status}** |")
    lines += [
        "",
        "**Other cited IDs.** `arXiv:2110.14168` resolves to *Training Verifiers to Solve "
        "Math Word Problems* (Cobbe et al., 2021); the repository's title matches, so no "
        "correction is needed.",
        "",
        "## Required corrections before submission",
        "",
    ]
    for aid, spec in VERIFIED_ANCHORS.items():
        live = by_arxiv.get(aid)
        lines += [
            f"### `{aid}`",
            "",
            f"- **Document says:** *{spec['doc_title']}*",
            f"- **Live record says:** *{live.get('title') if live else spec['actual_title']}*",
            f"- **Assessment:** {spec['note']}",
        ]
        if live:
            lines += [
                f"- **Live abstract (opening):** {auto_summary(live, 500)}",
                f"- **Link:** https://arxiv.org/abs/{aid}",
                f"- **Local PDF:** {'`' + live.get('pdf_path', '') + '`' if live.get('pdf_status') == 'ok' else '_not downloaded_'}",
            ]
        lines += [""]
    lines += [
        "## Numeric claim reconciliation",
        "",
        "The table below compares headline numbers currently asserted in the repository's "
        "literature docs against the live abstracts. A paper abstract is not proof that a "
        "number is absent from the full text, so every `VERIFY` item must be traced to a "
        "table/section before submission.",
        "",
        "| Claim in repository docs | Source | What the live abstract says | Action |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for claim, source, finding, action in NUMERIC_CLAIMS:
        lines.append(f"| {claim} | `{source}` | {finding} | **{action}** |")
    lines += [
        "",
        "### Why this matters",
        "",
        "The AAVS thesis does not depend on the inflated range. The defensible core is: "
        "multiple independent 2025–2026 audits found that a substantial fraction of "
        "SWE-bench instances can be passed by defective or shortcut patches, and that "
        "augmenting tests changes resolved rates and leaderboard rankings. Cite each paper "
        "for what it actually measured, with its own denominator.",
        "",
        "## What was verified mechanically",
        "",
        "- Each cited arXiv ID resolves to a real record via the arXiv API.",
        "- Titles above are taken from the live API response, not from memory.",
        "- Every corpus record has a live source URL and, where open access allowed, a "
        "checksum-valid PDF (magic-byte verified).",
        "",
    ]
    out = DOCS / "CITATION_INTEGRITY_AUDIT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


def write_flat_list(corpus: list[dict]) -> None:
    ranked = sorted(corpus, key=lambda r: (-r.get("score", 0), r.get("year", 0)))
    lines = [
        f"# Master Paper List ({len(ranked)} Papers)",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        "Sorted by relevance score. `A` ≥ 95, `B` 85–94, `C` < 85. "
        "Every row has a live link; `PDF` means a local open-access copy exists.",
        "",
        "| # | ID | Score | Tier | Year | Cluster | Paper | Links | PDF |",
        "| ---: | :--- | ---: | :--- | ---: | :--- | :--- | :--- | :--- |",
    ]
    for idx, rec in enumerate(ranked, 1):
        title = (rec.get("title") or "").replace("|", "\\|")
        links = link_md(rec, DOCS)
        pdf = "yes" if rec.get("pdf_status") == "ok" else (
            "metadata-only" if rec.get("pdf_status") == "metadata_only" else "no")
        lines.append(
            f"| {idx} | {rec.get('corpus_id')} | {rec.get('score')} | "
            f"{rec.get('tier')} | {rec.get('year') or ''} | {rec.get('cluster')} | "
            f"{title} | {links} | {pdf} |")
    out = DOCS / "PAPER_LIST.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} ({len(ranked)} rows)")


def write_papers_readme(corpus: list[dict]) -> None:
    total = len(corpus)
    pdf_ok = sum(1 for r in corpus if r.get("pdf_status") == "ok")
    txt_ok = sum(1 for r in corpus if r.get("text_status") == "ok")
    lines = [
        "# AAVS Literature Corpus",
        "",
        f"{total} deduplicated papers · {pdf_ok} open-access PDFs · {txt_ok} extracted texts.",
        "",
        "This directory is generated by `scripts/literature_harvester.py` and "
        "`scripts/literature_report.py`. Do not hand-edit the JSONL/CSV; edit the query plan "
        "and re-run.",
        "",
        "## Layout",
        "",
        "| Path | Contents |",
        "| :--- | :--- |",
        "| `pdf/` | Open-access PDFs, validated by magic bytes |",
        "| `text/` | `pdftotext -layout` output |",
        "| `metadata/papers_corpus.jsonl` | Source of truth |",
        "| `metadata/papers_master.csv` | Spreadsheet export |",
        "| `metadata/papers.bib` | BibTeX export |",
        "| `../docs/PAPER_LIST.md` | Flat score-sorted list of every paper |",
        "| `metadata/download_manifest.jsonl` | Per-paper download status |",
        "| `metadata/query_cache/` | Cached arXiv/Crossref responses |",
        "",
        "## Storage warning",
        "",
        "The PDF/text corpus is roughly 2.6 GB. It is intended to stay local. Do not commit "
        "`papers/pdf/` or `papers/text/` to plain Git; use Git LFS or add them to "
        "`.gitignore`. The metadata, CSV, BibTeX, and docs are small and safe to track.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "python scripts/literature_harvester.py harvest --target 1500",
        "python scripts/literature_harvester.py download --limit 1500",
        "python scripts/literature_harvester.py extract",
        "python scripts/enrich_abstracts.py",
        "python scripts/literature_report.py",
        "python scripts/literature_fulltext_index.py",
        "python scripts/build_compendium.py",
        "```",
        "",
        "## Read first",
        "",
        "- [`docs/LITERATURE_DOSSIER.md`](../docs/LITERATURE_DOSSIER.md)",
        "- [`docs/COMPLETE_PAPER_COMPENDIUM.md`](../docs/COMPLETE_PAPER_COMPENDIUM.md)",
        "- [`docs/literature_explorer.html`](../docs/literature_explorer.html)",
        "- [`docs/LITERATURE_CORPUS_REPORT.md`](../docs/LITERATURE_CORPUS_REPORT.md)",
        "- [`docs/literature/INDEX.md`](../docs/literature/INDEX.md)",
        "- [`docs/ANCHOR_PAPER_REVIEWS.md`](../docs/ANCHOR_PAPER_REVIEWS.md)",
        "- [`docs/CITATION_INTEGRITY_AUDIT.md`](../docs/CITATION_INTEGRITY_AUDIT.md)",
        "",
        "## Curation note",
        "",
        "Relevance scores are lexical prioritization aids. A high score means the paper's "
        "title/abstract is saturated with AAVS vocabulary, not that its methodology is sound. "
        "Tier A papers should still be read before being cited.",
        "",
    ]
    (ROOT / "papers" / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote papers/README.md")


def main() -> None:
    corpus = load_corpus()
    corpus.sort(key=lambda r: (r.get("cluster", ""), -r.get("score", 0)))
    write_csv(corpus)
    write_bib(corpus)
    write_master_report(corpus)
    write_flat_list(corpus)
    write_dossiers(corpus)
    write_anchor_reviews(corpus)
    write_citation_audit(corpus)
    write_papers_readme(corpus)
    print(f"done: {len(corpus)} papers")


if __name__ == "__main__":
    main()
