# Autonomous Adversarial Verifier Synthesis (AAVS)

A research prototype for auditing and hardening the test verifiers used to evaluate coding agents.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

Coding agents are evaluated and trained with outcome-based verifiers: a patch is treated as
correct if it passes the repository's tests. Independent audits in 2025 and 2026 show that this
assumption is too weak.

- 77% of SWE-bench Verified instances admit at least one surviving program variant (P0120).
- 345 patches previously marked as passing were reclassified by UTBoost (P0001).
- 19.71% of passing patches were rejected after adversarial strengthening (P0837).

AAVS applies an adversarial loop to a verifier:

1. **Attacker.** Injects semantic, AST-guided bugs into a reference solution.
2. **Blind-spot detector.** Runs the original suite on each mutant and records survivors.
3. **Defender.** Synthesizes targeted assertions against the survivors.
4. **Judge.** Retains a test only if the gold patch passes (soundness) and the mutant fails
   (completeness).

The project does not claim this loop is new. The closest prior work already implements it in
narrow settings. The contribution targeted here is a released protocol that reports both false
passes and false rejections, with per-task provenance, across code and container state. The
evidence and the scope of the claim are documented in
[`docs/STATE_OF_THE_FIELD.md`](docs/STATE_OF_THE_FIELD.md).

---

## Repository layout

```
Agent_to_Agent/
├── data/
│   └── curated_tasks.json          # Lightweight SWE-bench task records
├── papers/
│   ├── pdf/                        # Open-access PDFs
│   ├── text/                       # Extracted full text
│   └── metadata/                   # Corpus JSONL, CSV, BibTeX, query cache
├── docs/
│   ├── README.md                   # Documentation index
│   ├── STATE_OF_THE_FIELD.md       # Prior work, gaps, and defensible claims
│   ├── PAPER_COMPARISON.md         # 37-paper comparison table
│   ├── NEXT_STEPS.md               # Execution order and acceptance criteria
│   ├── RESEARCH_PLAN.md            # Definitions, metrics, and staged roadmap
│   ├── ARCHITECTURE.md             # Codebase guide
│   ├── AAVS_Literature_Review_Main.docx
│   └── archive/                    # Generated literature dumps (not required reading)
├── paper_notes/
│   └── experiment_log.md           # Research notebook and empirical notes
├── scripts/
│   ├── ast_mutator.py              # AST mutation engine (eight operator families)
│   ├── patch_mutator.py            # Patch-aware mutation (changed lines only)
│   ├── code_sanitizer.py           # Code extraction and import deduplication
│   ├── sandbox.py                  # Isolated subprocess execution
│   ├── verifier_gate.py            # Dual-execution soundness/completeness gate
│   ├── verifier_synthesizer.py     # Test synthesis orchestrator
│   ├── llm_client.py               # Groq, OpenAI, and Ollama client
│   ├── run_local_audit.py          # End-to-end local demonstration
│   ├── download_subset.py          # Benchmark task extractor
│   ├── build_google_doc.py         # Review generator (docx and txt)
│   └── archive/                    # Corpus harvesting and report generation scripts
├── tests/                          # Offline unit tests for the core pipeline
├── requirements.txt
└── README.md
```

---

## Quickstart

```bash
git clone https://github.com/Jeevant010/Agent_to_Agent.git
cd Agent_to_Agent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the audit without an API key:

```bash
python scripts/run_local_audit.py --audit-only
```

Run the full loop with a configured provider:

```bash
python scripts/run_local_audit.py
```

The audit-only mode injects all eight mutation families, runs the existing suite, and reports the
Surviving Mutant Rate (SMR). The full mode additionally requests hardened assertions from the
configured LLM and validates them through the dual sandbox gate.

Download additional benchmark tasks:

```bash
python scripts/download_subset.py --count 5 --output data/curated_tasks.json
```

Run the tests:

```bash
python -m pytest tests -q
```

---

## Metrics

| Metric | Definition | Purpose |
| :--- | :--- | :--- |
| `SMR` | Surviving mutants divided by valid mutants | Measures the weakness of the original verifier. |
| `VHR` | Survivors killed by the hardened suite, with the gold patch still passing | Measures hardening without false rejection. |
| `FRR` | Valid gold-patch runs rejected by the hardened suite | The false-rejection side, rarely reported in prior work. |
| `FPFR` | Public agent patches that passed originally and fail under the hardened suite | Re-evaluates leaderboard results without re-running agents. |

---

## Roadmap

| Stage | Benchmark | Focus |
| :--- | :--- | :--- |
| 1 | SWE-bench Verified | Python AST mutations, branch omissions, unit-test gaps |
| 2 | Terminal-Bench | Filesystem state, exit codes, stdout spoofing |
| 3 | DeepSWE | Polyglot repositories, contamination-resistant tasks |

The work required to reach Stage 1 is specified in [`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md).

---

## Documentation

The index is [`docs/README.md`](docs/README.md). The primary documents are:

- [`docs/STATE_OF_THE_FIELD.md`](docs/STATE_OF_THE_FIELD.md): closest prior work, documented
  failure modes, and the claims the project can defend.
- [`docs/PAPER_COMPARISON.md`](docs/PAPER_COMPARISON.md): 37 papers compared on authors, year,
  tools, domain, pros, cons, and future work.
- [`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md): execution order, acceptance criteria, and kill
  criteria.
- [`docs/RESEARCH_PLAN.md`](docs/RESEARCH_PLAN.md): formal definitions and staged plan.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): codebase guide.
- [`docs/AAVS_Literature_Review_Main.docx`](docs/AAVS_Literature_Review_Main.docx): the
  submission-ready review, including the comparison tables.

Generated literature dumps are kept locally in `docs/archive/` (gitignored); they are retained for
traceability and are not required reading. The 1,500-paper corpus in `papers/` is likewise local
data and is not committed.
