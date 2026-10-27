# Documentation Index

This directory contains six documents. Everything else is generated output and is stored in
`archive/`; it is retained for traceability but is not required reading.

## Documents

| Document | Contents |
| :--- | :--- |
| [`STATE_OF_THE_FIELD.md`](STATE_OF_THE_FIELD.md) | The closest prior work, the point at which each line stops, documented failure modes, and the claims this project can defend. |
| [`PAPER_COMPARISON.md`](PAPER_COMPARISON.md) | A 37-paper comparison table: authors, year, tools, about, domain, pros, cons, and future work, followed by a capability matrix. |
| [`NEXT_STEPS.md`](NEXT_STEPS.md) | The execution order derived from the review: substrate, attacker calibration, two-sided measurement, defender synthesis, container case, release. Includes acceptance and kill criteria. |
| [`RESEARCH_PLAN.md`](RESEARCH_PLAN.md) | Formal definitions, metrics (`SMR`, `VHR`, `FPFR`), the three-stage roadmap, and target venues. |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | The codebase guide: what each script does and how the pipeline runs. |
| [`AAVS_Literature_Review_Main.docx`](AAVS_Literature_Review_Main.docx) | The submission-ready literature review, including the field-status section and the comparison tables. A plain-text mirror is in `AAVS_Literature_Review_Main.txt`. |

## Summary

Coding-agent benchmarks such as SWE-bench decide that a patch is correct if it passes the
repository's tests. Three independent 2025–2026 audits show that this is insufficient: 77% of
Verified instances admit a surviving program variant (P0120), 345 patches were reclassified
(P0001), and 19.71% of passing patches were rejected after adversarial strengthening (P0837).

The components for addressing this exist separately: mutation testing, LLM test synthesis,
adversarial strengthening, and reward-hacking datasets. The corpus does not contain one released
protocol that reports both false passes and false rejections, with per-task provenance, across
code and container state. The project targets that gap. It does not claim the loop is new; it
claims the measurement and the release are. The full argument is in
[`STATE_OF_THE_FIELD.md`](STATE_OF_THE_FIELD.md).

## Archive

`archive/` contains the machine-generated literature dumps: the 1,500-paper index, the
compendium, the HTML explorer, per-paper dossiers, the older surveys, the citation audit, and the
expanded appendix. The directory is gitignored because of its size, and is retained locally for
traceability. It can be regenerated with the scripts in `scripts/archive/`:

```bash
python scripts/archive/literature_report.py
python scripts/archive/build_compendium.py
```

The corpus itself (PDFs, extracted text, JSONL and CSV metadata) is in `papers/` and is also
gitignored.
