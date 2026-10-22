# System Architecture & Codebase Guide

> A plain-English guide explaining how this project works and what each file does.

---

## 1. What Does This Project Do?

When AI models write code (like fixing bugs in open-source projects), we test their code with standard unit tests to see if they solved the problem.

**The catch:** Studies show that up to **77% of benchmark unit tests have blind spots**. An AI can write buggy or broken code, and the test suite might still give it a "PASS" (a false positive).

**Our solution:**
1. **The Attacker:** We deliberately inject small, realistic bugs (mutations) into working code.
2. **The Audit:** We run the existing tests. If the tests let broken code pass, we found a blind spot!
3. **The Defender:** We ask an LLM (Groq or Ollama) to write a new test case that specifically catches that bug.
4. **The Judge:** We test the new test in a sandbox to guarantee two things:
   - It must PASS on the original working code (no false alarms).
   - It must FAIL on the buggy code (the bug is caught).

Once both conditions are met, the new test is accepted, closing the loophole.

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

### Core Subsystems (`scripts/`)

#### 1. Mutator Subsystem (`scripts/mutator/`) — Attacker
- [`scripts/mutator/ast_mutator.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/mutator/ast_mutator.py): Global AST mutation engine injecting comparison, boolean, and return perturbations.
- [`scripts/mutator/diff_parser.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/mutator/diff_parser.py): Parses unified diff hunks (`@@ -start,len +start,len @@`) and applies in-memory text patches.
- [`scripts/mutator/ast_transformers.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/mutator/ast_transformers.py): Line-constrained AST transformers that restrict mutations strictly to modified patch lines.
- [`scripts/mutator/patch_mutator.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/mutator/patch_mutator.py): Orchestrates diff parsing, in-memory patching, and line-constrained mutant generation.

#### 2. Verifier Subsystem (`scripts/verifier/`) — Defender
- [`scripts/verifier/llm_client.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/verifier/llm_client.py): Multi-provider client (Groq Llama 3.3 70B, OpenAI, Ollama) with Cloudflare-safe headers and .env loader.
- [`scripts/verifier/code_sanitizer.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/verifier/code_sanitizer.py): Strips markdown fences and reasoning blocks (`<think>`), deduplicates imports, and extracts target functions.
- [`scripts/verifier/sandbox.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/verifier/sandbox.py): Spawns temporary directories for isolated pytest subprocess execution with timeouts.
- [`scripts/verifier/verifier_gate.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/verifier/verifier_gate.py): Dual-execution judge enforcing Soundness (gold pass) and Completeness (mutant kill).
- [`scripts/verifier/verifier_synthesizer.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/verifier/verifier_synthesizer.py): Orchestrates LLM synthesis prompts, iterative error feedback, and retry loops.

#### 3. Runners Subsystem (`scripts/runners/`) — Execution CLIs
- [`scripts/runners/run_local_audit.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/runners/run_local_audit.py): Interactive terminal audit demo with rich tables and live verifier hardening.
- [`scripts/runners/download_subset.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/runners/download_subset.py): Streams lightweight task parquets (< 5MB) from SWE-bench Verified.

---

### Benchmark Data (`data/`)

- [`data/curated_tasks.json`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/data/curated_tasks.json): Contains real bug-fix tasks downloaded from GitHub repositories (like `astropy`). Each task includes the problem description, the real code patch, and the unit tests written by human developers.

---

### Tests (`tests/`)

- [`tests/test_patch_mutator.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/tests/test_patch_mutator.py): Unit tests for unified diff parsing, in-memory patch application, and line-constrained AST mutations.
- [`tests/test_verifier_synthesizer.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/tests/test_verifier_synthesizer.py): Unit tests for markdown stripping, empty output validation, sandbox execution, and the dual-execution gate.

---

### Documentation (`docs/` & `deep-docs/`)

- [`docs/ARCHITECTURE.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/docs/ARCHITECTURE.md): *This file!* A friendly guide explaining what every file in the project does.
- [`docs/RESEARCH_PLAN.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/docs/RESEARCH_PLAN.md): The formal academic research plan targeting conferences like ACL, EMNLP, and ICLR.
- [`docs/TEAM_ONBOARDING.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/docs/TEAM_ONBOARDING.md): A quick-start guide for new teammates to set up their laptop and run their first experiment in 5 minutes.
- [`docs/GRANT_PROPOSAL.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/docs/GRANT_PROPOSAL.md): A proposal written for cloud compute grants and university funding.
- [`deep-docs/future_implementation.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/deep-docs/future_implementation.md): Future technical upgrades, including running tests in parallel across all CPU cores and automatic boundary value test generation.

---

### Settings & Environment

- [`.env.example`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/.env.example): Example file showing where to put your `GROQ_KEY`.
- [`.gitignore`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/.gitignore): Tells Git not to commit secret API keys or temporary cache files.
- [`pyproject.toml`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/pyproject.toml): Modern PEP 517/621 build configuration enabling editable installation (`pip install -e .`) and registering the `aavs-audit` CLI command.
- [`requirements.txt`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/requirements.txt): The 3 Python packages needed to run (`pytest`, `datasets`, `rich`).
- [`README.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/README.md): The main front page of the repository on GitHub.
