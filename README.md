# Autonomous Adversarial Verifier Synthesis (AAVS)
> **Eliminating False Positives & Reward Hacking in Autonomous AI Agent Benchmarks**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Research Track](https://img.shields.io/badge/Track-NLP4SE%20%7C%20AI%20Alignment-purple.svg)](docs/RESEARCH_PLAN.md)

---

## 📌 Overview

Large Language Model (LLM) coding agents are evaluated and trained using outcome-based test verifiers (e.g., `SWE-bench`, `Terminal-Bench`, `DeepSWE`). However, recent 2026 audits reveal that **up to 77% of benchmark unit tests suffer from coverage deficits**, allowing agents to pass tasks using shortcut heuristics, edge-case hardcoding, and state corruption (**Reward Hacking**).

**AAVS** is a model-agnostic, zero-human-verifier framework that deterministically stress-tests and hardens agent verifiers:
1. **Adversarial Mutation (Attacker):** Injects semantic, AST-guided bugs into reference solutions.
2. **Blind Spot Detection:** Catches surviving mutants where broken code falsely passes existing test suites.
3. **Automated Verifier Synthesis (Defender):** Synthesizes strict, bi-directionally verified test assertions to close loopholes.

---

## 🚀 Quickstart (Under 3 Minutes)

Get running locally on your laptop with **zero GPU or Docker setup required**:

### 1. Setup Environment
```bash
git clone https://github.com/Jeevant010/Agent_to_Agent.git
cd Agent_to_Agent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Local Verifier Audit Demo
Witness AST mutation and verifier loophole detection live in your terminal:
```bash
python scripts/run_local_audit.py
```

### 3. Download Curated Benchmark Tasks
Download a lightweight, curated subset of tasks from Hugging Face (< 5 MB) without pulling multi-gigabyte Docker images:
```bash
python scripts/download_subset.py --count 5 --output data/curated_tasks.json
```

### 4. Run AST Mutation on Any Function
```bash
python scripts/ast_mutator.py
```

---

## 📂 Repository Structure

```
Agent_to_Agent/
├── data/
│   ├── curated_tasks.json     # Curated lightweight benchmark tasks (< 5MB)
│   └── mutated_preds.jsonl    # Formatted mutant patch predictions for SWE-bench harness
├── deep-docs/
│   └── future_implementation.md # Technical scalability & future implementation roadmap
├── docs/
│   ├── LITERATURE_SURVEY.md   # Critical reading syllabus & paper-by-paper literature analysis
│   ├── RESEARCH_PLAN.md       # Full academic blueprint (SWE-bench -> Terminal-Bench -> DeepSWE)
│   ├── TEAM_ONBOARDING.md     # 3-weekend step-by-step milestone guide for teammates
│   └── GRANT_PROPOSAL.md      # Itemized resource requirements for compute & cloud grants
├── paper_notes/
│   └── experiment_log.md      # Living research notebook, hypotheses, and empirical tables
├── scripts/
│   ├── ast_mutator.py         # AST semantic mutation engine
│   ├── code_sanitizer.py      # AST parsing, markdown stripping, import deduplication
│   ├── download_subset.py     # Lightweight benchmark task extractor
│   ├── llm_client.py          # Multi-provider client (Groq, OpenAI, Ollama) & .env loader
│   ├── run_local_audit.py     # End-to-end local demonstration runner
│   ├── sandbox.py             # Isolated subprocess execution sandbox
│   ├── verifier_gate.py       # Dual-execution judge (Soundness & Completeness)
│   └── verifier_synthesizer.py # Autonomous test synthesis orchestrator
├── requirements.txt           # Lightweight dependencies (pytest, datasets, rich)
└── README.md
```

---

## 🔬 3-Stage Research Roadmap

| Stage | Benchmark Focus | Verification Frontier | Hardware Profile |
| :--- | :--- | :--- | :--- |
| **Stage 1** | **SWE-bench Verified** | Python code AST mutations, branch omissions, unit test gaps | Standard laptop / Single GPU |
| **Stage 2** | **Terminal-Bench** | Stateful Linux OS, filesystem diffs, exit-code & stdout faking | Multi-container Docker host |
| **Stage 3** | **DeepSWE** | Polyglot (Python, Go, TS, Rust), non-contaminated real-world repositories | Distributed cluster / Cloud grant |

---

## 📖 Key Documentation

- 📚 **[Academic Literature Survey](docs/LITERATURE_SURVEY.md)**: Comprehensive survey across coding agent benchmarks, test incompleteness, mutation analysis, and automated verifier synthesis.
- 📄 **[Research Plan & Epistemic Thesis](docs/RESEARCH_PLAN.md)**: Formal mathematical definitions, surviving mutant rates, and target venues (EMNLP / ICLR / ICSE).
- 👥 **[Teammate Onboarding Guide](docs/TEAM_ONBOARDING.md)**: Zero-friction guide for teammates with practical milestones.
- 📋 **[Resource Requirements Proposal](docs/GRANT_PROPOSAL.md)**: Compute, storage, and token requirements for cloud research access.