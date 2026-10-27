# Next Steps

**Purpose.** This document converts the literature review into an execution order. It defines
what to build first, what result counts as success or failure, and which claims are deferred until
the corresponding evidence exists.

**Governing principle.** The literature already contains the loop (Probe to Generate, SWE-ABS).
Replicating that loop is necessary but not sufficient. The contribution is the measurement the
literature does not report: the false-rejection rate on the gold patch, reported alongside the
false-pass rate, on public artifacts. Work should be ordered so that this number is produced as
early as possible.

---

## Phase 0 — Freeze the evaluation substrate

**Objective.** Establish a fixed, reproducible task set before any synthesis work begins.

Required artifacts:

1. A task list of 20 to 30 SWE-bench Verified instances, pinned by `instance_id`, with the base
   commit, gold patch, and test patch recorded for each.
2. A local checkout or container image per instance, at the recorded base commit.
3. A baseline run of the original suite on the gold patch, stored as a pass/fail record.

Current repository state: `data/curated_tasks.json` contains three task records and
`scripts/download_subset.py` can extend the list. There is no loader that applies a task's gold
patch and test patch to a working tree. That loader is the first engineering task.

**Acceptance criterion.** For all selected instances, the gold patch passes the original suite and
the base commit fails at least one test in the test patch. Any instance that violates this is
excluded and the exclusion is recorded.

**Do not proceed** to Phase 1 until the substrate is fixed. A moving task set invalidates every
downstream comparison.

---

## Phase 1 — Calibrate the attacker

**Objective.** Reproduce a surviving-mutant rate in the range reported by prior work on the same
benchmark.

Tasks:

1. Apply `scripts/patch_mutator.py` and `scripts/ast_mutator.py` to the gold patch, restricted to
   lines the patch adds.
2. For each mutant, apply it to the base checkout and run the original test suite.
3. Record killed, survived, and invalid (does not apply, does not compile, or times out).
4. Report the surviving-mutant rate with the same denominator used by prior work (instances with
   at least one survivor, not individual tests).

**Acceptance criterion.** A non-zero surviving-variant rate on the majority of instances, in the
same order of magnitude as P0120 and P0837. The exact value is less important than the direction:
if the rate is near zero, the mutation or execution pipeline is defective.

**Kill criterion.** If three debugging passes cannot produce a non-zero rate, stop and audit the
pipeline (patch application, import paths, test selection) before any synthesis work.

---

## Phase 2 — Produce the two-sided measurement

This is the contribution. It does not require an LLM.

**Objective.** For every surviving mutant, determine whether a proposed hardened test rejects the
mutant without rejecting the gold patch.

Tasks:

1. For each survivor, record the original suite result on the gold patch and on the mutant.
2. For each synthesized test, run four cells: gold patch, mutant, and the two corresponding
   unmutated controls.
3. Report:
   - `SMR`: surviving mutants divided by valid mutants.
   - `VHR`: survivors killed by the hardened suite, subject to the gold patch still passing.
   - `FRR`: valid gold-patch runs rejected by the hardened suite.
   - `FPFR`: public agent patches that passed originally and fail under the hardened suite.

The `FRR` column is the differentiator. Most prior work reports only false passes.

**Acceptance criterion.** A completed table for the pinned task set with all four metrics and
explicit denominators. A non-trivial `VHR` with a near-zero `FRR` is the target. A high `VHR` with
a high `FRR` is a failed gate, not a success.

---

## Phase 3 — Synthesize the defender

**Objective.** Close survivors with generated assertions rather than with hand-written tests.

Tasks:

1. Use `scripts/verifier_synthesizer.py` with the configured provider; retain the existing
   dual-execution gate in `scripts/verifier_gate.py`.
2. Feed the mutant diff and the failing execution trace to the prompt.
3. Reject any candidate that does not pass the gold patch and kill the mutant. Log rejected
   candidates with the failure reason.
4. Measure the retry budget and the rejection rate. These are evidence that the gate is doing
   work, not overhead.

**Acceptance criterion.** A measurable improvement in `VHR` over Phase 2's hand-written baseline,
with `FRR` unchanged or lower, and a recorded rejection log.

**Warning from the literature.** DCAware (P0191) shows that iterating until execution succeeds
produces weak oracles. The objective is mutant kill, not successful execution. A synthesizer that
converges quickly is not necessarily good.

---

## Phase 4 — Test one container case

**Objective.** Determine whether the two-layer claim is empirical.

Tasks:

1. Select one environment from the Terminal Wrench distribution (P0121).
2. Reproduce the exploit and confirm that the original verifier accepts it.
3. Apply the same gate to the task's state oracle: exit code, filesystem state, and stdout.
4. Record whether the procedure adapts without task-specific engineering.

**Acceptance criterion.** A documented result in either direction. A negative result is
publishable as a scope limitation and prevents an unsupported claim in the paper.

---

## Phase 5 — Release

**Objective.** Convert the measurements into the artifact the literature lacks.

Deliverables:

- the hardened suite with per-task provenance (task ID, mutant, generated test, gate result);
- the public-patch re-evaluation table (`FPFR` per model);
- a reproduction script that runs the audit without re-running agents;
- a short technical report with the four metrics and explicit denominators.

---

## Order of work

| Order | Work item | Blocking dependency |
| ---: | :--- | :--- |
| 1 | Task loader: apply gold patch and test patch, run baseline | None |
| 2 | Patch-level mutation and survivor recording | Task loader |
| 3 | Two-sided measurement on hand-written tests | Survivor recording |
| 4 | Defender synthesis against survivors | Two-sided measurement |
| 5 | Public-patch re-evaluation | Hardened suite |
| 6 | Container case | Survivor recording (independent of 3–5) |

Items 1 through 3 constitute the minimum publishable result. Item 4 is the system contribution.
Items 5 and 6 extend the claim.

---

## Decisions deferred until after the first measurements

The following questions should not be answered in prose before Phase 2 produces data:

- whether the two-layer protocol is feasible;
- whether the effect size is large enough to justify a paper;
- whether the security axis should be included;
- whether a new benchmark split is required.

The literature supports the premise and the components. It does not support claims about this
project's effect size. Those claims require the measurements above.
