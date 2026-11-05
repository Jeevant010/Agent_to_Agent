# Research Blueprint: Autonomous Adversarial Verifier Synthesis (AAVS)
## A 3-Stage Investigation into Verifier Hardening for Autonomous Coding & System Agents

**Target Venues:** ACL / EMNLP (Main / Findings), ICLR, ICSE / ISSTA (AI for Software Engineering)  
**Authors:** Research Team  
**Focus Area:** NLP for Software Engineering (NLP4SE), Autonomous Verifiers, Multi-Agent Self-Play, Reinforcement Learning with Verifiable Rewards (RLVR).

---

## 1. Executive Summary & Epistemic Thesis

Current benchmarks for Large Language Model (LLM) agents—such as **SWE-bench**, **Terminal-Bench**, and **DeepSWE**—assess task completion primarily through **outcome-based verification** (e.g., unit test pass/fail status or exit codes). 

Recent audits have established the premise, with different denominators:
- **77% of SWE-bench Verified instances admit at least one surviving program variant** (Probe to Generate, P0120).
- **345 patches were reclassified** as false passes, affecting 40.9% of SWE-bench Lite and 24.4% of Verified leaderboard entries (UTBoost, P0001).
- **19.71% of previously passing patches were rejected** after adversarial strengthening; the previous top agent falls to fifth (SWE-ABS, P0837).

Incomplete test coverage allows agents to pass benchmarks via **unfaithful shortcuts**, including:
  1. Hardcoding targeted edge cases.
  2. Bypassing unasserted preconditions and security invariants.
  3. Modifying hidden global state without triggering test failures.
  4. Silencing exceptions (`try...except: pass`).

### The Core Research Thesis
> **Outcome-based regression tests are insufficient as verifiers and reward signals for autonomous agents.**  
> Verification must be **adversarial, semantic, and autonomous**. By structuring verifier hardening as an adversarial game between a **Semantic Mutator Agent** (Attacker) and a **Trace-Conditioned Verifier Synthesizer** (Defender), the system can identify and eliminate test-suite loopholes without manual human engineering.

---

## 2. The Three-Stage Benchmark Progression

To build a foundational paper that scales from local experimentation to state-of-the-art multi-environment verification, the project executes across three progressive tiers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Python AST Mutation & Test Synthesis (SWE-bench Verified)          │
│ - Scope: 50-100 real-world Python bug-fixes from open-source repositories   │
│ - Focus: Single-language AST mutations, branch omissions, unit test gaps    │
│ - Hardware: Standard laptop / Single GPU (Ollama / vLLM 7B-14B models)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Stateful System & OS-Level Verifier Hardening (Terminal-Bench)      │
│ - Scope: Linux CLI tasks, package builds, daemon configurations, pipelines  │
│ - Focus: Filesystem state diffing, exit code faking, stdout reward-hacking  │
│ - Hardware: Multi-container Docker host, automated state-snapshot engine    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: Polyglot Multi-Repo Frontier (DeepSWE & Production Repositories)   │
│ - Scope: Multi-language (Python, TypeScript, Go, Rust), un-contaminated PRs │
│ - Focus: Tree-sitter cross-language AST parsing, zero-leak sandboxing       │
│ - Output: Publication of Hardened Benchmark Suite + Frontier Agent Ranking  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Mathematical & Algorithmic Formulation

### 3.1 Formal Definitions
Let a software verification task $T$ be represented by a tuple:
$$T = \langle \mathcal{S}_{\text{base}}, \mathcal{P}^*, \mathcal{V}_0 \rangle$$
where:
- $\mathcal{S}_{\text{base}}$ is the base codebase / container state.
- $\mathcal{P}^*$ is the reference human patch (the Gold Solution) that resolves the underlying issue.
- $\mathcal{V}_0$ is the initial verifier test suite (e.g., `pytest` suite or bash verification script).

Under the ground truth, the reference solution must satisfy the verifier:
$$\mathcal{V}_0(\mathcal{S}_{\text{base}} \oplus \mathcal{P}^*) = \text{PASS}$$

### 3.2 The Surviving Mutant (Weak Verifier) Condition
A Semantic Mutator operator $\mathcal{M}$ applies a semantic corruption to the patch:
$$\tilde{\mathcal{P}}_i = \mathcal{M}_i(\mathcal{P}^*), \quad \tilde{\mathcal{P}}_i \neq \mathcal{P}^*$$
where $\tilde{\mathcal{P}}_i$ introduces a deliberate logic flaw, state desynchronization, or boundary error.

A **Surviving Mutant (False Positive)** occurs when the initial verifier fails to detect the corruption:
$$\text{Status}(\tilde{\mathcal{P}}_i) = \begin{cases} 
\text{KILLED} & \text{if } \mathcal{V}_0(\mathcal{S}_{\text{base}} \oplus \tilde{\mathcal{P}}_i) = \text{FAIL} \\
\text{SURVIVED (Weakness Detected)} & \text{if } \mathcal{V}_0(\mathcal{S}_{\text{base}} \oplus \tilde{\mathcal{P}}_i) = \text{PASS}
\end{cases}$$

### 3.3 Verifier Hardening Synthesis
For every surviving mutant $\tilde{\mathcal{P}}_i$, the Verifier Synthesizer agent $\mathcal{G}_{\text{ver}}$ produces an auxiliary test assertion $\Delta \mathcal{V}_i$:
$$\mathcal{V}_{k+1} = \mathcal{V}_k \cup \Delta \mathcal{V}_i$$
subject to the **Strict Bi-Directional Validity Criteria**:
1. **Soundness:** $\mathcal{V}_{k+1}(\mathcal{S}_{\text{base}} \oplus \mathcal{P}^*) = \text{PASS}$ (The correct code must still pass).
2. **Completeness on Mutant:** $\mathcal{V}_{k+1}(\mathcal{S}_{\text{base}} \oplus \tilde{\mathcal{P}}_i) = \text{FAIL}$ (The corrupted code is strictly rejected).

---

## 4. Key Metrics for the Research Paper

| Metric Name | Mathematical Formulation | Scientific Purpose |
| :--- | :--- | :--- |
| **Initial Mutation Score ($MS_0$)** | $\frac{\text{Mutants Killed by } \mathcal{V}_0}{\text{Total Valid Mutants}}$ | Quantifies the vulnerability of existing industry benchmarks before the intervention. |
| **Surviving Mutant Rate (SMR)** | $1 - MS_0$ | Headline metric proving how often benchmark verifiers allow buggy code to pass. |
| **Hardened Mutation Score ($MS_{\text{hard}}$)** | $\frac{\text{Mutants Killed by } \mathcal{V}_{\text{hardened}}}{\text{Total Valid Mutants}}$ | Measures the rigor and closure of test loopholes achieved by the pipeline. |
| **Agent Accuracy Collapse ($\Delta \text{Pass@1}$)** | $\text{Pass@1}(\mathcal{V}_0) - \text{Pass@1}(\mathcal{V}_{\text{hardened}})$ | Re-evaluates top models (Claude 3.5, GPT-4o, Qwen-2.5-Coder) to show how much of their performance was inflated by weak tests. |

---

## 5. Experimental Protocol & Work Breakdown

### Phase 1: Local Prototype & Pilot (Weeks 1–4)
- Curate 20 lightweight Python tasks from `SWE-bench_Verified` (`psf/requests`, `pallets/flask`).
- Implement AST operator mutator in Python.
- Quantify baseline surviving mutants on unmodified SWE-bench tests.

### Phase 2: Autonomous Test Synthesizer (Weeks 5–8)
- Implement LLM prompt engine to generate targeted `pytest` assertions for surviving mutants.
- Run local validation: verify that generated tests pass on Gold Patch and fail on mutant.
- Integrate trace-conditioning using line execution coverage.

### Phase 3: Benchmark Re-Evaluation & Terminal-Bench Expansion (Weeks 9–14)
- Scale to 100+ tasks in SWE-bench.
- Adapt the system to Terminal-Bench (state and filesystem diff verification).
- Run evaluation across 4 top coding agents.
- Draft conference paper and submit to arXiv / EMNLP / ICLR.
