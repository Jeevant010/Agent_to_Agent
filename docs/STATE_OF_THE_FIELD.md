# State of the Field

**Purpose.** This document establishes whether autonomous adversarial verifier synthesis is an
open problem or an already-published result. It identifies the closest prior work, the point at
which each line of work stops, the documented failure modes, and the claims this project can
defend.

**Method.** All statements below refer to the 1,500-paper corpus described in
[`README.md`](README.md). Corpus IDs (for example, P0120) resolve to records in
`papers/metadata/papers_research_cards.jsonl`. Absence of a capability in this corpus is
evidence, not proof; the corpus should be refreshed before submission.

---

## 1. Summary

The components of the proposed system are published. The assembly is not.

- Mutating a reference patch to expose weak tests is published: Probe to Generate (P0120, 2026),
  SWE-ABS (P0837, 2026).
- LLM test generation against surviving mutants is published: UTBoost (P0001, 2025), MUTGEN
  (P0847, 2026), PRIMG (P1154, 2025).
- Reward hacking in terminal environments is published and measured: Terminal Wrench (P0121,
  2026), HVE (P0058, 2026), HVTB (P0071, 2026).

This review found no paper in the corpus that combines these into one model-agnostic loop which
reports both false passes and false rejections, releases a per-task hardened suite, and covers
both code and container state. That combination is the gap.

The defensible claim is: *the loop has been demonstrated in narrow settings; the unified,
released, two-sided protocol has not.* The claim that "no one has done this" is not supportable
and should not appear in the manuscript or in review responses.

---

## 2. Decomposition of the problem

The project comprises four components and one extension. Each has a different status in the
literature and should be assessed separately.

| # | Component | Function | Status |
| ---: | :--- | :--- | :--- |
| 1 | Attacker | Injects semantic bugs into the reference patch at AST level | Published and mature. Mutation testing dates to the 1970s; LLM-generated mutants to 2024. |
| 2 | Blind-spot detector | Runs the original benchmark suite on each mutant and records survivors | Published. Probe to Generate (P0120) and SWE-ABS (P0837) apply it to SWE-bench. |
| 3 | Defender | Synthesizes assertions that kill the survivors | Published. UTBoost (P0001), MUTGEN (P0847), PRIMG (P1154), DCAware (P0191). |
| 4 | Bidirectional gate | Retains a synthesized test only if the gold patch passes and the mutant fails | Implemented inside the systems above, but rarely reported as a soundness/completeness pair. |
| 5 | Container/state layer | Applies the same procedure to exit codes, filesystem state, and stdout | Measured (Terminal Wrench, HVE, HVTB), not defended. This is the least covered component. |

The contribution of this project is located at components 4 and 5, plus artifact release. It is
not located at components 1 through 3.

---

## 3. Closest prior work

### 3.1 Probe to Generate (P0120, 2026)

Closest to the full loop.

- **Method.** Generates semantically modified variants of the reference patch, retains the
  variants that pass the original tests, generates targeted tests, and keeps a test only if the
  gold patch passes, a surviving variant fails, and the test is robust to behavior-preserving
  transformations.
- **Results.** On SWE-bench Verified, 77% of instances admit at least one surviving variant;
  1,014 validated tests cover 211 instances; top-10 agents lose 4.2% to 9.0% resolved rate.
- **Limits.** Test augmentation only. No container or state layer, no released per-task hardened
  suite with provenance, and variant equivalence is handled by filters rather than solved.

### 3.2 SWE-ABS (P0837, 2026)

Strongest adversarial strengthening result.

- **Method.** A two-stage pipeline combines coverage-driven augmentation with mutation-driven
  synthesis of plausible but incorrect patches, then rejects patches that still pass.
- **Results.** Strengthens 50.2% of 500 Verified instances; rejects 19.71% of previously passing
  patches; lowers the top score from 78.80% to 62.20%; the previous leader falls to fifth.
- **Limits.** Synthetic wrong patches may not resemble real agent shortcuts; no environment
  layer; no reusable hardened suite is released.

### 3.3 UTBoost (P0001, 2025)

Strongest leaderboard re-evaluation result.

- **Method.** UTGenerator writes tests for real Python projects; UTBoost cross-validates gold and
  agent patches and re-grades public submissions.
- **Results.** Reclassifies 345 patches; corrections affect 40.9% of SWE-bench Lite and 24.4% of
  Verified leaderboard entries, with 18 and 11 ranking changes.
- **Limits.** Works only on tasks that at least one agent already solved; one LLM backend; no
  execution-state layer.

UTBoost and SWE-ABS share a first author. This is a small, fast-moving line rather than a crowded
field, and a follow-up should be expected.

### 3.4 Mutation-guided test synthesis (P0847, P1154, P1155, P0516)

The defender's toolbox, at function scale.

- **MUTGEN (P0847).** Feeds surviving mutants into the prompt; beats EvoSuite on mutation score
  across 204 subjects.
- **PRIMG (P1154).** Prioritizes mutants before generating tests, for Solidity.
- **Tratto (P1155).** Derives axiomatic oracles neuro-symbolically.
- **TOGA (P0516).** Infers exception and assertion oracles from method context.

All operate at function or unit level, not on repository patches or benchmark harnesses.

### 3.5 Terminal Wrench, HVE, and HVTB (P0121, P0058, P0071, 2026)

The environment layer.

- **Method and results.** Terminal Wrench releases 331 hackable environments, 3,632 exploit
  trajectories, and 2,352 legitimate baselines. Exploits range from output spoofing to stack-frame
  introspection, standard-library patching, and rootkit-style hijacking. Monitor AUC falls from
  0.97 to 0.92 without chain-of-thought. HVE and HVTB turn hack detection into a measurement
  protocol.
- **Limits.** Measurement only. No task-agnostic defense covering both code and state exists in
  the corpus.

### 3.6 LLM mutant generation and state-oracle calibration (P0240, P0906, 2026)

- **P0240.** Generates mutants that pass base tests using five LLMs: 87.7% (HumanEval) and 79.1%
  (MBPP) verified fault rate, against 4.4% and 5.7% for rule-based `mutmut`. This is the attacker
  side at function scale.
- **P0906.** Mutation-tests the evaluators of stateful agent benchmarks; official evaluators
  rejected 100 of 110 harmful mutations (90.9%). It validates that the state-oracle idea is
  measurable but does not synthesize fixes.

---

## 4. Timeline

| Year | Capability established | Representative work |
| ---: | :--- | :--- |
| 2014 | Mutation score validated as a fault proxy; coverage questioned | Just et al. (P0555); Inozemtseva and Holmes (P0554) |
| 2015–2021 | Oracle problem formalized; neural oracle generation | Barr et al. (P0553); TOGA (P0516) |
| 2022 | Generated tests used to select code | CodeT (P0546) |
| 2024 | Repository-level benchmark standard; reward hacking formalized | SWE-bench (P0434); Skalse et al. (P0011); InfoRM (P0005) |
| 2025 | Public patches re-graded; test generation against mutants; exploit datasets | UTBoost (P0001); PRIMG (P1154); Terminal Wrench (P0121) |
| 2026 | Adversarial strengthening at scale; variant probing; harness auditing | SWE-ABS (P0837); Probe to Generate (P0120); Complex Agents, Shallow Tests (P0841); HVE/HVTB (P0058/P0071) |

The interval between "weak tests are a problem" (2025) and "a loop that fixes them" (2026) was
approximately twelve months. A follow-up to the closest work should be expected.

---

## 5. Novelty assessment

### 5.1 Not novel

The following are published and should be attributed rather than presented as gaps:

- mutation of code to test a suite;
- LLM-based test generation;
- evidence that SWE-bench tests are insufficient;
- re-grading of public patches (UTBoost, SWE-ABS);
- measurement of terminal reward hacking (Terminal Wrench, HVE, HVTB);
- a soundness-plus-completeness gate as a concept (present in Probe to Generate and SWE-ABS).

### 5.2 Potentially novel

1. **One protocol, two denominators.** Reporting the false-pass rate and the false-rejection rate
   on the gold patch for the same tasks. Most papers report only the first. This is a measurement
   contribution and is inexpensive to add.
2. **A released, model-agnostic hardened suite with per-task provenance.** UTBoost and SWE-ABS
   demonstrate feasibility but do not leave a reusable artifact.
3. **One gate over AST mutants and container/state hacks.** The corpus contains no unified
   protocol across the two layers. This is the riskiest claim and requires Stage 2 data.
4. **Zero-cost leaderboard mining.** Re-evaluating public `.patch` files against the hardened
   suite rather than re-running agents. UTBoost performs the re-evaluation; a reusable, per-model
   FPFR report is a smaller but real increment.

### 5.3 Positioning

> Prior work shows that benchmark tests are weak and that individual components can be hardened.
> This project contributes a single released protocol that quantifies both directions of error,
> false passes and false rejections, across code and execution state, on public artifacts.

---

## 6. Documented failure modes

These results constrain the design of any hardening system.

| Failure mode | Evidence | Consequence for design |
| :--- | :--- | :--- |
| Self-repair trap: iterating until tests pass produces easy-to-satisfy oracles | DCAware (P0191) | Score the defender on mutant kill, not on pass rate. Log rejected candidates. |
| Coverage is not strength: 100% coverage can coexist with 4% mutation score | P0554; MUTGEN (P0847) | Never use coverage as the headline metric. Report mutation score and survival. |
| Equivalent mutants inflate the denominator | P0239; P0032 | Canonicalize, filter, and report the equivalence policy. |
| Contamination is a competing explanation | SWE-Bench Illusion (P0564) | Include a memorization probe and a non-benchmark repository set. |
| Hacks are task-specific; a harness patch that fixes one exploit does not generalize | Terminal Wrench (P0121) | Report per-task hacks, not a single "defense" claim. |
| Benchmarks drift as agents reach unanticipated tasks and environments | SWE-Bench Pro V2 (P0034) | Pin the benchmark version and re-grade in a clean container. |
| Test generation is not oracle generation; generated tests encode implemented behavior | P0192 | Gate on behavior, not on the code's current output. |
| A strict soundness gate creates false rejections | Project risk | Report the false-rejection rate. A suite that rejects valid code is not a success. |

---

## 7. Evidence strength

| Claim | Strength | Basis |
| :--- | :--- | :--- |
| Passing benchmark tests does not imply a correct patch | High | Three independent audits: P0120, P0001, P0837 |
| Hardening changes leaderboard rankings, not only scores | High | 18 and 11 rank changes (P0001); leader falls to fifth (P0837) |
| The attacker → survivor → defender loop has been published | High | P0120 closes it; P0837 and P0001 implement most of it |
| No mature, task-agnostic defense covers code and container hacks | Medium-high | Absence across clusters C3, C5, and C10; stated as open in the synthesis |
| A single two-sided protocol with a released suite is unpublished | Medium | Absence in this corpus; not proof of absence in the literature |
| The project can cover both layers in one protocol | Medium-low | Requires Stage 2 data that does not yet exist |

---

## 8. Experiments required to establish novelty

The literature review does not by itself establish a contribution. Three experiments do.

1. **Replicate the closest prior work.** Run the attacker on 20 to 30 SWE-bench Verified tasks
   and reproduce a surviving-variant rate in the published range. A rate near zero indicates a
   pipeline defect, not a gap in the literature.
2. **Produce the unreported number.** For every hardened test, record whether the gold patch
   still passes. Report the false-rejection rate alongside the false-pass rate. This is the
   clearest differentiator and requires no new model inference.
3. **Test one container case.** Take one Terminal Wrench-style exploit, apply the same gate, and
   determine whether the procedure transfers. One case is sufficient to judge whether the
   two-layer claim is empirical or aspirational.

If experiment 1 succeeds and experiment 2 yields a non-trivial result, the project has a
publishable measurement contribution. If experiment 3 also succeeds, it supports the larger
claim. If experiment 1 fails, pipeline debugging takes precedence over further writing.

A concrete execution order is in [`NEXT_STEPS.md`](NEXT_STEPS.md).

---

## 9. Scope

The corpus contains a large security cluster (C2), and that material can easily become the
organizing frame. It should not. A patch that passes functional tests but introduces a CWE is a
surviving mutant with a security label: one evaluation axis, one section of the paper, not the
thesis. The organizing frame is verifier soundness and completeness.
