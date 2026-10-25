# AAVS Research Experiment Log & Living Manuscript Notes

> **Working Title:** Autonomous Adversarial Verifier Synthesis (AAVS): Eliminating False Positives and Reward Hacking in AI Coding Benchmarks  
> **Target Venues:** IEEE TSE, ACM TOSEM, ICSE, EMNLP, ICLR  
> **Authors:** Research Team  
> **Status:** Phase 1 (Single-Task Harness Verification & Mutation Baseline)

---

## 1. The Core Research Hypotheses

Everything we build and run in this repository serves to determine the empirical values for $[X\%]$, $[Y\%]$, and $[Z\%]$:

1. **The Vulnerability Hypothesis ($H_1$):**  
   *"Standard unit-test verifiers in agent benchmarks (SWE-bench Lite/Verified) only validate narrow happy-path outputs. By applying AST-guided and LLM-driven semantic mutations to official Gold Patches, we hypothesize that over **$[X\%]$** of benchmark tasks will falsely pass defective code (Surviving Mutants / Mutation Survival Rate $MSR$)."*

2. **The Hardening Hypothesis ($H_2$):**  
   *"Our trace-conditioned Verifier Synthesizer automatically synthesizes black-box pytest assertions that eliminate over **$[Y\%]$** of surviving mutants (Verifier Hardening Rate $VHR$) while preserving 100% pass rates on human Gold Patches (Soundness)."*

3. **The Leaderboard Impact Hypothesis ($H_3$):**  
   *"Re-evaluating official public pull requests from top leaderboard models (Claude 3.5 Sonnet, GPT-4o, DeepSeek-V3, Qwen-2.5-Coder) against our hardened verifiers reveals a **$[Z\%]$** False Positive Flip Rate ($FPFR$), demonstrating that published agent benchmarks substantially inflate true reasoning performance."*

---

## 2. Benchmark Task Tracking Matrix

| ID | Instance ID | Repo | Modified Function / Path | Total Mutants | Surviving Mutants | MSR (%) | Synthesized Tests | Hardened (Killed) | VHR (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **01** | `sympy__sympy-20590` | `sympy/sympy` | `sympy/core/basic.py` | TBD | TBD | TBD | TBD | TBD | TBD |
| **02** | `psf__requests-2674` | `psf/requests` | `requests/adapters.py` | TBD | TBD | TBD | TBD | TBD | TBD |
| **03** | `pallets__flask-4045` | `pallets/flask` | `src/flask/blueprints.py` | TBD | TBD | TBD | TBD | TBD | TBD |
| **04** | `pytest-dev__pytest-5221`| `pytest-dev/pytest` | `src/_pytest/fixtures.py`| TBD | TBD | TBD | TBD | TBD | TBD |
| **05** | `astropy__astropy-14182`| `astropy/astropy`| `astropy/io/ascii/rst.py`| TBD | TBD | TBD | TBD | TBD | TBD |

---

## 3. Real-World Leaderboard Model Re-Evaluation (Zero-Cost Metric)

Using public `.patch` submissions downloaded directly from the official SWE-bench Leaderboard:

| Model Name | Original SWE-bench Lite Accuracy | Patches Evaluated | Patches Failing Hardened Verifier | False Positive Flip Rate (FPFR) | Adjusted True Accuracy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Claude 3.5 Sonnet** | TBD % | 20 | TBD | TBD % | TBD % |
| **GPT-4o (OpenAI)** | TBD % | 20 | TBD | TBD % | TBD % |
| **DeepSeek-V3** | TBD % | 20 | TBD | TBD % | TBD % |
| **Qwen-2.5-Coder-32B** | TBD % | 20 | TBD | TBD % | TBD % |

---

## 4. Literature Corpus Baseline (2026-10-21)

- **Corpus:** 1,500 deduplicated papers (540 A / 926 B / 34 C), 10 clusters; 1,112 open-access PDFs and 1,112 extracted full texts.
- **Sources:** arXiv (1,103 records) + Crossref (536 records), deduplicated by arXiv ID / DOI / normalized title.
- **Deliverables:** `docs/LITERATURE_CORPUS_REPORT.md`, `docs/PAPER_LIST.md`, `docs/LITERATURE_SYNTHESIS.md`, `docs/EVIDENCE_MATRIX.md`, `docs/FULLTEXT_SIGNAL_INDEX.md`, `docs/literature/dossiers_C*.md`, `docs/ANCHOR_PAPER_REVIEWS.md`.
- **Review artifacts:** `docs/COMPLETE_PAPER_COMPENDIUM.md` (all 1,500 research cards), `docs/LITERATURE_DOSSIER.md` (cover + 5-minute walkthrough), `docs/literature_explorer.html` (searchable/filterable HTML).
- **Citation audit:** all four previously cited arXiv IDs resolve, but all four document titles differ from the live records. The “24.4%–77.1%” range conflates two denominators; Terminal Wrench reports 331 environments / 3,632 trajectories, not 42 patterns / 150 tasks. See `docs/CITATION_INTEGRITY_AUDIT.md`.
- **Defensible headline numbers:** 77% of SWE-bench Verified instances admit ≥1 surviving variant (P0120); 345 erroneous patches / 40.9% Lite / 24.4% Verified leaderboard entries / 18 and 11 ranking changes (P0001); 50.2% of instances strengthened and top score 78.80% → 62.20% (P0837).
- **Next:** replace the unsupported numbers in the manuscript, add a contamination probe, and run the local SMR/VHR baseline on curated tasks.

---

## 5. Single-Task Day-1 Log: `sympy__sympy-20590`

- **Task Overview:** `sympy__sympy-20590` deals with symbolic core expression traversal in `sympy/core/basic.py`.
- **Target File:** `sympy/core/basic.py`
- **Gold Solution Patch:** Fixes expression equivalence checks for specific compound symbols.
- **Official Evaluation Command:**
  ```bash
  python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path gold \
    --instance_ids sympy__sympy-20590 \
    --max_workers 1 \
    --clean True \
    --run_id baseline-gold-check
  ```
- **Observations:**
  - [ ] Gold Patch executes and outputs `"resolved": true` in `report.json`.
  - [ ] Injected AST mutant (operator inversion) generated and written to `data/mutated_preds.jsonl`.
  - [ ] Mutant executed in harness; check whether it incorrectly yields `"resolved": true` (Surviving Mutant caught!).
  - [ ] Hardened assertion synthesized via `scripts/verifier_synthesizer.py`.
  - [ ] Hardened test applied; verify that it flips `"resolved": false` for the mutant while maintaining `"resolved": true` for the Gold Patch.
