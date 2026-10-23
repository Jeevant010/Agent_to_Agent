# System Architecture & Codebase Guide

> A plain-English guide explaining how this project works and what each file does.

---

## 1. What Does This Project Do?

When AI models write code, for example to fix bugs in open-source projects, the result is tested
with the repository's unit tests to determine whether the issue was resolved.

**The problem.** Independent audits show that **77% of SWE-bench Verified instances admit at least
one surviving program variant** (P0120), and UTBoost reclassified 345 patches that had been marked
as passing (P0001). A model can write incorrect code and the existing suite can still report a
pass.

**The approach:**
1. **Attacker.** Deliberately inject realistic bugs (mutations) into working code.
2. **Audit.** Run the existing test suite. A bug that passes the suite marks a blind spot.
3. **Defender.** Prompt an LLM (Groq or Ollama) to write a test that targets that bug.
4. **Judge.** Execute the candidate test in a sandbox under two conditions:
   - it must pass on the original working code (soundness);
   - it must fail on the mutated code (completeness).

A test that satisfies both conditions is retained and closes the loophole.

---

## 2. How the Pipeline Works (Step-by-Step)

```
[1. Good Code]
      │
      ▼
[2. AST Mutator] ──────────► Injects a bug (e.g. changes "<" to "<=")
      │
      ▼
[3. Run Audit] ────────────► Tests the bug against the existing test suite
      │
   Did it pass?
   ├── NO  (Killed)    ──► The existing test is strong enough. Nothing to fix.
   └── YES (Survived)  ──► Loophole found! Broken code passed the tests.
                                │
                                ▼
                       [4. Verifier Synthesizer]
                                │ (Asks LLM to write a targeted test)
                                ▼
                       [5. Dual-Execution Judge]
                                ├── Runs on Good Code  ──► Must PASS (Soundness)
                                └── Runs on Buggy Code ──► Must FAIL (Completeness)
                                        │
                             Did it pass both checks?
                             ├── YES ──► Loophole closed! New test added.
                             └── NO  ──► Send error to LLM and retry.
```

---

## 3. What Each File Does

### Running the Project (`scripts/`)

- [`scripts/run_local_audit.py`](../scripts/run_local_audit.py)  
  **The main runner.** Runs the full pipeline in a terminal and prints a table of results. It
  injects bugs into a sample discount function, reports which bugs pass the tests, and asks the
  LLM to write tests that close the gaps. `--audit-only` stops before synthesis, so the demo runs
  without an API key or a local model.

- [`scripts/ast_mutator.py`](../scripts/ast_mutator.py)  
  **The bug injector (Attacker).** It reads Python code, turns it into an Abstract Syntax Tree (AST), and creates variations with small realistic bugs across eight families: comparison flips, boolean flips, return nullification, arithmetic operator flips, `and`/`or` swaps, `if` negation, augmented-assignment flips, and exception swallowing.

- [`scripts/patch_mutator.py`](../scripts/patch_mutator.py)  
  **The patch-aware filter.** Parses a unified diff and keeps only mutants on lines the PR actually added, instead of mutating every line in a 3,000-line file.

- [`scripts/verifier_synthesizer.py`](../scripts/verifier_synthesizer.py)  
  **The synthesis coordinator (Defender).** It coordinates the LLM, the code cleaner, and the verification gate. If the LLM writes an invalid test, it sends the failure message back to the LLM and asks it to try again.

- [`scripts/llm_client.py`](../scripts/llm_client.py)  
  **The LLM connector.** A lightweight client for Groq (Llama 3.3 70B), OpenAI, and local Ollama.
  It loads the API key from `.env` and sets the headers required by Cloudflare.

- [`scripts/code_sanitizer.py`](../scripts/code_sanitizer.py)  
  **The code cleaner.** Takes messy text from the LLM, strips out chat explanations and reasoning tags (`<think>`), removes duplicate imports, and makes sure the code is valid Python syntax before anything runs.

- [`scripts/sandbox.py`](../scripts/sandbox.py)  
  **The safe runner.** Runs `pytest` inside a clean temporary directory so concurrent runs do not
  interfere and a looping mutant cannot hang the machine.

- [`scripts/verifier_gate.py`](../scripts/verifier_gate.py)  
  **The judge.** Runs candidate tests twice: once on good code and once on bad code. It only approves the test if good code passes and bad code fails.

- [`scripts/download_subset.py`](../scripts/download_subset.py)  
  **The data downloader.** Downloads a small subset of SWE-bench Verified tasks (< 5 MB) so the
  pipeline can be exercised on real code without multi-gigabyte Docker images.

---

### Benchmark Data (`data/`)

- [`data/curated_tasks.json`](../data/curated_tasks.json)  
  Contains real bug-fix tasks downloaded from GitHub repositories (like `astropy`). Each task includes the problem description, the real code patch, and the unit tests written by human developers.

---

### Literature Pipeline (`scripts/archive/`)

These scripts built the corpus and the archived reports. They are not part of the verification
pipeline and are retained only for reproducibility.

- [`scripts/archive/literature_harvester.py`](../scripts/archive/literature_harvester.py)  
  Queries arXiv and Crossref across 120 cluster-specific queries, deduplicates by arXiv ID / DOI /
  normalized title, scores relevance over ten clusters, downloads open-access PDFs, and extracts
  text with `pdftotext`.
- [`scripts/archive/enrich_abstracts.py`](../scripts/archive/enrich_abstracts.py)  
  Fills missing abstracts from Semantic Scholar's batch endpoint and records the provenance per
  paper.
- [`scripts/archive/literature_report.py`](../scripts/archive/literature_report.py)  
  Turns the corpus into a master Markdown report, CSV, BibTeX, per-cluster dossiers,
  full-text-assisted anchor reviews, and a citation-integrity audit.
- [`scripts/archive/literature_fulltext_index.py`](../scripts/archive/literature_fulltext_index.py)  
  Scans every extracted full text for AAVS signal terms, records per-paper counts, and extracts
  the highest-signal sentence for navigation.
- [`scripts/archive/build_compendium.py`](../scripts/archive/build_compendium.py)  
  Builds the complete literature compendium (all 1,500 research cards), the one-page dossier, and
  the self-contained HTML explorer.
- [`scripts/build_google_doc.py`](../scripts/build_google_doc.py)  
  Builds the current review, including the field-status section and the comparison tables, as
  both `.docx` and `.txt`.

---

### Tests (`tests/`)

- [`tests/test_pipeline.py`](../tests/test_pipeline.py)  
  Offline tests for the eight mutation families, patch-aware filtering, output sanitization, sandbox execution/timeouts, and the dual-execution gate. Run with `.venv/bin/python -m pytest tests -q`.

---

### Documentation (`docs/` & `deep-docs/`)

The five files that matter are indexed in [`docs/README.md`](../docs/README.md).

- [`docs/STATE_OF_THE_FIELD.md`](../docs/STATE_OF_THE_FIELD.md)  
  Has anyone already built this? Closest prior work, what failed, and what is actually new.
- [`docs/PAPER_COMPARISON.md`](../docs/PAPER_COMPARISON.md)  
  37-paper comparison table: authors, year, tools, about, domain, pros, cons, future work.
- [`docs/AAVS_Literature_Review_Main.docx`](../docs/AAVS_Literature_Review_Main.docx)  
  Submission-ready review with the comparison table and field-status section.
- [`docs/AAVS_Literature_Review_Main.txt`](../docs/AAVS_Literature_Review_Main.txt)  
  Plain-text version for pasting directly into Google Docs.
- [`docs/RESEARCH_PLAN.md`](../docs/RESEARCH_PLAN.md)  
  The formal academic research plan targeting conferences like ACL, EMNLP, and ICLR.
- [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)  
  *This file!* A friendly guide explaining what every file in the project does.

Generated literature dumps are in [`docs/archive/`](../docs/archive/) and are not meant to be read:
the full 1,500-record index, the compendium, per-paper dossiers, the older surveys, the evidence
matrix, the citation audit, and the expanded appendix. They can be regenerated with the scripts in
`scripts/`.
- [`deep-docs/future_implementation.md`](../deep-docs/future_implementation.md)  
  Future technical upgrades, including running tests in parallel across all CPU cores and automatic boundary value test generation.

---

### Settings & Environment

- [`.env.example`](../.env.example): Example environment file showing where to set `GROQ_KEY`.
- [`.gitignore`](../.gitignore): Tells Git not to commit secret API keys or temporary cache files.
- [`requirements.txt`](../requirements.txt): The 3 Python packages needed to run (`pytest`, `datasets`, `rich`).
- [`README.md`](../README.md): The main front page of the repository on GitHub.
