# 00. Goal

## 1. The problem

Security patches are usually judged by one question: does the exploit still work?

That question is necessary, but it is not sufficient. A patch can block the original exploit and
still:

- leave a semantically equivalent path open;
- fail the developer's `PoC+` tests, which encode root-cause and intent;
- introduce a new weakness in the same function;
- break functional behavior that the original tests do not cover.

The evaluation is one-sided. It rewards "the exploit is blocked" and does not measure "the fix is
complete and the code still works".

A second problem sits behind the first: static checkers are used as oracles without calibration.
A checker that flags the vulnerable version but also flags the fixed version is not a useful
verifier. A checker that stays silent on both is not a useful verifier either. The field needs to
measure the checker, not only the patch.

## 2. The evidence

| Result | What it shows |
| :--- | :--- |
| PVBench (2026): over 40% of AVR patches that pass basic tests fail developer `PoC+` tests | Basic tests overestimate patch success |
| Beyond Bypass (2026): LLM patches can introduce new weaknesses while removing the target | Patch-level security regression is real |
| On the Risks of using LLM-Generated Tests (2026): 8% to 17% of generated regression tests enforce faults | Generated tests can preserve the wrong behavior |
| L-AVRBench (ICSE 2026): match-based metrics do not capture functional and security correctness | Test-based evaluation is necessary |
| PATCHEVAL (2025): 1,000 CVEs, 230 Dockerized cases with PoC and unit tests | Executable security tasks are feasible at scale |
| AutoSUIT (ACL 2026): functional and security unit tests across 232 CWEs | Security tests can be generated and executed |
| Google Mantis (2026): sandboxed reproduction filters scanner findings | Dynamic grounding changes scanner results |

The premise is established. The missing piece is the measurement protocol and the released
artifact.

## 3. The gap

The reviewed literature does not contain a single released protocol that:

1. reports false passes and false rejections on the same executable tasks;
2. audits the static checkers used as oracles on vulnerable, fixed, and near-fixed code;
3. separates security correctness from behavioral correctness;
4. records per-task provenance and can be re-run from a clean checkout.

Absence in the reviewed corpus is evidence, not proof. The manuscript must state the claim that
way.

## 4. The goal

Build and release a two-sided, dynamic audit for security patches.

For a task `T` and a candidate patch `p`, the harness returns:

```text
(security_verdict, behavior_verdict, provenance)
```

For a checker `K`, the harness returns:

```text
(recall_on_vulnerable, precision_on_fixed, false_repair_rate, cost)
```

The same task record supports both.

## 5. Research questions

**RQ1. Patch correctness.** How often do patches that pass basic tests fail developer `PoC+` tests
or introduce a new CWE?

**RQ2. Checker quality.** How well do CodeQL, Semgrep, Bandit, and cppcheck distinguish the
vulnerable version, the fixed version, and security-regression mutants?

**RQ3. False rejection.** How often does a two-sided gate reject a valid developer fix?

**RQ4. Ranking impact.** Does the two-sided gate change the ordering of patch sources or models?

RQ1 and RQ2 are the core of Paper 1. RQ3 is the differentiator. RQ4 is a secondary analysis if the
data supports it.

## 6. Scope

### In scope

- 30 executable security tasks from PATCHEVAL, PVBench, BAC-Bench, and CWE-Bench-Java.
- Four checkers: Semgrep, Bandit, CodeQL, cppcheck.
- `PoC` and `PoC+` tests where available.
- Functional tests from the upstream project.
- Security-regression mutants generated from developer fixes.
- False-pass and false-rejection measurement.

### Out of scope for Paper 1

- A new repair model.
- A new static analyzer.
- Full firmware emulation.
- Container state and filesystem breakage (Paper 2).
- A general-purpose RAG system.
- Claims of soundness or zero false positives.

## 7. Success criteria

A successful Paper 1 has:

1. 30 tasks that reproduce from a clean checkout.
2. Four checkers with normalized SARIF results.
3. A security gate that accepts the developer fix and rejects known bad patches.
4. A measurement table with `SPR`, `SFR`, `FRR`, `CSR`, `CPR`, and `CFR`.
5. A released harness and task set.
6. A draft that a reviewer can understand without reading the implementation.

A negative result is acceptable if it is measured. If the checkers agree with the PoCs on every
task, the paper becomes a calibration study and the system claim is deferred.

## 8. One-slide statement

> **Problem.** Security patches are graded by exploit blocking; code patches are graded by
> repository tests. Both are one-sided. Static checkers are used as oracles without calibration.
>
> **Goal.** A two-sided, dynamic, checker-agnostic audit that reports security correctness and
> behavioral correctness for the same change, with false-pass and false-rejection rates and
> per-task provenance.
>
> **Paper 1.** 30 executable CVEs, four checkers, a released harness, and a measurement table.

## 9. 30-second pitch

> Security patches are usually tested with one exploit and a few unit tests. Recent benchmarks show
> that a large fraction of patches that pass those tests still fail the developer's own tests, and
> that static checkers are used as oracles without calibration. This project builds a two-sided
> audit: it checks whether the patch blocks the exploit and whether it preserves behavior, then
> audits the checkers on the same tasks. The first paper releases 30 executable CVEs and reports
> both false passes and false rejections.
