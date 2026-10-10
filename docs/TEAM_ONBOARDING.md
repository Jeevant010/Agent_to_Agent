# Teammate Onboarding Guide: 3-Weekend Practical Milestones

Welcome to the project! This guide is written so that **any team member with a standard laptop** can set up the environment, run their first experiment in 10 minutes, and contribute directly to the research paper.

---

## 1. Quick Local Setup (Under 5 Minutes)

### Step 1: Clone & Navigate to Repository
```bash
git clone https://github.com/Jeevant010/Agent_to_Agent.git
cd Agent_to_Agent
```

### Step 2: Set Up Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Run the Local Verifier Demonstration
Run our interactive test script to verify that your environment works:
```bash
python3 scripts/run_local_audit.py
```
If you see the colored table showing **"MUTANT SURVIVED (Weak Verifier Found)"** and **"MUTANT KILLED"**, your machine is 100% ready!

---

## 2. The 3-Weekend Milestones for Teammates

### 🎯 Weekend 1: Data Curation & Task Inspection
- **Goal:** Download and inspect 5 real bug-fix tasks from `SWE-bench_Verified` without downloading gigabytes of Docker images.
- **Action:** Run:
  ```bash
  python3 scripts/download_subset.py --count 5 --output data/curated_tasks.json
  ```
- **Deliverable:** Inspect `data/curated_tasks.json`. Look at the `patch` (what the human developer wrote) and `test_patch` (what tests they wrote). Pick one task and read the code.

---

### 🎯 Weekend 2: AST Mutation Testing
- **Goal:** Take a code patch and generate 3 realistic bugs (mutants) using our AST mutator script.
- **Action:** Run:
  ```bash
  python3 scripts/ast_mutator.py --task-id 0
  ```
- **Deliverable:** Find at least one mutated version where the existing test suite passes even though the logic was broken. Save the mutant diff as an artifact for our research results table.

---

### 🎯 Weekend 3: Verifier Hardening (Closing the Loop)
- **Goal:** Feed the working code + surviving mutant to an LLM (via local Ollama or API) and produce a new `pytest` function that kills the mutant.
- **Action:**
  1. Test the new assertion against the original patch: must output `PASS`.
  2. Test the new assertion against the mutant: must output `FAIL`.
- **Deliverable:** Record your first hardened test file!

---

## 3. Team Ownership Matrix

| Teammate | Role / Area | Responsibilities |
| :--- | :--- | :--- |
| **Lead / Systems** | Execution Pipeline & Harness | Maintain the runner scripts, Docker environments for Stage 2, and logging infrastructure. |
| **Teammate A** | AST Mutation & Parsing | Expand mutation operators (boundary conditions, state leakage, error suppression) using Python `ast` and `tree-sitter`. |
| **Teammate B** | Test Synthesis & LLM Prompting | Refine prompts for generating strict `pytest` assertions; test prompt strategies on local Ollama / Open-weights models. |
| **Teammate C** | Evaluation & Paper Results | Track baseline mutation kill rates, maintain the results spreadsheet, and prepare tables for the paper draft. |

---

## 4. Frequently Asked Questions

**Q: Do I need a powerful GPU on my laptop?**  
A: **No.** The entire AST mutation engine and test execution runs on a standard CPU. For the LLM generation step, you can either use a free/cheap API key (OpenAI/DeepSeek) or run a lightweight 3B/7B model locally using Ollama (`ollama run qwen2.5-coder:3b`).

**Q: Will this fill up my laptop's hard drive?**  
A: **No.** Our curated subset scripts download only the text JSON metadata (< 10 MB). We do not pull full multi-gigabyte Docker images until Stage 2 on dedicated lab hardware.
