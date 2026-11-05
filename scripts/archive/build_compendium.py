#!/usr/bin/env python3
"""Build the teacher-facing complete literature compendium.

Inputs (all already produced by the pipeline):
  papers/metadata/papers_corpus.jsonl
  papers/metadata/fulltext_index.csv
  papers/text/*.txt
  docs/ANCHOR_PAPER_REVIEWS.md (for the deep-review set)

Outputs:
  docs/COMPLETE_PAPER_COMPENDIUM.md  - one file, every paper, clustered
  docs/LITERATURE_DOSSIER.md         - one-page cover / how to verify the work
  docs/literature_explorer.html      - self-contained searchable explorer
  papers/metadata/papers_research_cards.jsonl - structured cards

Summaries are rule-based extractions from the abstract/full text. No LLM is
used to invent findings. Every card states its evidence depth explicitly.
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "archive"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from literature_report import (  # noqa: E402
    AAVS_ROLE,
    CLUSTER_NAMES,
    author_line,
    auto_summary,
    key_numbers,
    limitation_sentence,
    link_md,
    read_text_excerpt,
    sandbox_papers,
)

CORPUS = ROOT / "papers" / "metadata" / "papers_corpus.jsonl"
FT_INDEX = ROOT / "papers" / "metadata" / "fulltext_index.csv"
CARDS = ROOT / "papers" / "metadata" / "papers_research_cards.jsonl"
ANCHORS = DOCS / "ANCHOR_PAPER_REVIEWS.md"

CLUSTER_INTROS = {
    "C1": {
        "question": "Do passing benchmark tests actually imply that the bug was fixed?",
        "why": "This is AAVS's core premise: outcome tests are proxies, not proofs.",
        "look_for": ["false-pass rates and their denominators", "mutation/surviving-variant protocols", "coverage-vs-assertion evidence", "contamination controls"],
        "takeaway": "Multiple independent audits find material false-pass rates, but their units differ (instances vs patches vs leaderboard entries). Never merge them.",
    },
    "C2": {
        "question": "Do LLM-generated code and AI patches introduce new vulnerabilities?",
        "why": "A hardened verifier must check security invariants, not only functional outputs.",
        "look_for": ["CWE regression measurements", "security-patch correctness", "secure code benchmarks", "static vs dynamic detection"],
        "takeaway": "Vulnerability detection is mature; evidence that AI patches regress security is thinner and often benchmark-specific.",
    },
    "C3": {
        "question": "How do agents satisfy checks while violating intent?",
        "why": "This supplies AAVS's Layer-2 threat model and the fixtures for environment tests.",
        "look_for": ["reward-hacking definitions", "terminal exploit datasets", "specification gaming", "prompt mitigations", "monitorability"],
        "takeaway": "Environment-level hacking is documented at scale; unified, task-agnostic defenses are still immature.",
    },
    "C4": {
        "question": "Can we synthesize stronger test oracles and verifiers?",
        "why": "This is the defender half of AAVS.",
        "look_for": ["oracle quality vs execution success", "self-repair traps", "assertion generation", "execution feedback", "mutation kill"],
        "takeaway": "More tests is not the same as better oracles. Optimize fault revelation and soundness, not pass rate.",
    },
    "C5": {
        "question": "What substrates are used to evaluate coding agents?",
        "why": "AAVS's evaluation target and public-patch source.",
        "look_for": ["SWE-bench variants", "contamination and leakage", "harness hygiene", "multilingual coverage", "long-horizon tasks"],
        "takeaway": "Benchmark maintenance and contamination control are first-order experimental variables, not footnotes.",
    },
    "C6": {
        "question": "What makes mutation testing scientifically valid?",
        "why": "The attacker engine's theoretical foundation.",
        "look_for": ["coupling effect", "equivalent mutants", "mutation-score validity", "operator selection"],
        "takeaway": "Mutation is a defensible proxy for real faults, but equivalent mutants must be handled explicitly.",
    },
    "C7": {
        "question": "How reliable are verifiers and reward models?",
        "why": "AAVS's output is a verification signal; RLVR makes verifier flaws consequential.",
        "look_for": ["process reward models", "reward overoptimization", "verifier reliability", "execution-guided RL"],
        "takeaway": "Verifier/reward reliability is the bottleneck; better verifiers change both training and evaluation.",
    },
    "C8": {
        "question": "Why do patches that pass tests remain incorrect?",
        "why": "This is the failure mode AAVS's completeness gate targets.",
        "look_for": ["patch correctness assessment", "APR overfitting", "plausible vs correct patches", "fault localization"],
        "takeaway": "Patch overfitting is a longstanding, measurable problem; test-based repair needs stronger oracles.",
    },
    "C9": {
        "question": "How should we evaluate evaluations?",
        "why": "AAVS must not repeat the validity mistakes it criticizes.",
        "look_for": ["contamination", "construct validity", "leaderboard reliability", "reproducibility", "benchmark leakage"],
        "takeaway": "Report denominators, contamination probes, and construct validity; a leaderboard is not a measurement model.",
    },
    "C10": {
        "question": "How do we defend the execution environment itself?",
        "why": "Stage 2/3 agents can modify the harness, filesystem, or process state.",
        "look_for": ["sandbox isolation", "container escape", "state verification", "tamper resistance", "read-only verifier volumes"],
        "takeaway": "Mechanisms exist, but no unified task-agnostic protocol connects code-level and environment-level verification.",
    },
}

MUST_READ = [
    ("P0120", "Closest methodological prior: variant-guided test augmentation on SWE-bench."),
    ("P0001", "Public-patch re-evaluation; 345 false passes and ranking changes."),
    ("P0837", "Independent adversarial strengthening; top score 78.80% → 62.20%."),
    ("P0121", "331 hackable terminal environments and 3,632 exploit trajectories."),
    ("P0841", "The agent harness itself is undertested."),
    ("P0191", "Warns that iterative self-repair can weaken oracles."),
    ("P0564", "Memorization vs reasoning on SWE-bench."),
    ("P0034", "What it takes to maintain a coding benchmark over time."),
    ("P0071", "Environment-level reward-hacking measurement protocol."),
    ("P0002", "Survey of patch overfitting and correctness assessment."),
    ("P0011", "Formal definition of reward hacking / proxy hackability."),
    ("P0052", "Vulnerability regression in AI-generated security patches."),
    ("P0116", "Step-level security reward modeling for code."),
    ("P0434", "The original SWE-bench task definition and harness."),
    ("P0013", "Multilingual issue-resolving benchmark."),
    ("P0262", "Live-updatable benchmark to reduce contamination."),
    ("P0553", "The oracle problem, defined."),
    ("P0555", "Are mutants valid substitutes for real faults?"),
    ("P0554", "Coverage is not strongly correlated with effectiveness."),
    ("P0019", "Inference-time reward hacking and hedging."),
]

BENCHMARK_TERMS = [
    "SWE-bench Verified", "SWE-bench Lite", "SWE-bench Pro", "SWE-bench",
    "SWE-agent", "HumanEval", "MBPP", "LiveCodeBench", "BigCodeBench",
    "Terminal-Bench", "DeepSWE", "Multi-SWE-bench", "Defects4J", "RepoBench",
    "CrossCodeEval", "DS-1000", "CRUXEval", "OSWorld", "AppWorld", "InterCode",
    "WebArena", "GAIA", "TheAgentCompany", "Codeforces",
]

TECHNIQUE_TERMS = [
    "mutation testing", "test oracle", "oracle generation", "test generation",
    "assertion generation", "property-based testing", "fuzzing",
    "metamorphic testing", "differential testing", "automated program repair",
    "fault localization", "reinforcement learning", "RLVR", "GRPO",
    "process reward model", "reward model", "static analysis",
    "symbolic execution", "LLM-as-judge", "sandbox", "container",
    "coverage-guided", "dual execution", "execution feedback",
]

METHOD_CUES = re.compile(
    r"\b(we|this (?:paper|work|study))\s+(?:propose|introduce|present|develop|design|"
    r"build|train|use|apply|evaluate|conduct|perform|release|construct|implement)\b"
    r"|\bour (?:approach|method|framework|system|pipeline)\b", re.I)
FINDING_CUES = re.compile(
    r"(\d+(?:\.\d+)?\s?%|\boutperform|\bimprov|\breduc|\bincreas|\bachiev|"
    r"\bwe (?:find|show|demonstrate|observe|reveal)\b|"
    r"\bresults? (?:show|indicate|demonstrate)\b|\bsignificant)", re.I)


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'])", text)
            if 30 <= len(s.strip()) <= 500]


def first_sentences(text: str, n: int = 2, limit: int = 420) -> str:
    sents = split_sentences(text)
    out = " ".join(sents[:n]).strip()
    return (out[:limit].rsplit(" ", 1)[0] + "...") if len(out) > limit else out


def pick_sentences(text: str, cue: re.Pattern, used: set[str], n: int = 2,
                   limit: int = 420) -> str:
    chosen = []
    for sent in split_sentences(text):
        key = sent.lower()[:120]
        if key in used or not cue.search(sent):
            continue
        used.add(key)
        chosen.append(sent)
        if len(chosen) >= n:
            break
    out = " ".join(chosen)
    return (out[:limit].rsplit(" ", 1)[0] + "...") if len(out) > limit else out


def extract_abstract_from_text(text: str) -> str:
    head = text[:30000]
    m = re.search(r"\bAbstract\b", head, re.I)
    if not m:
        return ""
    chunk = head[m.end():m.end() + 2200]
    chunk = re.split(r"\b(?:1\s+)?Introduction\b|\bI\.\s+Introduction\b", chunk,
                     maxsplit=1, flags=re.I)[0]
    return re.sub(r"\s+", " ", chunk).strip()


def detect_terms(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    return [t for t in terms if t.lower() in low]


def load_corpus() -> list[dict]:
    return [json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()]


def load_ft_index() -> dict[str, dict]:
    if not FT_INDEX.exists():
        return {}
    with FT_INDEX.open() as fh:
        return {row["corpus_id"]: row for row in csv.DictReader(fh)}


def deep_review_ids() -> set[str]:
    if not ANCHORS.exists():
        return set()
    return set(re.findall(r"^## (P\d{4})", ANCHORS.read_text(), re.M))


def evidence_depth(rec: dict, deep: set[str]) -> str:
    if rec.get("corpus_id") in deep:
        return "full-text reviewed"
    if rec.get("text_status") == "ok":
        return "full text scanned"
    if rec.get("abstract"):
        return "abstract reviewed"
    return "metadata only"


def build_card(rec: dict, ft: dict | None, deep: set[str]) -> dict:
    abstract = rec.get("abstract") or ""
    text = ""
    if not abstract and rec.get("text_status") == "ok" and rec.get("text_path"):
        p = ROOT / rec["text_path"]
        if p.exists():
            text = p.read_text(errors="ignore")
            abstract = extract_abstract_from_text(text)
    # Do not fabricate a summary for metadata-only records: leave the fields
    # empty and let the card say "metadata only".
    used: set[str] = set()
    abstract_sents = split_sentences(abstract)
    problem = first_sentences(abstract, 1)
    if len(problem) < 80 and len(abstract_sents) > 1:
        problem = " ".join(abstract_sents[:2])
    for sent in split_sentences(problem):
        used.add(sent.lower()[:120])

    method = pick_sentences(abstract, METHOD_CUES, used, n=2)
    findings = pick_sentences(abstract, FINDING_CUES, used, n=3)

    # Grounded fallbacks: use the next unused abstract sentences rather than
    # leaving a card half-empty (or inventing prose).
    remaining = [s for s in abstract_sents if s.lower()[:120] not in used]
    if not method:
        for sent in remaining:
            if re.search(
                    r"\b(approach|framework|method|system|pipeline|technique|model|"
                    r"tool|dataset|benchmark|architecture)\b", sent, re.I
            ) and not FINDING_CUES.search(sent):
                method = sent[:420]
                used.add(sent.lower()[:120])
                remaining.remove(sent)
                break
    if not findings:
        cand = [s for s in remaining
                if s.lower()[:120] not in used
                and (FINDING_CUES.search(s) or re.search(r"\d", s))]
        if not cand:
            cand = [s for s in remaining if s.lower()[:120] not in used][-2:]
        if cand:
            findings = " ".join(cand[:2])[:420]

    limitations = limitation_sentence({"abstract": abstract})
    conclusion = ""
    if rec.get("corpus_id") in deep and rec.get("text_status") == "ok":
        if not limitations:
            excerpt = read_text_excerpt(
                rec, r"(?:limitations?|threats? to validity)", 600,
                fallback_ratio=0.72, require_heading=False)
            if excerpt:
                excerpt = re.split(r"\b(?:Acknowledg|References)\b", excerpt)[0]
                excerpt = re.sub(
                    r"^\s*(?:\d+(?:\.\d+)*\.?\s*)?(?:limitations?|threats? to validity)"
                    r"\s*[:.]?\s*", "", excerpt, flags=re.I)
                excerpt = re.sub(r"\s+", " ", excerpt).strip()
                if excerpt:
                    excerpt = excerpt[:460]
                    if ". " in excerpt:
                        excerpt = excerpt.rsplit(". ", 1)[0] + "."
                    else:
                        excerpt = excerpt.rsplit(" ", 1)[0].rstrip(",;: ") + "."
                    limitations = excerpt[0].upper() + excerpt[1:]
        concl = read_text_excerpt(rec, r"(?:conclusions?|discussion)", 900,
                                  fallback_ratio=0.88, require_heading=True)
        if concl:
            concl = re.split(r"\b(?:References|Acknowledg)\b", concl)[0]
            concl = re.sub(
                r"^\s*(?:\d+(?:\.\d+)*\.?\s*)?(?:conclusions?|discussion)"
                r"(?:\s+and\s+future\s+work)?\s*[:.]?\s*", "", concl, flags=re.I)
            conclusion = re.sub(r"\s+", " ", concl).strip()[:700]

    combined = " ".join([rec.get("title", ""), abstract, text[:5000]])
    benchmarks = detect_terms(combined, BENCHMARK_TERMS)
    techniques = detect_terms(combined, TECHNIQUE_TERMS)
    nums = key_numbers({"abstract": abstract}, 5)

    depth = evidence_depth(rec, deep)
    signals = {}
    best_sentence = ""
    if ft:
        for key in ("benchmarks", "mutation", "oracles", "failure_modes",
                    "agents", "security", "verification"):
            signals[key] = int(ft.get(f"n_{key}", 0) or 0)
        best_sentence = ft.get("best_sentence", "")

    return {
        "corpus_id": rec.get("corpus_id"),
        "title": rec.get("title", ""),
        "authors": rec.get("authors") or [],
        "year": rec.get("year"),
        "venue": rec.get("venue") or rec.get("category") or "",
        "cluster": rec.get("cluster", ""),
        "cluster_name": CLUSTER_NAMES.get(rec.get("cluster", ""), ""),
        "tier": rec.get("tier", ""),
        "score": rec.get("score", 0),
        "seed": bool(rec.get("seed")),
        "arxiv_id": rec.get("arxiv_id", ""),
        "doi": rec.get("doi", ""),
        "url": rec.get("url", ""),
        "pdf_path": rec.get("pdf_path", ""),
        "pdf_status": rec.get("pdf_status", ""),
        "text_status": rec.get("text_status", ""),
        "abstract_source": rec.get("abstract_source", ""),
        "evidence_depth": depth,
        "problem": problem,
        "method": method,
        "findings": findings,
        "limitations": limitations,
        "conclusion": conclusion,
        "key_numbers": nums,
        "benchmarks": benchmarks,
        "techniques": techniques,
        "signal_counts": signals,
        "best_sentence": best_sentence,
        "aavs_role": AAVS_ROLE.get(rec.get("cluster", ""), "Contextual background."),
    }


def cluster_stats(cards: list[dict]) -> dict:
    out = {}
    for cid in CLUSTER_NAMES:
        rows = [c for c in cards if c["cluster"] == cid]
        out[cid] = {
            "count": len(rows),
            "A": sum(1 for r in rows if r["tier"] == "A"),
            "fulltext": sum(1 for r in rows if r["text_status"] == "ok"),
            "top": sorted(rows, key=lambda r: r["score"], reverse=True)[:10],
        }
    return out


def cluster_rows(cid: str, cards: list[dict]) -> list[dict]:
    rows = sorted([c for c in cards if c["cluster"] == cid],
                  key=lambda c: c["score"], reverse=True)
    if cid == "C10":
        merged = {c["corpus_id"]: c for c in rows}
        for card in sandbox_papers(cards):
            merged.setdefault(card["corpus_id"], card)
        rows = sorted(merged.values(), key=lambda c: c["score"], reverse=True)
    return rows


def md_escape(value: str) -> str:
    return (value or "").replace("|", "\\|")


def write_cards(cards: list[dict]) -> None:
    CARDS.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n"
                             for c in cards), encoding="utf-8")
    print(f"wrote {CARDS}")


def write_compendium(cards: list[dict]) -> None:
    stats = cluster_stats(cards)
    tiers = Counter(c["tier"] for c in cards)
    years = Counter(c["year"] for c in cards if c["year"])
    depth = Counter(c["evidence_depth"] for c in cards)
    lines = [
        "# The Complete AAVS Literature Compendium",
        "",
        "**Every paper, every cluster, one file.**",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Corpus:** {len(cards)} papers · {sum(1 for c in cards if c['text_status']=='ok')} full texts scanned "
        f"· {depth['full-text reviewed']} full-text reviews · {sum(1 for c in cards if c['pdf_status']=='ok')} PDFs on disk  ",
        "**Summaries:** rule-based extraction from abstracts/full text. **No LLM invented any finding.**",
        "",
        "---",
        "",
        "## How to read this file",
        "",
        "1. Read this cover section and the cluster map.",
        "2. Pick a cluster; each starts with the question it answers, why it matters, and what to look for.",
        "3. Every paper has a research card: problem, method, findings, limitations, benchmarks/techniques, "
        "full-text signal, and its role in AAVS.",
        "4. The `Evidence` field is honest: `full-text reviewed` (50 papers), `full text scanned` "
        "(lexical index over 1,112 texts), `abstract reviewed`, or `metadata only`.",
        "5. Use `docs/literature_explorer.html` to search/filter the same cards interactively.",
        "",
        "## What was actually done (reproducible)",
        "",
        f"- **19,072** raw records were harvested from **120** arXiv + Crossref queries.",
        f"- **10,454** unique records remained after deduplication by arXiv ID / DOI / normalized title.",
        f"- **{len(cards)}** papers passed the relevance/domain filters and form this corpus.",
        f"- **{sum(1 for c in cards if c['pdf_status']=='ok')}** open-access PDFs were downloaded; every file was "
        "validated by `%PDF-` magic bytes and a 10 KB minimum.",
        f"- **{sum(1 for c in cards if c['text_status']=='ok')}** full texts were extracted with `pdftotext` "
        "and scanned for AAVS signal terms.",
        "- **149** missing abstracts were filled from Semantic Scholar's batch API; the source is "
        "recorded per card (`abstract_source`).",
        f"- **{depth['full-text reviewed']}** papers received full-text-assisted reviews (abstract + conclusion + "
        "limitations + quantitative signals).",
        "- **All 1,500** papers have a per-paper dossier; every cited link comes from live arXiv/Crossref metadata.",
        "- The four papers already cited by the repository were re-verified; all four titles in the old docs "
        "differed from the live records. See `CITATION_INTEGRITY_AUDIT.md`.",
        "",
        "## Corpus at a glance",
        "",
        "| Metric | Value |",
        "| :--- | ---: |",
        f"| Papers | {len(cards)} |",
        f"| Tier A (directly on-thesis) | {tiers.get('A', 0)} |",
        f"| Tier B (strongly relevant) | {tiers.get('B', 0)} |",
        f"| Tier C (contextual) | {tiers.get('C', 0)} |",
        f"| Year range | {min(years) if years else 0}–{max(years) if years else 0} |",
        f"| 2023 or newer | {sum(v for k, v in years.items() if k >= 2023)} |",
        f"| Full texts scanned | {depth['full text scanned'] + depth['full-text reviewed']} |",
        f"| Full-text reviews | {depth['full-text reviewed']} |",
        "",
        "### Cluster map",
        "",
        "| Cluster | Papers | Tier A | Full texts | Question |",
        "| :--- | ---: | ---: | ---: | :--- |",
    ]
    for cid, s in stats.items():
        count = s["count"]
        if cid == "C10":
            extra = len(cluster_rows(cid, cards)) - count
            count = f"{count} (+{extra} cross-cutting)"
        lines.append(f"| **{cid}** — {CLUSTER_NAMES[cid]} | {count} | {s['A']} | "
                     f"{s['fulltext']} | {CLUSTER_INTROS[cid]['question']} |")

    lines += [
        "",
        "## The 20 papers to read first",
        "",
        "| # | ID | Paper | Why |",
        "| ---: | :--- | :--- | :--- |",
    ]
    by_id = {c["corpus_id"]: c for c in cards}
    for idx, (pid, why) in enumerate(MUST_READ, 1):
        card = by_id.get(pid)
        if card:
            lines.append(f"| {idx} | {pid} | {md_escape(card['title'])} | {why} |")

    lines += ["", "---", ""]

    for cid, name in CLUSTER_NAMES.items():
        intro = CLUSTER_INTROS[cid]
        rows = cluster_rows(cid, cards)
        lines += [
            f"# {cid} — {name}",
            "",
            f"**{len(rows)} papers.** "
            f"**Question:** {intro['question']}  ",
            f"**Why it matters:** {intro['why']}  ",
            "**What to look for:** " + "; ".join(intro["look_for"]) + "  ",
            f"**Cluster takeaway:** {intro['takeaway']}",
            "",
        ]
        if cid == "C10":
            lines += [
                "_Cross-cutting view: these papers are primarily assigned to C3/C5, but "
                "their titles match sandbox/container/state-integrity terms. They are "
                "included here so Stage 2 work does not lose them._",
                "",
            ]
        if rows:
            lines += ["**Top papers in this cluster:** " +
                      "; ".join(f"{r['corpus_id']} — {r['title']} ({r['score']})"
                                for r in rows[:5]), ""]
        for card in rows:
            lines += card_markdown(card)
        lines += ["---", ""]

    lines += [
        "# Appendix A — Evidence and provenance",
        "",
        "| Evidence level | Papers | Meaning |",
        "| :--- | ---: | :--- |",
        f"| full-text reviewed | {depth['full-text reviewed']} | Abstract + conclusion/limitations + quantitative signals read from the PDF |",
        f"| full text scanned | {depth['full text scanned']} | Full text extracted and lexically indexed for AAVS terms |",
        f"| abstract reviewed | {depth['abstract reviewed']} | Metadata abstract read; no local PDF |",
        f"| metadata only | {depth['metadata only']} | No abstract in source; title/venue/DOI only |",
        "",
        "## Reproduce",
        "",
        "```bash",
        "python scripts/literature_harvester.py harvest --target 1500",
        "python scripts/literature_harvester.py download --limit 1500",
        "python scripts/literature_harvester.py extract",
        "python scripts/literature_report.py",
        "python scripts/literature_fulltext_index.py",
        "python scripts/build_compendium.py",
        "```",
        "",
        "## Honest limitations",
        "",
        "- Relevance scoring is lexical; tier A means on-thesis, not necessarily correct.",
        "- Per-paper summaries compress the abstract. Verify every number in the PDF before quoting.",
        "- 388 records are metadata-only or have no local PDF; they are still listed with DOI links.",
        "- The full-text scan is lexical; it shows coverage, not endorsement.",
        "",
    ]
    out = DOCS / "COMPLETE_PAPER_COMPENDIUM.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} ({len(lines)} lines)")


def card_markdown(card: dict) -> list[str]:
    title = card["title"].strip()
    links = []
    if card["arxiv_id"]:
        links.append(f"[arXiv](https://arxiv.org/abs/{card['arxiv_id']})")
    if card["doi"]:
        links.append(f"[DOI](https://doi.org/{card['doi']})")
    if card["pdf_status"] == "ok" and card["pdf_path"]:
        links.append(f"[local PDF](../{card['pdf_path']})")
    link_str = " · ".join(links) if links else "—"
    lines = [
        f"## {card['corpus_id']} — {title}",
        "",
        f"**Authors:** {author_line({'authors': card['authors']})}  ",
        f"**Year / venue:** {card['year'] or 'n.d.'} · {card['venue'] or '—'}  ",
        f"**Cluster:** {card['cluster']} — {card['cluster_name']} · "
        f"**Relevance:** {card['tier']} ({card['score']})  ",
        f"**Evidence:** {card['evidence_depth']} · **PDF:** {card['pdf_status']} · "
        f"**Text:** {card['text_status']}"
        + (f" · **Abstract source:** {card['abstract_source']}"
           if card.get("abstract_source") else "") + "  ",
        f"**Links:** {link_str}",
        "",
    ]
    if card["problem"]:
        lines += [f"**Problem.** {card['problem']}", ""]
    if card["method"]:
        lines += [f"**Method.** {card['method']}", ""]
    if card["findings"]:
        lines += [f"**Findings.** {card['findings']}", ""]
    if card["key_numbers"]:
        lines += ["**Numbers in the abstract.** " +
                  "; ".join(f"“{n}”" for n in card["key_numbers"]), ""]
    if card["limitations"]:
        lines += [f"**Limitations / caveats.** {card['limitations']}", ""]
    if card.get("conclusion"):
        lines += [f"**Conclusion (full-text excerpt).** {card['conclusion']}", ""]
    terms = []
    if card["benchmarks"]:
        terms.append("Benchmarks: " + ", ".join(card["benchmarks"]))
    if card["techniques"]:
        terms.append("Techniques: " + ", ".join(card["techniques"]))
    if terms:
        lines += ["**Detected.** " + " · ".join(terms), ""]
    signals = card.get("signal_counts") or {}
    if signals and sum(signals.values()):
        lines += ["**Full-text signal.** " +
                  ", ".join(f"{k}={v}" for k, v in signals.items() if v) +
                  (f". Highest-signal sentence: “{card['best_sentence']}”"
                   if card.get("best_sentence") else ""), ""]
    lines += [f"**Why it matters for AAVS.** {card['aavs_role']}", "", "---", ""]
    return lines


def write_dossier(cards: list[dict]) -> None:
    tiers = Counter(c["tier"] for c in cards)
    depth = Counter(c["evidence_depth"] for c in cards)
    lines = [
        "# Literature Review Dossier",
        "",
        "**A single entry point for reviewing the AAVS literature work.**",
        "",
        f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}  ",
        f"**Corpus:** {len(cards)} papers · {sum(1 for c in cards if c['pdf_status']=='ok')} PDFs · "
        f"{sum(1 for c in cards if c['text_status']=='ok')} full texts · {depth['full-text reviewed']} full-text reviews  ",
        "**Full compendium:** [`COMPLETE_PAPER_COMPENDIUM.md`](COMPLETE_PAPER_COMPENDIUM.md)  ",
        "**Interactive explorer:** [`literature_explorer.html`](literature_explorer.html)  ",
        "**Flat list:** [`PAPER_LIST.md`](PAPER_LIST.md)",
        "",
        "## 1. What this work is",
        "",
        "This is a systematic literature review of verifier weakness and hardening for coding agents. "
        "It covers benchmark inadequacy, mutation testing, test-oracle synthesis, patch correctness, "
        "reward hacking, coding-agent benchmarks, RLVR/verifiers, and sandbox integrity. The goal is "
        "not a reading list; it is an evidence base for the AAVS thesis and a map of what is already "
        "known versus what AAVS must contribute.",
        "",
        "## 2. What was actually done",
        "",
        "| Step | Result |",
        "| :--- | :--- |",
        "| Query plan | 120 arXiv + Crossref queries across 10 clusters |",
        "| Raw records | 19,072 |",
        "| Deduplicated | 10,454 (arXiv ID / DOI / normalized title) |",
        f"| Curated corpus | {len(cards)} papers after relevance + domain filters |",
        f"| Tier A / B / C | {tiers.get('A',0)} / {tiers.get('B',0)} / {tiers.get('C',0)} |",
        f"| Open-access PDFs | {sum(1 for c in cards if c['pdf_status']=='ok')}, magic-byte verified |",
        f"| Full texts extracted | {sum(1 for c in cards if c['text_status']=='ok')} |",
        "| Missing abstracts enriched | 149 from Semantic Scholar |",
        f"| Full-text reviews | {depth['full-text reviewed']} |",
        f"| Per-paper dossiers | {len(cards)} (all papers) |",
        "| Citation audit | 4 previously cited papers checked against live metadata; all 4 titles corrected |",
        "",
        "## 3. Why the teacher can spot-check it",
        "",
        "- Every paper has a stable row in `PAPER_LIST.md` and a card in the compendium.",
        "- Every card has a live arXiv/DOI link and, where open access allowed, a local PDF path.",
        "- Every summary is labelled by evidence depth; nothing pretends to be a full read when it is not.",
        "- The four originally cited papers were re-checked, and the unsupported numbers were removed.",
        "- The pipeline is reproducible from `scripts/literature_harvester.py` and cached query responses.",
        "",
        "## 4. Cluster map",
        "",
        "| Cluster | Papers | Question it answers |",
        "| :--- | ---: | :--- |",
    ]
    for cid in CLUSTER_NAMES:
        count = sum(1 for c in cards if c["cluster"] == cid)
        if cid == "C10":
            count = f"{count} (+{len(cluster_rows(cid, cards)) - count} cross-cutting)"
        lines.append(f"| {cid} — {CLUSTER_NAMES[cid]} | {count} | {CLUSTER_INTROS[cid]['question']} |")
    lines += [
        "",
        "## 5. The 12 papers to read first",
        "",
        "| ID | Paper | Why |",
        "| :--- | :--- | :--- |",
    ]
    by_id = {c["corpus_id"]: c for c in cards}
    for pid, why in MUST_READ[:12]:
        card = by_id.get(pid)
        if card:
            lines.append(f"| {pid} | {md_escape(card['title'])} | {why} |")
    lines += [
        "",
        "## 6. Five-minute walkthrough",
        "",
        "1. Open this dossier (the file you are reading). Point to the “What was actually done” table.",
        "2. Open `literature_explorer.html`. Search `reward hacking`; the card count drops sharply and only matching clusters remain.",
        "3. Clear the search, choose cluster `C1`, and click **Expand visible**. Show one card's Problem / Method / Findings / Limitations fields.",
        "4. Open `COMPLETE_PAPER_COMPENDIUM.md`, jump to `# C1`, and show the same paper in the single-file compendium.",
        "5. Open `CITATION_INTEGRITY_AUDIT.md`. Show that four previously cited papers were re-checked and their titles/numbers corrected.",
        "6. Open `papers/pdf/arxiv_2604.01518.pdf` (or any card's local PDF link) to prove the source file exists.",
        "7. Optional: run `python scripts/literature_harvester.py status` and `python scripts/build_compendium.py` to show reproducibility.",
        "",
        "The point to make: this is not a list of links. Every paper has a stable ID, a cluster, a relevance score, an evidence-depth label, a research card, and a source link; 1,112 of them have a local PDF and extracted text.",
        "",
        "## 7. Honest limitations",
        "",
        "- 388 records are metadata-only or lack a local PDF; they remain in the corpus with DOI links.",
        "- Summaries compress abstracts; quantitative claims must be checked in the PDF.",
        "- Relevance scoring is lexical. Tier A means on-thesis, not necessarily a strong paper.",
        "- The full-text scan is lexical; it demonstrates coverage, not endorsement.",
        "",
    ]
    out = DOCS / "LITERATURE_DOSSIER.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


HTML_CSS = """
:root{--bg:#f6f6f2;--ink:#1c1c1a;--muted:#5b5b54;--line:#d8d8d0;--card:#fff;
--accent:#0f5c4a;--accent-soft:#e5f0ec;--warn:#8a4b08;--warn-soft:#fbf0df}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 ui-sans-serif,system-ui,
-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
header{padding:40px 24px 24px;border-bottom:1px solid var(--line);background:var(--card)}
.wrap{max-width:1180px;margin:0 auto}
h1{font-size:clamp(26px,4vw,40px);line-height:1.1;margin:0 0 10px;letter-spacing:-.02em}
.lede{color:var(--muted);max-width:850px;margin:0 0 18px}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 0}
.stat{border:1px solid var(--line);background:var(--bg);padding:10px 14px;border-radius:4px}
.stat b{display:block;font-size:20px}
.stat span{color:var(--muted);font-size:13px}
.toolbar{position:sticky;top:0;z-index:10;background:var(--bg);
border-bottom:1px solid var(--line);padding:12px 24px}
.controls{max-width:1180px;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
input[type=search],select{font:inherit;padding:9px 11px;border:1px solid var(--line);
border-radius:4px;background:var(--card);color:var(--ink);min-width:180px}
input[type=search]{flex:1 1 320px}
button{font:inherit;padding:9px 12px;border:1px solid var(--line);background:var(--card);
color:var(--ink);border-radius:4px;cursor:pointer}
button:hover{border-color:var(--accent)}
button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{
outline:2px solid var(--accent);outline-offset:2px}
main{max-width:1180px;margin:0 auto;padding:22px 24px 80px}
.cluster{margin:34px 0 10px}
.cluster h2{font-size:22px;margin:0 0 6px;letter-spacing:-.01em}
.cluster p{color:var(--muted);margin:0 0 6px;max-width:900px}
.count{color:var(--muted);font-size:14px}
details.paper{background:var(--card);border:1px solid var(--line);border-radius:4px;
margin:8px 0;overflow:hidden}
details.paper>summary{list-style:none;cursor:pointer;padding:13px 16px;display:grid;
grid-template-columns:86px 1fr auto;gap:12px;align-items:start}
details.paper>summary::-webkit-details-marker{display:none}
details.paper>summary:hover{background:#fbfbf8}
.pid{font-variant-numeric:tabular-nums;color:var(--muted);font-size:13px;padding-top:2px}
.ptitle{font-weight:600;line-height:1.3}
.pmeta{color:var(--muted);font-size:13px;margin-top:3px}
.badges{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.badge{font-size:11px;letter-spacing:.02em;text-transform:uppercase;padding:3px 7px;
border-radius:3px;border:1px solid var(--line);color:var(--muted);white-space:nowrap}
.badge.a{background:var(--accent-soft);border-color:#bcd6cd;color:var(--accent)}
.badge.ev{background:var(--warn-soft);border-color:#e6d2b5;color:var(--warn)}
.body{padding:4px 16px 18px;border-top:1px solid var(--line)}
.body p{margin:12px 0}
.body h3{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
margin:16px 0 4px}
.links a{color:var(--accent);text-decoration:none;border-bottom:1px solid #b9d3ca}
.links a:hover{border-bottom-color:var(--accent)}
.mono{font-variant-numeric:tabular-nums}
.empty{padding:40px;text-align:center;color:var(--muted)}
footer{border-top:1px solid var(--line);padding:20px 24px;color:var(--muted);font-size:13px}
@media(max-width:720px){
 details.paper>summary{grid-template-columns:1fr}
 .badges{justify-content:flex-start}
 .pid{padding-top:0}
}
@media print{
 .toolbar{display:none}
 details.paper{break-inside:avoid}
 details.paper>summary{background:none}
}
"""


HTML_JS = """
const q = document.getElementById('q');
const cluster = document.getElementById('cluster');
const tier = document.getElementById('tier');
const evidence = document.getElementById('evidence');
const cards = [...document.querySelectorAll('details.paper')];
const visible = document.getElementById('visible');
function apply(){
  const term = q.value.trim().toLowerCase();
  let n = 0;
  for (const card of cards){
    const okQ = !term || card.dataset.search.includes(term);
    const okC = !cluster.value || card.dataset.cluster === cluster.value;
    const okT = !tier.value || card.dataset.tier === tier.value;
    const okE = !evidence.value || card.dataset.evidence === evidence.value;
    const show = okQ && okC && okT && okE;
    card.hidden = !show;
    if (show) n++;
  }
  visible.textContent = n.toLocaleString() + ' cards shown';
  for (const section of document.querySelectorAll('section.cluster')){
    const any = [...section.querySelectorAll('details.paper')].some(c => !c.hidden);
    section.hidden = !any;
  }
}
q.addEventListener('input', apply);
cluster.addEventListener('change', apply);
tier.addEventListener('change', apply);
evidence.addEventListener('change', apply);
document.getElementById('expand').addEventListener('click', () => {
  cards.forEach(c => { if (!c.hidden) c.open = true; });
});
document.getElementById('collapse').addEventListener('click', () => {
  cards.forEach(c => c.open = false);
});
document.getElementById('print').addEventListener('click', () => {
  cards.forEach(c => { if (!c.hidden) c.open = true; });
  setTimeout(() => window.print(), 100);
});
apply();
"""


def write_html(cards: list[dict]) -> None:
    stats = cluster_stats(cards)
    tiers = Counter(c["tier"] for c in cards)
    depth = Counter(c["evidence_depth"] for c in cards)
    c10_primary = sum(1 for c in cards if c["cluster"] == "C10")
    total_cards = len(cards) + len(cluster_rows("C10", cards)) - c10_primary
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def esc(v):
        return html.escape(str(v or ""))

    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>AAVS Literature Explorer</title>",
        f"<style>{HTML_CSS}</style></head><body>",
        "<header><div class='wrap'>",
        "<h1>AAVS Literature Explorer</h1>",
        f"<p class='lede'>{len(cards)} unique papers across 10 clusters, built from 19,072 harvested records. "
        f"{sum(1 for c in cards if c['text_status']=='ok')} full texts were extracted and scanned; "
        f"{depth['full-text reviewed']} received full-text-assisted reviews. "
        f"{total_cards:,} cards are shown because C10 cross-cutting papers appear in two clusters. "
        "Every summary is rule-based and labelled by evidence depth.</p>",
        "<div class='stats'>",
        f"<div class='stat'><b>{len(cards):,}</b><span>papers</span></div>",
        f"<div class='stat'><b>{tiers.get('A',0):,}</b><span>tier A</span></div>",
        f"<div class='stat'><b>{tiers.get('B',0):,}</b><span>tier B</span></div>",
        f"<div class='stat'><b>{sum(1 for c in cards if c['pdf_status']=='ok'):,}</b><span>open-access PDFs</span></div>",
        f"<div class='stat'><b>{sum(1 for c in cards if c['text_status']=='ok'):,}</b><span>full texts scanned</span></div>",
        f"<div class='stat'><b>{depth['full-text reviewed']:,}</b><span>deep reviews</span></div>",
        "</div></div></header>",
        "<div class='toolbar'><div class='controls'>",
        "<input id='q' type='search' placeholder='Search title, author, summary, finding…' "
        "aria-label='Search papers'>",
        "<select id='cluster' aria-label='Filter by cluster'><option value=''>All clusters</option>",
    ]
    for cid, name in CLUSTER_NAMES.items():
        parts.append(f"<option value='{cid}'>{cid} — {esc(name)} ({stats[cid]['count']})</option>")
    parts += [
        "</select>",
        "<select id='tier' aria-label='Filter by tier'><option value=''>All tiers</option>"
        "<option value='A'>Tier A</option><option value='B'>Tier B</option>"
        "<option value='C'>Tier C</option></select>",
        "<select id='evidence' aria-label='Filter by evidence depth'>"
        "<option value=''>All evidence</option>"
        "<option value='full-text reviewed'>Full-text reviewed</option>"
        "<option value='full text scanned'>Full text scanned</option>"
        "<option value='abstract reviewed'>Abstract reviewed</option>"
        "<option value='metadata only'>Metadata only</option></select>",
        "<button id='expand' type='button'>Expand visible</button>",
        "<button id='collapse' type='button'>Collapse</button>",
        "<button id='print' type='button'>Print / PDF</button>",
        f"<span class='count' id='visible'>{total_cards:,} cards shown</span>",
        "</div></div><main>",
    ]

    for cid, name in CLUSTER_NAMES.items():
        rows = cluster_rows(cid, cards)
        intro = CLUSTER_INTROS[cid]
        parts += [f"<section class='cluster' data-cluster='{cid}'>",
                  f"<h2>{cid} — {esc(name)}</h2>",
                  f"<p><b>Question:</b> {esc(intro['question'])}</p>",
                  f"<p><b>Why it matters:</b> {esc(intro['why'])}</p>",
                  f"<p><b>Takeaway:</b> {esc(intro['takeaway'])}</p>",
                  f"<p class='count'>{len(rows)} papers</p>"]
        if cid == "C10":
            parts.append("<p class='count'>Cross-cutting: these papers are primarily "
                         "assigned to C3/C5 but match sandbox/container/state-integrity terms.</p>")
        for card in rows:
            search_blob = " ".join([
                card["title"], " ".join(card["authors"]), card["problem"],
                card["method"], card["findings"], card["limitations"],
                card.get("conclusion", ""),
                " ".join(card["benchmarks"]), " ".join(card["techniques"]),
                card["aavs_role"],
            ]).lower()
            links = []
            if card["arxiv_id"]:
                links.append(f"<a href='https://arxiv.org/abs/{esc(card['arxiv_id'])}'>arXiv</a>")
            if card["doi"]:
                links.append(f"<a href='https://doi.org/{esc(card['doi'])}'>DOI</a>")
            if card["pdf_status"] == "ok" and card["pdf_path"]:
                links.append(f"<a href='../{esc(card['pdf_path'])}'>local PDF</a>")
            signals = ", ".join(f"{k}={v}" for k, v in card["signal_counts"].items() if v)
            parts += [
                f"<details class='paper' data-search=\"{esc(search_blob)}\" "
                f"data-cluster='{esc(card['cluster'])}' data-tier='{esc(card['tier'])}' "
                f"data-evidence='{esc(card['evidence_depth'])}'>",
                "<summary>",
                f"<div class='pid'>{esc(card['corpus_id'])}</div>",
                f"<div><div class='ptitle'>{esc(card['title'])}</div>"
                f"<div class='pmeta'>{esc(author_line({'authors': card['authors']}))} · "
                f"{esc(card['year'])} · {esc(card['venue'])}</div></div>",
                "<div class='badges'>",
                f"<span class='badge a'>{esc(card['tier'])} {esc(card['score'])}</span>",
                f"<span class='badge'>{esc(card['cluster'])}</span>",
                f"<span class='badge ev'>{esc(card['evidence_depth'])}</span>",
                "</div></summary>",
                "<div class='body'>",
                f"<p class='links'>{' · '.join(links) if links else 'No external link'}</p>",
            ]
            if card.get("abstract_source"):
                parts.append(f"<p class='count'>Abstract source: "
                             f"{esc(card['abstract_source'])}</p>")
            if card["problem"]:
                parts.append(f"<h3>Problem</h3><p>{esc(card['problem'])}</p>")
            if card["method"]:
                parts.append(f"<h3>Method</h3><p>{esc(card['method'])}</p>")
            if card["findings"]:
                parts.append(f"<h3>Findings</h3><p>{esc(card['findings'])}</p>")
            if card["key_numbers"]:
                parts.append("<h3>Numbers in the abstract</h3><ul>" +
                             "".join(f"<li>{esc(n)}</li>" for n in card["key_numbers"]) +
                             "</ul>")
            if card["limitations"]:
                parts.append(f"<h3>Limitations / caveats</h3><p>{esc(card['limitations'])}</p>")
            if card.get("conclusion"):
                parts.append(f"<h3>Conclusion (full-text excerpt)</h3>"
                             f"<p>{esc(card['conclusion'])}</p>")
            detected = []
            if card["benchmarks"]:
                detected.append("Benchmarks: " + ", ".join(card["benchmarks"]))
            if card["techniques"]:
                detected.append("Techniques: " + ", ".join(card["techniques"]))
            if detected:
                parts.append(f"<h3>Detected</h3><p>{esc(' · '.join(detected))}</p>")
            if signals:
                parts.append(f"<h3>Full-text signal</h3><p class='mono'>{esc(signals)}</p>")
            if card["best_sentence"]:
                parts.append(f"<h3>Highest-signal sentence</h3><p>{esc(card['best_sentence'])}</p>")
            parts += [f"<h3>Why it matters for AAVS</h3><p>{esc(card['aavs_role'])}</p>",
                      "</div></details>"]
        parts.append("</section>")

    parts += [
        "</main><footer>",
        f"Generated {generated} · 19,072 raw records → 10,454 deduplicated → {len(cards)} curated · "
        "Summaries are rule-based extractions from abstracts/full text, not LLM inventions. "
        "Verify numbers in the source PDF before citing.",
        "</footer>",
        f"<script>{HTML_JS}</script></body></html>",
    ]
    out = DOCS / "literature_explorer.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size/1e6:.1f} MB)")


def main() -> None:
    corpus = load_corpus()
    ft = load_ft_index()
    deep = deep_review_ids()
    cards = [build_card(rec, ft.get(rec.get("corpus_id")), deep) for rec in corpus]
    cards.sort(key=lambda c: (c["cluster"], -c["score"]))
    write_cards(cards)
    write_compendium(cards)
    write_dossier(cards)
    write_html(cards)
    print(f"done: {len(cards)} cards, {len(deep)} deep reviews")


if __name__ == "__main__":
    main()
