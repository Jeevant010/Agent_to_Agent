# 05. Explainer

This document is for explaining the project to a collaborator, a reviewer, or a new engineer. It
has four versions: 30 seconds, 5 minutes, 15 minutes, and a FAQ.

## 1. The 30-second version

> Security patches are usually tested with one exploit and a few unit tests. Recent benchmarks show
> that many patches that pass those tests still fail the developer's own tests, and that static
> checkers are used as oracles without calibration. This project builds a two-sided audit: it
> checks whether the patch blocks the exploit and whether it preserves behavior, then audits the
> checkers on the same tasks. The first paper releases 30 executable CVEs and reports both false
> passes and false rejections.

## 2. The 5-minute version

### 2.1 The problem

A security patch is normally accepted if the original exploit stops working. That is a single
question. It does not tell us whether:

- the fix is complete;
- the developer's own `PoC+` tests pass;
- a new weakness was introduced;
- the behavior of the program changed.

The same problem exists on the checker side. A static checker is often used as an oracle, but the
checker is not calibrated on the vulnerable version, the fixed version, and a near-fixed version.

### 2.2 The evidence

- PVBench: over 40% of AVR patches that pass basic tests fail developer `PoC+` tests.
- Beyond Bypass: LLM patches can introduce new weaknesses while removing the target.
- LLM-generated regression tests: 8% to 17% enforce faults.
- L-AVRBench: match-based metrics do not capture functional and security correctness.

The premise is not in dispute. The missing measurement is a two-sided, checker-agnostic audit on
executable tasks.

### 2.3 The approach

One task record, two modes:

- **Artifact mode:** evaluate a candidate patch.
- **Checker mode:** evaluate a checker used as an oracle.

Two gates:

- **Security gate:** exploit blocked, `PoC+` passes, no new CWE.
- **Behavior gate:** functional tests pass, contracts hold.

Two-sided metrics:

- false pass (`SFR`);
- false rejection (`FRR`);
- checker recall and precision (`CSR`, `CPR`);
- checker false-repair rate (`CFR`).

### 2.4 The deliverable

- 30 executable security tasks.
- Four checkers.
- A released harness.
- A measurement table.
- A paper that reports both directions of error.

## 3. The 15-minute version

### 3.1 Task record

```text
T = (repo, base_commit, fix_commit, build, poc, poc_plus, tests, cwe, license, image)
```

The record is the contract. It says exactly how to reproduce the vulnerable and fixed states.

### 3.2 Baseline

Before any measurement, the task must satisfy:

```text
vulnerable + PoC  = FAIL   (the exploit works)
fixed + PoC       = PASS   (the exploit is blocked)
fixed + tests     = PASS
```

If these do not hold, the task is excluded. The exclusion is recorded.

### 3.3 Gate

A candidate patch is accepted only if:

1. the PoC passes;
2. the functional tests pass;
3. `PoC+` passes, when present;
4. the checker reports no new CWE.

The gate is not a proof. It is a measurement device. It can miss. The paper reports the miss rate
and the false-rejection rate.

### 3.4 Checker audit

Each checker is run on:

- the vulnerable version;
- the fixed version;
- security-regression mutants;
- benign refactors.

The comparison produces recall, precision, and false-repair rate. This is the "audit the auditor"
layer.

### 3.5 Corpus

- Calibration: OWASP Benchmark, Juliet.
- Breadth: CVEfixes, CrossVul, CWE-Bench-Java, L-AVRBench.
- Executable: PATCHEVAL, PVBench, BAC-Bench, AutoSUIT, SusVibes.
- Breakage: SWE-bench, Terminal-Bench (Paper 2).

Paper 1 uses 30 tasks from the executable tier.

### 3.6 Why 30 tasks

Thirty is large enough to see a pattern and small enough to debug every task. A benchmark with 30
reproducible tasks is stronger than one with 200 unverified tasks. The slate expands to 60 after
the pilot.

### 3.7 What is new

- Two-sided measurement on the same tasks.
- Checker audit, not only patch audit.
- Security and behavior in one protocol.
- A released, executable artifact.
- False rejection reported alongside false pass.

### 3.8 What is not new

- Mutation testing.
- LLM test generation.
- Static analysis.
- RAG for repair.
- The observation that some patches are incomplete.

The paper must attribute these clearly.

## 4. FAQ

### "Why not just run CodeQL?"

CodeQL is a scanner. It produces alerts, not a verdict on a patch. It also has false positives and
false negatives. The project audits CodeQL instead of assuming it is the oracle.

### "Why not use one large vulnerable repository?"

A large repository without pinned commits, PoCs, tests, and labels is not a benchmark. It produces
alerts, not measurements. The corpus is built from executable pairs.

### "Why 30 tasks instead of 1,000?"

Thirty is enough to measure and small enough to debug. The first paper is a measurement paper, not
a leaderboard. Scale follows reproducibility.

### "Why both security and breakage?"

They are the two ways a patch can be wrong: it can fail to fix the vulnerability, or it can break
the program. One protocol, two gates.

### "What if the checkers agree with the PoCs on every task?"

Then the paper becomes a calibration study: the checkers are better than expected on this set. That
is still a result. The system claim is deferred.

### "What if the gate rejects many valid fixes?"

That is the false-rejection result. It is reported, not hidden. A gate with high false rejection is
a failed gate, not a success.

### "Is this an AI paper or a security paper?"

It is a software engineering and security measurement paper. It uses AI-generated patches as one
patch source, but the contribution is the protocol and the measurement.

### "Why not use an LLM to generate the patches?"

Paper 1 does not need to. Developer fixes, public patches, and rule-based mutants are sufficient.
An LLM is optional and adds cost and variance.

### "What is the artifact?"

The task set, manifests, Dockerfiles, PoCs, tests, checker adapters, gate, and report generator.

### "How is this different from PVBench?"

PVBench shows that basic tests overestimate patch success. This project adds the checker audit, the
false-rejection measurement, and a released two-sided harness. It uses PVBench-style tasks, not
only PVBench's result.

## 5. Explaining to different audiences

### To a security researcher

Lead with the measurement gap: patches and checkers are evaluated one-sided. Emphasize `SFR`,
`FRR`, and the checker audit. Do not lead with LLMs. LLMs are one patch source.

### To an ML researcher

Lead with the evaluation problem: outcome-based verifiers are weak, and generated tests can encode
faults. Emphasize the two-sided matrix and the released benchmark. Do not claim a new model.

### To an engineer

Lead with the practical question: "Does this patch actually fix the bug without breaking the
build?" Show the gate and the one-command run. Keep the paper framing out of the first five
minutes.

### To a reviewer

Lead with the closest prior work and the exact increment. Say what is already published before
saying what is new. A reviewer who hears "first" will look for a counterexample.

## 6. Slide outline

1. **Title.** Two-sided verification of security patches.
2. **Problem.** One-sided evaluation of patches and checkers.
3. **Evidence.** PVBench, Beyond Bypass, LLM-generated tests.
4. **Protocol.** Task record, artifact mode, checker mode.
5. **Gates.** Security and behavior, two-sided matrix.
6. **Corpus.** Four tiers, 30 tasks, four checkers.
7. **Metrics.** `SFR`, `FRR`, `CSR`, `CPR`, `CFR`.
8. **Results.** The table, including negative results.
9. **Threats.** Equivalence, contamination, flakiness, scope.
10. **Release.** Harness, tasks, reproduction command.

## 7. What not to say

- "We are the first to show that LLM patches are incomplete."
- "We solve vulnerability repair."
- "Our gate is sound."
- "CodeQL is the oracle."
- "The benchmark is the largest."
- "Zero false positives and zero false negatives."
- "RAG is the key contribution."

These claims are either false, crowded, or unsupported by the planned evidence.
