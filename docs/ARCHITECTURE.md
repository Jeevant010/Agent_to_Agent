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

### Running the Project (`scripts/`)

- [`scripts/run_local_audit.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/run_local_audit.py)  
  **The main demo runner.** It runs the whole process in your terminal with colorful tables. It injects bugs into a sample discount function, finds which bugs slip past the tests, and asks the LLM to write tests to fix the blind spots.

- [`scripts/ast_mutator.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/ast_mutator.py)  
  **The bug injector (Attacker).** It reads Python code, turns it into an Abstract Syntax Tree (AST), and creates variations with small realistic bugs (e.g., flipping `==` to `!=`, `<` to `<=`, `True` to `False`, or returning `None`).

- [`scripts/verifier_synthesizer.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/verifier_synthesizer.py)  
  **The synthesis coordinator (Defender).** It coordinates the LLM, the code cleaner, and the verification gate. If the LLM writes an invalid test, it sends the failure message back to the LLM and asks it to try again.

- [`scripts/llm_client.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/llm_client.py)  
  **The LLM connector.** A lightweight client that talks to Groq (Llama 3.3 70B), OpenAI, or local Ollama. It automatically loads your API key from `.env` and includes headers so Cloudflare doesn't block the request.

- [`scripts/code_sanitizer.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/code_sanitizer.py)  
  **The code cleaner.** Takes messy text from the LLM, strips out chat explanations and reasoning tags (`<think>`), removes duplicate imports, and makes sure the code is valid Python syntax before anything runs.

- [`scripts/sandbox.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/sandbox.py)  
  **The safe runner.** Runs `pytest` inside a clean, temporary folder on your computer so test runs don't interfere with each other or freeze your machine if a mutant loops forever.

- [`scripts/verifier_gate.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/verifier_gate.py)  
  **The judge.** Runs candidate tests twice: once on good code and once on bad code. It only approves the test if good code passes and bad code fails.

- [`scripts/download_subset.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/download_subset.py)  
  **The data downloader.** Downloads a small slice of real bug-fix tasks from the `SWE-bench_Verified` benchmark (< 5 MB) so you can test on real code without downloading gigabytes of Docker images.

---

### Benchmark Data (`data/`)

- [`data/curated_tasks.json`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/data/curated_tasks.json)  
  Contains real bug-fix tasks downloaded from GitHub repositories (like `astropy`). Each task includes the problem description, the real code patch, and the unit tests written by human developers.

---

### Tests (`tests/`)

- [`tests/test_verifier_synthesizer.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/tests/test_verifier_synthesizer.py)  
  Unit tests for our own pipeline code. It verifies that markdown stripping works, empty outputs are caught, the sandbox executes properly, and the dual-execution gate works.

---

### Documentation (`docs/` & `deep-docs/`)

- [`docs/ARCHITECTURE.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/docs/ARCHITECTURE.md)  
  *This file!* A friendly guide explaining what every file in the project does.
- [`docs/RESEARCH_PLAN.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/docs/RESEARCH_PLAN.md)  
  The formal academic research plan targeting conferences like ACL, EMNLP, and ICLR.
- [`docs/TEAM_ONBOARDING.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/docs/TEAM_ONBOARDING.md)  
  A quick-start guide for new teammates to set up their laptop and run their first experiment in 5 minutes.
- [`docs/GRANT_PROPOSAL.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/docs/GRANT_PROPOSAL.md)  
  A proposal written for cloud compute grants and university funding.
- [`deep-docs/future_implementation.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/deep-docs/future_implementation.md)  
  Future technical upgrades, including running tests in parallel across all CPU cores and automatic boundary value test generation.

---

### Settings & Environment

- [`.env.example`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/.env.example): Example file showing where to put your `GROQ_KEY`.
- [`.gitignore`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/.gitignore): Tells Git not to commit secret API keys or temporary cache files.
- [`requirements.txt`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/requirements.txt): The 3 Python packages needed to run (`pytest`, `datasets`, `rich`).
- [`README.md`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/README.md): The main front page of the repository on GitHub.
