# 07. Paper Outline

## 1. Title options

1. *Do Security Patches Actually Fix Vulnerabilities? A Two-Sided Dynamic Audit of AVR and Static
   Checkers*
2. *Auditing the Auditors: Two-Sided Verification of Security Patches*
3. *Beyond the Exploit: Measuring Security and Behavioral Correctness of Security Patches*

Option 1 is descriptive and safe. Option 2 is memorable but may overclaim. Option 3 is broad but
clear.

## 2. Abstract skeleton

1. Security patches are graded by exploit blocking; code patches are graded by tests.
2. Recent work shows that basic tests overestimate patch success and that generated tests can
   encode faults.
3. This paper presents a two-sided, checker-agnostic audit on 30 executable security tasks.
4. The audit reports false passes, false rejections, and checker quality on the same tasks.
5. The harness and task set are released.

The abstract must include the actual numbers. Do not write the numbers before the pilot.

## 3. Section structure

### 1. Introduction

- The one-sided evaluation problem.
- The evidence from PVBench, Beyond Bypass, and generated-test studies.
- The gap: no released two-sided, checker-agnostic audit.
- Contributions:
  1. A task protocol with artifact and checker modes.
  2. A two-sided security gate with false-pass and false-rejection measurement.
  3. An audit of four static checkers on vulnerable, fixed, and near-fixed code.
  4. A released 30-task executable artifact.

### 2. Background and related work

- Automated vulnerability repair.
- Patch validation and `PoC+`.
- Static analysis and checker benchmarks.
- Security regression.
- Generated tests and behavioral verification.
- Benchmark design.

The related-work table should include: PVBench, L-AVRBench, PATCHEVAL, Beyond Bypass, AutoSUIT,
BAC-Bench, SusVibes, CWE-Bench-Java, and the benchmark-design paper.

### 3. Problem formulation

- Task tuple.
- Reference fix and candidate patch.
- Security verdict.
- Behavior verdict.
- Checker verdict.
- The two-sided matrix.

### 4. Protocol

- Artifact mode.
- Checker mode.
- Baseline validation.
- Security gate.
- Security-regression mutants.
- Provenance.

### 5. Corpus

- Tier A: calibration.
- Tier B: breadth.
- Tier C: executable.
- The 30-task slate.
- Selection criteria and exclusions.
- License and contamination controls.

### 6. Experimental setup

- Checkers and versions.
- Rule sets and query packs.
- Container images.
- Runtime budget.
- Metrics and denominators.
- Statistical treatment.

### 7. Results

#### RQ1. Patch correctness

- `SPR`: patches that block the PoC.
- `SFR`: patches that block the PoC but fail `PoC+` or add a CWE.
- Per-CWE and per-language breakdown.

#### RQ2. Checker quality

- `CSR`: recall on vulnerable versions.
- `CPR`: precision on fixed versions.
- `CFR`: patches that pass the checker but fail the PoC.
- Cost per task.

#### RQ3. False rejection

- `FRR`: valid developer fixes rejected by the gate.
- Per-task failure reasons.
- Gate tuning and sensitivity.

#### RQ4. Ranking impact (optional)

- Does the two-sided gate change the ordering of patch sources?
- Only report if the data supports it.

### 8. Discussion

- What the two-sided matrix reveals.
- Why checker calibration matters.
- When the gate is too strict.
- What the results do not imply.

### 9. Threats to validity

- Construct validity: PoC and `PoC+` may not capture all security semantics.
- Internal validity: flaky tests, environment drift, checker versions.
- External validity: 30 tasks, four checkers, limited languages.
- Conclusion validity: small denominators, multiple comparisons.
- Contamination: training data may include the CVEs.

### 10. Conclusion

- Restate the measurement, not the aspiration.
- Release the artifact.
- State the open problems for Paper 2.

## 4. Tables and figures

| Item | Content |
| :--- | :--- |
| Table 1 | Closest prior work and the increment |
| Table 2 | Corpus composition and exclusions |
| Table 3 | Baseline validation results |
| Table 4 | Patch correctness: `SPR`, `SFR` |
| Table 5 | Checker quality: `CSR`, `CPR`, `CFR`, cost |
| Table 6 | False rejection: `FRR` and reasons |
| Figure 1 | Two-sided matrix |
| Figure 2 | Protocol diagram: task, gate, checker |
| Figure 3 | Per-task heatmap of security and behavior verdicts |
| Figure 4 | Checker disagreement examples |

## 5. Claims-evidence map

| Claim | Evidence | Status |
| :--- | :--- | :--- |
| Basic tests overestimate patch success | `SFR` table | Pending pilot |
| Checkers disagree with PoCs | `CFR` table | Pending pilot |
| The gate rejects valid fixes at a measurable rate | `FRR` table | Pending pilot |
| The protocol is reproducible | Clean-checkout run | Pending WP13 |
| The artifact is reusable | Released manifests and images | Pending release |

No claim enters the abstract until its evidence row is complete.

## 6. Writing order

1. Problem statement and contributions.
2. Related work and closest prior work.
3. Problem formulation and protocol.
4. Corpus and experimental setup.
5. Results tables after the pilot.
6. Discussion and threats.
7. Abstract after the results.

Writing the abstract first is a common failure mode. The numbers drive the abstract.

## 7. Artifact checklist

- `README.md` with one-command reproduction.
- `pyproject.toml` and lockfile.
- `tooling.lock.json` with checker versions.
- 30 task manifests.
- Dockerfiles or image digests.
- PoCs and tests.
- Gate implementation.
- Report generator.
- Raw JSONL results.
- Exclusion log.
- License and provenance records.

## 8. Submission checklist

- All claims have a table or figure.
- All numbers have denominators.
- Closest prior work is cited and distinguished.
- Negative results are reported.
- Threats to validity are explicit.
- The artifact runs from a clean checkout.
- The paper does not claim soundness or zero errors.
- The security pack is described as a subsystem, not the whole thesis.
