# 06. Novelty

## 1. The crowded space

| Area | Representative work | What it establishes |
| :--- | :--- | :--- |
| Automated vulnerability repair | EvoRepair, RAVEN, VulMaster, VulRepair | LLMs can repair many CVEs; RAG and experience banks improve scores |
| Patch validation | PVBench, L-AVRBench, PATCHEVAL | Basic tests overestimate patch success; `PoC+` and executable tests expose failures |
| Security regression | Beyond Bypass | LLM patches can introduce new weaknesses; measured statically |
| Security unit tests | AutoSUIT | Functional and security suites can be generated across C, C++, Java, Python |
| Benchmark design | On the Reliability of LLM-Based Vulnerability Patching Benchmarks | Benchmark choices change reported success |
| Dynamic reproduction | Google Mantis | Sandboxed reproduction reduces scanner false positives |
| Generated regression tests | On the Risks of using LLM-Generated Tests | Generated tests can enforce faults; developer suites miss many |
| Functional equivalence | Differential fuzzing studies | Test suites miss non-equivalent refactorings |

The security space is moving quickly. A paper that only says "LLM security patches are incomplete"
is late. A paper that says "RAG improves vulnerability repair" is in a crowded lane.

## 2. The open gap

The reviewed literature does not contain a single released protocol that combines:

1. **Two-sided measurement.** False passes and false rejections on the same executable tasks.
2. **Checker audit.** CodeQL, Semgrep, Bandit, and cppcheck evaluated as verifiers on vulnerable,
   fixed, and security-regression triples.
3. **Security plus behavior.** The same task record produces both verdicts.
4. **Released executable artifact.** 30 to 60 tasks with Docker, PoCs, tests, manifests, and
   provenance.
5. **Artifact mode and checker mode.** One protocol can audit a patch or audit a checker.

Absence in the reviewed corpus is evidence, not proof. The manuscript must say so.

## 3. Defensible claims

- The project reports both directions of error on the same tasks.
- The project audits the checkers used as oracles, not only the patches.
- The project unifies security verification and behavioral verification under one protocol.
- The project releases a reproducible task set with per-task provenance.
- The project reports false rejections of valid developer fixes.

Each claim is tied to a table or a released artifact.

## 4. Claims to avoid

| Claim | Why it fails |
| :--- | :--- |
| "First to show LLM security patches are incomplete" | PVBench, Beyond Bypass, and others already show it |
| "First to use mutation testing" | Mutation testing dates to the 1970s |
| "First RAG for vulnerability repair" | EvoRepair and RAVEN occupy this lane |
| "CodeQL-based detection is novel" | CWE-Bench, IRIS, and many others use it |
| "The largest benchmark" | Juliet, OWASP Benchmark, CVEfixes, and CrossVul are larger |
| "The gate is sound" | The gate is dynamic and can miss |
| "Zero false positives and zero false negatives" | No dynamic gate achieves this |
| "We solve vulnerability repair" | The project measures and verifies; it does not solve repair |

## 5. Positioning statement

> Prior work shows that security patches can pass tests and still be incomplete, and that
> LLM-generated tests can encode faults. This project contributes a released, checker-agnostic
> protocol that measures both directions of error, on executable security and behavior tasks, and
> audits the static checkers used as oracles.

## 6. Reviewer objections and responses

### "This is just PVBench with extra steps."

PVBench establishes that `PoC+` tests expose false success. This project adds:

- the checker audit on the same tasks;
- the false-rejection measurement;
- a released two-sided harness;
- the separation of security and behavior verdicts.

The paper must cite PVBench as the closest work and quantify the increment.

### "The checker audit is just a benchmark of static analyzers."

Static-analyzer benchmarks exist, but they usually score findings on vulnerable and safe code.
This project scores checkers as **patch verifiers** on vulnerable, fixed, and near-fixed code. The
question is not only "does it find the bug?" but "does it know the bug is fixed?"

### "The task set is too small."

Thirty tasks is enough for a measurement paper when every task is reproducible. The paper reports
confidence intervals and per-task results. The artifact can grow to 60. A small, verified set is
stronger than a large, noisy one.

### "The gate may reject valid fixes."

That is exactly what `FRR` measures. A high `FRR` is a negative result about the gate, and it is
reported. The gate is not assumed to be correct.

### "The security-regression mutants are synthetic."

They are derived from developer fixes and are executed. A mutant is valid only if it builds, passes
the functional suite, and still fails the PoC or adds a CWE. The paper reports the invalid rate and
the mutant families.

### "The work is contaminated by training data."

The corpus includes post-cutoff CVEs where possible. The paper records retrieval dates and includes
a held-out subset. Contamination is a threat, not a claim of immunity.

### "Why not just use developer tests?"

Developer tests are the target, not the oracle. The project measures what they miss. When `PoC+`
tests exist, they are used as an additional signal, not as ground truth for all behavior.

## 7. Paper 1 versus Paper 2

| Question | Paper 1 | Paper 2 |
| :--- | :--- | :--- |
| Security correctness | Yes | Yes |
| Behavior correctness | Functional tests | Functional, hardened, differential, contracts, state |
| Checker audit | Yes | Yes |
| False rejection | Yes | Yes |
| Container state | No | Yes |
| Reward hacking | No | Yes |
| Benchmark scale | 30 to 60 security tasks | Security plus repository and environment tasks |
| Main claim | Two-sided security patch audit | Unified verifier protocol |

Paper 1 is the narrow, defensible measurement. Paper 2 is the larger system. The security pack is a
subsystem of AAVS, not the thesis.

## 8. Publication strategy

- Publish a preprint after the 10-task pilot and the checker table exist.
- Submit Paper 1 to a software engineering or security venue with an artifact track.
- Keep the claims tied to the measured tasks.
- Release the harness and the task manifests with the paper.
- Use the Paper 1 artifact as the security subsystem in Paper 2.

The window is narrow. The work should be framed as a measurement and artifact contribution, not as
a new model.
