# Two-Sided Verification Program

**Status:** planning document. Uncommitted.
**Scope:** Paper 1 (security pack) and Paper 2 (AAVS).
**Purpose:** define the goal, the corpus, the tooling, the artifacts to build, and the execution order.

---

## 1. Goal

### 1.1 One-sentence goal

Build and release a verifier-agnostic protocol that takes a code change and a repository, and
returns two independent verdicts:

1. **Security:** the targeted vulnerability is blocked, and no new weakness is introduced.
2. **Behavior:** the change preserves functional behavior, contracts, and execution state.

The protocol is used in two modes:

- **Artifact mode:** evaluate a candidate patch from an agent, a model, or a public patch file.
- **Checker mode:** evaluate a static checker or a test suite that is used as an oracle.

The same task record supports both modes. This is the unifying abstraction.

### 1.2 Why the problem matters

Current evaluation practice is one-sided:

- Security patch benchmarks ask whether the exploit is blocked, and often stop there.
- Coding-agent benchmarks ask whether the repository tests pass, and often stop there.
- Static checkers are used as oracles without calibration on the same code before and after a fix.

Three recent results constrain the design:

- **PVBench** (2026): over 40% of AVR patches that pass basic tests fail the developer's `PoC+`
  tests. The success rates reported by earlier AVR work are therefore inflated.
- **Beyond Bypass** (2026): LLM-generated security patches can introduce new weaknesses even when
  the targeted weakness is removed. The study measures this statically on 479 C/C++ functions.
- **On the Risks of using LLM-Generated Tests for Regression Testing** (2026): 8% to 17% of
  generated regression tests are fault-enforcing, while only 2.4% to 4.8% reveal faults. The
  developer suites detect only 14% to 30% of the enforced faults.

The missing measurement is not "are patches sometimes wrong". That is established. The missing
measurement is a **two-sided, checker-agnostic audit** that reports both false passes and false
rejections, on executable security and behavior tasks, with per-task provenance.

### 1.3 The two papers

| Paper | Working title | Scope | Contribution |
| :--- | :--- | :--- | :--- |
| Paper 1 | *Do Security Patches Actually Fix Vulnerabilities? A Two-Sided Dynamic Audit of AVR and Static Checkers* | 30 to 60 executable security tasks; CodeQL, Semgrep, Bandit, cppcheck; PoC and functional tests | Measurement, checker audit, released security harness |
| Paper 2 | *AAVS: A Verifier-Agnostic Protocol for Auditing Security and Behavioral Correctness of Agent Patches* | Security pack plus breakage pack plus state layer; repository-level and container-level tasks | Unified protocol, breakage gate, released benchmark, leaderboard re-evaluation |

Paper 1 is deliberately shorter. It is a measurement and artifact paper, not a new repair model.
Paper 2 is the larger system paper. The security pack is a subsystem inside AAVS, not the thesis.

The Paper 1 workspace is [`../secpatch-audit/`](../secpatch-audit/README.md). It contains the
goal, corpus, tooling, protocol, work split, explainer, novelty assessment, and paper outline for
the security paper only.

### 1.4 One-slide statement

> **Problem.** Security patches are graded by exploit blocking, and code patches are graded by
> repository tests. Both grades are one-sided. Static checkers are used as oracles without
> calibration.
>
> **Goal.** A two-sided, dynamic, checker-agnostic protocol that reports security correctness and
> behavioral correctness for the same change, with false-pass and false-rejection rates and
> per-task provenance.
>
> **Paper 1.** Security pack on 30 to 60 executable CVEs, plus an audit of the static checkers
> used as oracles.
>
> **Paper 2.** AAVS: the same protocol extended to breakage, contracts, and execution state.

### 1.5 Presentation outline

1. **The problem.** Security patches are graded by exploit blocking; code patches are graded by
   repository tests. Both grades are one-sided, and static checkers are used as oracles without
   calibration.
2. **The evidence.** PVBench reports over 40% false success under `PoC+`; Beyond Bypass reports
   security regressions in LLM patches; LLM-generated regression tests can enforce faults.
3. **The protocol.** One task record, two modes (artifact and checker), two gates (security and
   breakage), two-sided metrics.
4. **The corpus.** Four tiers: synthetic calibration, real CVE breadth, executable security
   tasks, and repository-level breakage tasks.
5. **The results.** `SFR` and `FRR` for security; `SMR`, `VHR`, `BDR`, and `FAR` for breakage.
6. **The split.** Paper 1 is the security measurement and checker audit; Paper 2 is the AAVS
   system and release.

---

## 2. What the referenced repository demonstrates

The repository `JacknCrack18/Music-Kit-Test` was examined at commit `65a5a05`.

### 2.1 Evidence

| Observation | Evidence |
| :--- | :--- |
| The only workflow is GitHub's default CodeQL setup | The Actions API returns one workflow at `dynamic/github-code-scanning/codeql`. |
| No custom workflow is committed | The repository has no `.github/` directory and no workflow YAML file. |
| One run exists and completed | Run `38216315375`, named `CodeQL Setup`, completed successfully. The `Analyze (c-cpp)` job completed. |
| No public findings are available | The code-scanning alerts API requires authentication. The repository contains no SARIF file, baseline, or findings report. |
| The codebase is small | 1,863 lines of C++: 976 in `software/src/main.cpp`, 765 in `software/old.cpp`, plus configuration. |
| The attack surface is small | No network stack, no authentication, no untrusted string parsing, no dynamic allocation, no file or command execution. The firmware reads GPIO pins and writes to an OLED, LEDs, and a DAC. |
| There is no test suite or PoC | The repository has no tests and no exploit harness. |

### 2.2 Interpretation

The security work in the referenced repository is a **default CodeQL scan**, not a security
pipeline. CodeQL is a static analyzer. It does not generate patches, apply fixes, or verify that a
fix is complete. The default setup is automatic: GitHub selects the languages, runs autobuild, and
stores alerts in the code-scanning service. No custom queries, build configuration, or result
analysis are present in the repository.

The small attack surface makes a low number of security findings likely. That is not evidence that
the code is secure in a general sense. It is evidence that the code is not a useful vulnerability
corpus.

### 2.3 Permitted use

The repository can serve as:

- a build and integration smoke test for the C/C++ toolchain;
- an example of a real hardware project with a constrained attack surface;
- a negative control in a discussion of why "run CodeQL" is not a security program.

It should not serve as the main corpus, the main benchmark, or the main evidence for a security
paper.

---

## 3. Point 1 strengthened: the corpus

### 3.1 The wrong target

A single large repository with many reported vulnerabilities is not a benchmark. It lacks:

- a pinned vulnerable commit and a pinned fixed commit for each case;
- a reproducible build;
- a deterministic PoC that fails before the fix and passes after it;
- functional tests that pass on the fixed version;
- ground-truth CWE labels;
- a license that permits redistribution and evaluation.

Without these, a large repository produces scanner alerts, not measurable claims. Code size is not
the same as statistical power.

### 3.2 The right target

The corpus is a set of **executable vulnerable/fixed pairs**. Each pair is a task record with a
build, a PoC, a functional suite, and provenance. Scale is added after the first 30 tasks are
reproducible.

The portfolio has four tiers. Each tier has a different job.

| Tier | Dataset | Scale | Role | Why it is used |
| :--- | :--- | :--- | :--- | :--- |
| A | OWASP Benchmark Java | 2,740 cases: 1,415 vulnerable, 1,325 safe; 11 CWEs | Checker calibration | Paired vulnerable/safe cases with ground truth |
| A | Juliet C/C++ 1.3 | 64,099 cases; 118 CWEs | Checker calibration | Large, compilable, ground-truth labels |
| A | Juliet Java 1.3 | 28,881 cases; 112 CWEs | Checker calibration | Large, compilable, ground-truth labels |
| B | CVEfixes (initial release) | 5,365 CVEs; 5,495 fixing commits; 18,249 files; 50,322 functions; 180 CWEs | Real-world breadth | Real commits across many languages |
| B | CrossVul | 27,476 files; 13,738 vulnerable/fixed pairs; 5,131 CVEs; 168 CWEs | Real-world breadth | Cross-language paired files |
| B | CWE-Bench-Java | 120 CVEs; 4 CWEs | Java checker audit | Manually vetted, buildable Java projects |
| B | L-AVRBench | 70 C/C++ functions with PoC and functional tests | Test-based AVR | Executable C/C++ cases |
| C | PATCHEVAL | 1,000 CVEs; 65 CWEs; 230 Docker cases; Go, JavaScript, Python | Executable security tasks | PoC plus unit tests in real repositories |
| C | PVBench | 209 cases; 20 C/C++ projects; 12 CWEs | Executable security tasks | Basic tests plus developer `PoC+` tests |
| C | BAC-Bench (repair) | 46 vulnerabilities; 6 web apps; Java, PHP, Go, Python | Logic-vulnerability tasks | Sandboxed runtime, PoC, functional tests |
| C | AutoSUIT | 951 released samples; 232 CWEs; C, C++, Java, Python | Security unit tests | Functional and security suites |
| C | SusVibes | 186 tasks; 108 projects; 77 CWEs | Real Python security tasks | Real CVE pairs with vulnerable/fixed versions |
| D | SWE-bench Verified / Lite | 500 / 300 tasks | Breakage and agent behavior | Repository-level patches with tests |
| D | Terminal-Bench | Environment tasks | State breakage | Filesystem, exit code, and stdout oracles |

Tier A is for calibration, not for headline claims. Synthetic cases are useful because the ground
truth is exact and the scale is large. They are not evidence that a checker works on real code.

Tier B is for breadth and for training or retrieval. Most of these records are file-level or
function-level pairs. They are useful for studying checker behavior, but they usually lack a
runtime harness.

Tier C is the core of Paper 1. These datasets provide executable environments, PoCs, and tests.
The first paper should be built on this tier.

Tier D is the core of Paper 2. These are repository-level and environment-level tasks. They are
where breakage, state, and reward hacking become measurable.

### 3.3 Selection criteria

A task is admitted only if all of the following hold:

1. The vulnerable and fixed versions exist at pinned commits.
2. The project builds in a container with a single command.
3. A deterministic PoC fails on the vulnerable version and passes on the fixed version.
4. A functional test suite passes on the fixed version.
5. The CWE label and the fix commit are recorded.
6. The license permits research use and, where possible, redistribution.
7. The task runs within a fixed budget, initially 10 minutes per task on the available hardware.
8. The evaluation does not require network access.
9. No secrets, personal data, or unlicensed code are included.
10. Flaky tests are quarantined or the task is excluded.

Any task that violates criterion 2, 3, or 4 is removed before measurement. The exclusion is
recorded with the reason. A benchmark with 30 valid tasks is better than a benchmark with 200
unverified tasks.

### 3.4 Initial slate

The first slate is 30 tasks:

| Source | Count | Language | Purpose |
| :--- | ---: | :--- | :--- |
| PATCHEVAL Verified | 10 | Python, Go, JavaScript | Dockerized PoC plus unit tests |
| PVBench | 10 | C/C++ | Basic tests plus `PoC+` tests |
| BAC-Bench | 5 | Java, PHP, Go, Python | Logic vulnerabilities with runtime |
| CWE-Bench-Java | 5 | Java | Checker audit on real Java CVEs |

The mix covers four languages, memory-safety and logic vulnerabilities, and four checkers. It is
small enough to debug and broad enough to support a paper.

After the first 30 tasks are reproducible, the slate expands to 60. The expansion adds:

- 10 more PATCHEVAL cases in the least represented language;
- 10 more PVBench cases in the least represented CWE;
- 10 CWE-Bench-Java cases for CodeQL and Semgrep comparison;
- 10 SusVibes or AutoSUIT cases for Python security tests.

### 3.5 What to build for each task

Each task directory contains:

```text
tasks/<task_id>/
├── manifest.json          # pinned commits, language, CWE, license, commands
├── Dockerfile             # reproducible build and runtime
├── gold.patch             # developer fix
├── test.patch             # developer tests, when separate
├── poc/                   # exploit harness and expected results
├── tests/                 # functional suite
├── expected.json          # vulnerable and fixed outcomes
├── provenance.json        # source URL, retrieval date, hashes
└── README.md              # build, run, and known limitations
```

The manifest schema is the contract. A minimal record:

```json
{
  "task_id": "patcheval-cve-2021-23376",
  "repo_url": "https://github.com/...",
  "base_commit": "<sha>",
  "fix_commit": "<sha>",
  "language": "python",
  "cwe": "CWE-78",
  "license": "Apache-2.0",
  "image": "ghcr.io/...",
  "build": {"command": "...", "timeout_sec": 600},
  "poc": {"command": "...", "vulnerable_exit": 0, "fixed_exit": 1},
  "tests": {"command": "...", "fixed_exit": 0},
  "provenance": {"source": "...", "retrieved": "2026-11-02", "sha256": "..."}
}
```

The exact fields are refined during implementation. The important property is that every command,
version, and expected result is recorded, so the task can be re-run without human interpretation.

### 3.6 Embedded and Arduino scope

The Music Kit repository is not a vulnerability corpus. If an embedded pack is required, it is a
separate effort:

- select ESP-IDF, Arduino library, or IoT CVEs with public PoCs;
- build with PlatformIO and generate `compile_commands.json`;
- run CodeQL C/C++ with an explicit build command, not autobuild;
- use cppcheck and clang-tidy as additional checkers;
- verify that the checker actually models the relevant APIs before claiming coverage;
- keep the pack as a case study, not as the main benchmark.

Embedded runtimes are hard to reproduce in Docker. A host-compilable C/C++ subset is the practical
starting point. Full firmware emulation is out of scope for Paper 1.

---

## 4. Point 2 strengthened: tooling and artifacts

### 4.1 Tool categories

The tools are separated by role. Mixing them is a common source of confused claims.

| Layer | Use | Build |
| :--- | :--- | :--- |
| Corpus | Hugging Face datasets, Zenodo, Git | Manifest loader, task validator |
| Execution | Docker, pytest, JUnit, `go test`, `npm test` | Container runner, timeout, log capture |
| Security checkers | CodeQL, Semgrep, Bandit, cppcheck, clang-tidy, Infer | SARIF adapter, version pin, result normalizer |
| PoC | pytest, shell, sanitizers, AFL++, libFuzzer, Atheris | PoC harness, deterministic runner |
| Repair baselines | LLM APIs via `litellm` and `instructor`; reproducible AVR systems | Patch generator adapter, patch applier |
| Breakage | pytest, Hypothesis, differential fuzzing, `coverage.py`, `mutmut`, `cosmic-ray` | Breakage gate, contract checks, state diff |
| Data | SQLite or DuckDB, JSONL, Pydantic, Polars | Schema, provenance, reports |
| Operations | `uv`, `ruff`, `mypy`, `typer`, `rich`, MLflow | CLI, experiment tracking |

### 4.2 Checkers under test

The checkers are systems under test, not the architecture.

| Checker | Languages | Role | Notes |
| :--- | :--- | :--- | :--- |
| CodeQL | C/C++, Java, Python, JavaScript, Go | Deep static analysis | Needs a build database; version and query pack must be pinned |
| Semgrep | Many | Fast pattern and taint analysis | Easy to run; custom rules must be versioned |
| Bandit | Python | Python security patterns | Limited to Python; useful as a fast baseline |
| cppcheck | C/C++ | Defect and security patterns | Works without a full build; good for embedded |
| clang-tidy | C/C++ | Compiler-based checks | Needs `compile_commands.json` |
| Infer | Java, C/C++, Objective-C | Interprocedural analysis | Heavier setup; optional |

CodeQL is one adapter. It is not the system. A paper that depends on a single proprietary-style
checker is fragile and hard to reproduce.

### 4.3 Repair baselines

The first paper does not need a new repair model. It needs patches to evaluate. The patch sources
are:

- developer fixes from the task corpus;
- public agent patches, where available;
- LLM-generated patches from a pinned model and prompt;
- reproducible AVR baselines, when their environments can be rebuilt.

If an LLM is used, the model, version, temperature, prompt, and retry budget are recorded. A patch
is not a result until it is applied and executed.

### 4.4 What must be created

Ranked by importance and novelty:

1. **Task manifest and loader.** Applies the base commit, the gold patch, and the test patch; runs
   the build; records the result. Required, not novel.
2. **Baseline validator.** Confirms that the vulnerable version fails the PoC and the fixed version
   passes the PoC and the functional suite. Required, not novel.
3. **SARIF normalizer.** Converts CodeQL, Semgrep, Bandit, cppcheck, and clang-tidy output into one
   schema with file, line, rule, CWE, and severity. Required, not novel.
4. **Security gate.** Checks exploit blocked, functional tests pass, and no new CWE is introduced.
   Core contribution.
5. **Security-regression mutator.** Mutates the developer fix into patches that still pass the
   functional suite but either leave the exploit path open or introduce a new weakness. Core
   contribution.
6. **Checker audit runner.** Runs each checker on the vulnerable version, the fixed version, and
   the security-regression mutants; computes recall, precision, and false-repair rate. Core
   contribution.
7. **Breakage gate.** Runs the original suite, a hardened suite, differential fuzzing, contract
   checks, and state checks. Core contribution for Paper 2.
8. **Provenance and report generator.** Emits JSONL and Markdown tables with task IDs, commands,
   versions, hashes, and denominators. Required for release.
9. **RAG memory.** Retrieval over verified fixes. Useful later; not the oracle.
10. **LLM defender.** Synthesizes tests or invariants for survivors. Useful after the deterministic
    gate works.

### 4.5 What not to build

- Another static analyzer.
- Another CodeQL wrapper presented as a research contribution.
- A RAG chatbot for vulnerability repair.
- An end-to-end "AI fixes vulnerabilities" product.
- A giant scraped dataset without PoCs and tests.
- A custom SWE-bench harness.
- A Firecracker or microVM sandbox before Docker works.
- A new query language or rule engine.

These are either crowded, out of scope, or premature.

### 4.6 Module map

```text
aavs/
├── core/
│   ├── manifest.py        # schema and validation
│   ├── loader.py          # repo checkout, patch application
│   ├── runner.py          # container execution, timeout, logs
│   ├── gate.py            # shared two-sided gate interface
│   ├── provenance.py      # hashes, versions, commands
│   └── metrics.py         # denominators and report tables
├── checkers/
│   ├── sarif.py           # normalized result schema
│   ├── codeql.py
│   ├── semgrep.py
│   ├── bandit.py
│   └── cppcheck.py
├── security/
│   ├── poc.py             # PoC harness
│   ├── gate.py            # security side
│   ├── mutator.py         # security-regression mutants
│   ├── cwe.py             # CWE normalization
│   └── datasets/          # task adapters
├── breakage/
│   ├── regression.py      # original and hardened suites
│   ├── differential.py    # differential fuzzing
│   ├── contracts.py       # API and invariant checks
│   └── state.py           # filesystem, exit code, stdout
├── corpus/
│   ├── manifests/
│   └── tasks/
└── reports/
```

The exact package layout can change. The boundaries should not: corpus, execution, checkers,
security gate, breakage gate, reporting.

---

## 5. Protocol and metrics

### 5.1 Task tuple

A task is:

```text
T = (repo, base_commit, fix_commit, build, poc, tests, cwe, license, image)
```

The reference fix is `p*`. A candidate patch is `p`.

### 5.2 Artifact mode

```text
verdict(T, p) = (security, behavior, provenance)
```

The gate applies `p` to `base_commit`, builds, and runs the PoC, the functional suite, the
hardened suite, and the checker. The result is a pair of verdicts, not a single pass/fail.

### 5.3 Checker mode

```text
audit(T, K) = (recall_on_vulnerable, precision_on_fixed, false_repair_rate, cost)
```

The checker `K` is run on:

- the vulnerable version;
- the fixed version;
- security-regression mutants of the fixed version;
- benign refactors of the fixed version, as a false-positive control.

Checker mode is the "audit the auditor" layer. It is the main cross-workstream asset.

### 5.4 Security gate

For each task:

1. `V0`: the PoC must fail on `base_commit` (the exploit works).
2. `V1`: the PoC must pass on `base_commit + p*` (the exploit is blocked).
3. `V2`: the functional suite must pass on `base_commit + p*`.
4. `V3`: the checker must report no new CWE on `base_commit + p*`.

For a candidate patch `p`:

1. `P0`: the PoC must pass on `base_commit + p`.
2. `P1`: the functional suite must pass.
3. `P2`: the checker must report no new CWE.
4. `P3`: when a `PoC+` test exists, it must pass.

The gate accepts `p` only if `P0` through `P3` hold. If `p*` fails any of `P0` through `P3`, the
task is either mis-specified or the gate is too strict. Both are recorded.

### 5.5 Breakage gate

The breakage gate is the second tool. It runs:

- the original repository suite;
- a hardened suite produced by mutation and synthesis;
- differential fuzzing against a reference implementation or a previous version;
- contract checks for types, invariants, and API behavior;
- state checks for filesystem, exit codes, stdout, and logs.

A candidate patch is accepted only if the original suite and the hardened suite pass, and no
contract or state check regresses. A valid developer patch that fails the gate is a false
rejection and is reported.

### 5.6 Metrics

| Metric | Definition | Paper |
| :--- | :--- | :--- |
| `SPR` | Candidate patches that block the PoC / candidate patches | 1 |
| `SFR` | Patches that block the PoC but fail `PoC+` or introduce a new CWE / candidate patches | 1 |
| `CSR` | Vulnerable cases flagged by checker `K` / vulnerable cases | 1 |
| `CPR` | Fixed cases not flagged by checker `K` / fixed cases | 1 |
| `CFR` | Patches that pass checker `K` but fail the PoC / patches | 1 |
| `FRR` | Valid developer fixes rejected by the gate / valid developer fixes | 1, 2 |
| `SMR` | Surviving mutants / valid mutants | 2 |
| `VHR` | Survivors killed by the hardened suite / survivors | 2 |
| `BDR` | Patches that pass the original suite but fail the hardened suite / patches | 2 |
| `FAR` | Valid patches rejected by the breakage gate / valid patches | 2 |

`SFR` and `FRR` are the headline pair for Paper 1. `SMR`, `VHR`, `BDR`, and `FAR` are the headline
pair for Paper 2. Every metric is reported with an explicit denominator and the number of excluded
tasks.

### 5.7 Two-sided matrix

| | Behavior passes | Behavior fails |
| :--- | :--- | :--- |
| **Security passes** | Acceptable | Dangerous: security-only fix |
| **Security fails** | Security theater: behavior preserved, exploit still works | Obvious reject |

The matrix is the presentation device. It makes the two-sided claim visible in one table and
prevents a single score from hiding the failure mode.

---

## 6. Novelty and positioning

### 6.1 What is crowded

| Area | Representative work | What it establishes |
| :--- | :--- | :--- |
| LLM vulnerability repair | EvoRepair, RAVEN, VulMaster, VulRepair | LLMs can repair many CVEs; RAG and experience banks improve scores |
| Patch validation | PVBench, L-AVRBench, PATCHEVAL | Basic tests overestimate patch success; `PoC+` and executable tests expose failures |
| Security regression | Beyond Bypass | LLM patches can introduce new weaknesses; measured statically |
| Security unit tests | AutoSUIT | Functional and security suites can be generated for C, C++, Java, Python |
| Benchmark design | On the Reliability of LLM-Based Vulnerability Patching Benchmarks | Benchmark choices change reported success |
| Dynamic reproduction | Google Mantis | Sandboxed reproduction reduces scanner false positives |
| Breakage | On the Risks of using LLM-Generated Tests; differential fuzzing studies | Generated tests can enforce faults; test suites miss non-equivalent refactorings |

The security space is moving quickly. A paper that claims "LLM security patches are often
incomplete" is already late. A paper that claims "RAG improves vulnerability repair" is in a
crowded lane.

### 6.2 What is still open

1. **Two-sided measurement.** Report false passes and false rejections on the same tasks, with
   explicit denominators. Most work reports only false passes.
2. **Cross-checker audit.** Evaluate CodeQL, Semgrep, Bandit, and cppcheck as verifiers on
   vulnerable, fixed, and security-mutant triples. Most work evaluates checkers only as scanners.
3. **Security and breakage in one protocol.** Use the same task tuple and gate to produce both
   verdicts. Most work studies them separately.
4. **A released executable artifact.** 30 to 60 tasks with Docker, PoCs, tests, manifests, and
   provenance. Many papers release prompts or patches, not runnable tasks.
5. **Artifact mode and checker mode.** One protocol can audit a patch or audit a checker. This is
   the cross-workstream asset.

### 6.3 Defensible claims

- The program measures both directions of error, on the same executable tasks.
- The program audits the checkers used as oracles, not only the patches.
- The program unifies security verification and behavioral verification under one protocol.
- The program releases a reproducible task set with per-task provenance.
- The program reports false rejections of valid developer fixes, not only false passes.

### 6.4 Claims to avoid

- "First to show that LLM security patches are incomplete." PVBench, Beyond Bypass, and others
  already show this.
- "First to use mutation testing." Mutation testing dates to the 1970s.
- "First RAG for vulnerability repair." EvoRepair and RAVEN already occupy this lane.
- "CodeQL-based vulnerability detection is novel." CWE-Bench, IRIS, and many others use it.
- "The largest benchmark." Juliet, OWASP Benchmark, CVEfixes, and CrossVul are larger.
- "The gate is sound." The gate is dynamic and can miss. Report limitations.
- "Zero false positives and zero false negatives." No dynamic gate achieves this.

### 6.5 Positioning statement

> Prior work shows that security patches can pass tests and still be incomplete, and that
> LLM-generated tests can encode faults. This program contributes a released, checker-agnostic
> protocol that measures both directions of error, on executable security and behavior tasks, and
> audits the static checkers used as oracles.

---

## 7. Work plan

### 7.1 Twelve-week plan

| Week | Work | Deliverable | Acceptance |
| ---: | :--- | :--- | :--- |
| 1 | Select 30 tasks and write manifests | `corpus/manifests/*.json` | 30 tasks with pinned commits, PoC, tests, license |
| 2 | Build loader, Docker runner, baseline validator | `core/loader.py`, `core/runner.py` | Gold passes; base fails PoC; all tasks reproduce |
| 3 | SARIF adapters and first checker runs | `checkers/*` | CodeQL, Semgrep, Bandit, cppcheck produce normalized output |
| 4 | Checker audit on vulnerable/fixed pairs | Checker report | `CSR`, `CPR`, and cost per checker |
| 5 | Security gate | `security/gate.py` | Gold passes the gate; known bad patches fail |
| 6 | Security-regression mutator | `security/mutator.py` | Mutants pass functional tests but fail PoC or add a CWE |
| 7 | Two-sided measurement on 30 tasks | Measurement report | `SPR`, `SFR`, `FRR`, `CSR`, `CPR`, `CFR` with denominators |
| 8 | Paper 1 draft | 8-page draft | Every claim backed by a table |
| 9 | Breakage gate: original and hardened suites | `breakage/regression.py` | Gold passes; broken patches fail |
| 10 | Differential fuzzing, contracts, state checks | `breakage/*` | At least one non-test breakage case detected |
| 11 | Scale to 60 tasks and public patches | Artifact | Reproducible run from a clean container |
| 12 | Paper 2 draft and release | Repository and report | Artifact-evaluation ready |

### 7.2 Kill criteria

- If fewer than 60% of the selected tasks reproduce (base fails PoC, gold passes PoC and tests),
  the substrate is defective. Fix it before scaling.
- If fewer than 10% of tasks show any checker disagreement, the checker audit lacks signal.
  Expand the CWE set or reframe the paper.
- If the gold patch is rejected by the security gate more than 20% of the time, the gate is too
  strict. Debug before claiming false rejection.
- If security-regression mutants are not executable or not semantically valid, the attacker is not
  usable. Do not report mutant rates from invalid mutants.
- If the breakage gate rejects more than 20% of gold patches, it is too strict.
- If a non-trivial two-sided table cannot be produced in eight weeks, narrow Paper 1 to a checker
  audit and defer the system claim.

### 7.3 Order of work

1. Manifest and loader.
2. Baseline validator.
3. SARIF normalizer.
4. Security gate.
5. Checker audit.
6. Security-regression mutator.
7. Two-sided measurement.
8. Breakage gate.
9. Scale and release.

The first six items produce Paper 1. Items 7 through 9 produce Paper 2.

---

## 8. Risks and mitigations

| Risk | Likelihood | Mitigation |
| :--- | :--- | :--- |
| Dataset licenses restrict redistribution | Medium | Prefer Apache-2.0, MIT, CC0, and CC BY; record the license per task; do not redistribute restricted code |
| PoCs are flaky or environment-dependent | High | Pin versions and commits; use Docker; fix seeds; quarantine flaky tasks |
| Runtime and storage costs grow quickly | High | Start with 30 tasks; cache images; parallelize; set per-task timeouts |
| Training-data contamination | Medium | Prefer post-cutoff CVEs; record dates; hold out a clean subset |
| Checker versions drift | High | Pin versions; store SARIF; re-run in the same container |
| False rejection of valid fixes | Medium | Report `FRR`; inspect every gold failure; tune the gate |
| Scope creep into a repair system | High | Two papers; security first; no RAG before the gate works |
| Novelty collision | High | Publish a preprint early; emphasize measurement and artifact, not the loop |
| Security pack becomes the thesis | Medium | Keep security as one axis; the organizing frame is verifier soundness and completeness |

---

## 9. Immediate next actions

1. Approve the 30-task slate and the 60-task target.
2. Create the `aavs/` package skeleton and the manifest schema.
3. Build the loader and baseline validator on three PATCHEVAL tasks.
4. Add Semgrep and Bandit adapters first, then CodeQL and cppcheck.
5. Write the one-page abstract and the task table before writing code for the gate.

The first three actions produce a reproducible substrate. The next two produce the first
measurement. No LLM key is required for this phase.

---

## 10. Selected references

- Yu et al. *Patch Validation in Automated Vulnerability Repair.* arXiv:2603.06858, 2026. PVBench.
- Rawajfih, Mahmud, and Arnold. *Beyond Bypass: Measuring Vulnerability Regression in
  LLM-Generated Security Patches.* AITest 2026.
- Charoosaei, Richter, and Papadakis. *On the Risks of using LLM-Generated Tests for Regression
  Testing.* arXiv:2610.11835, 2026.
- Han et al. *Rethinking the Capability of Fine-Tuned Language Models for Automated Vulnerability
  Repair.* ICSE 2026. L-AVRBench.
- Osebe et al. *AutoSUIT Bench: Automated Security UnIt Test Benchmark for LLM Coding.* Findings
  of ACL 2026.
- Wei et al. *PATCHEVAL: A New Benchmark for Evaluating LLMs on Patching Real-World
  Vulnerabilities.* arXiv:2511.11019, 2025.
- Liu et al. *Repairing Broken Access Control in Web Applications with LLMs: An Empirical
  Benchmark Study.* arXiv:2610.34290, 2026. BAC-Bench.
- *On the Reliability of LLM-Based Vulnerability Patching Benchmarks.* 2026.
- Google Cloud. *Getting started with the Mantis harness to find and fix bugs.* 2026.
- NIST. *Juliet Test Suite 1.3.* SARD test suites 111 and 112.
- OWASP. *OWASP Benchmark.*
- Bhandari, Naseer, and Moonen. *CVEfixes.* PROMISE 2021.
- Nikitopoulos et al. *CrossVul.* ESEC/FSE 2021.
- *CWE-Bench-Java.* 2024.
- *SusVibes.* 2026.
