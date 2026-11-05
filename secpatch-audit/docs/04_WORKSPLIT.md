# 04. Work Split

## 1. Roles

| Role | Owns | Does not own |
| :--- | :--- | :--- |
| **Lead** | Paper framing, corpus selection, experimental design, analysis, writing, external communication | Daily implementation, container plumbing |
| **Engineer** | Harness, loader, runner, adapters, gate implementation, tests, CI | Paper claims, corpus inclusion decisions, novelty positioning |
| **Shared** | Code review, task validation, result interpretation, release checklist | None |

The split is by deliverable, not by file. Each work package has one owner and one reviewer.

## 2. Work packages

### WP0. Repository bootstrap

**Owner:** Engineer
**Depends on:** none
**Deliverable:** package skeleton, `pyproject.toml`, `Makefile`, CI stub, `tooling.lock.json`
**Acceptance:**

- `uv sync --all-extras` succeeds on a clean machine.
- `uv run pytest` runs and reports zero tests or the bootstrap tests.
- `uv run ruff check .` and `uv run mypy src` pass.
- `tooling.lock.json` records checker versions.

### WP1. Manifest schema and validator

**Owner:** Engineer
**Depends on:** WP0
**Deliverable:** `manifest.py`, `schema.json`, unit tests
**Acceptance:**

- A valid manifest round-trips through JSON.
- Missing fields, bad SHAs, and missing commands produce clear errors.
- The schema is documented in `docs/01_CORPUS.md`.
- Tests cover valid, invalid, and boundary cases.

### WP2. Task loader

**Owner:** Engineer
**Depends on:** WP1
**Deliverable:** `loader.py` with checkout, patch application, and commit verification
**Acceptance:**

- Clones or copies a repository at `base_commit`.
- Applies `gold.patch` and `test.patch` cleanly.
- Rejects a patch that does not apply.
- Records the resulting tree hash.
- Unit tests use a local fixture repository, not a network clone.

### WP3. Container runner

**Owner:** Engineer
**Depends on:** WP2
**Deliverable:** `runner.py` with build, run, timeout, and log capture
**Acceptance:**

- Runs a command in a pinned container.
- Captures stdout, stderr, exit code, and duration.
- Kills a hanging process at the timeout.
- Works offline.
- Unit tests cover success, failure, and timeout.

### WP4. Baseline validator

**Owner:** Engineer
**Depends on:** WP3
**Deliverable:** `baseline.py` producing the four-cell record
**Acceptance:**

- On one PATCHEVAL task: vulnerable fails PoC, fixed passes PoC, fixed passes tests.
- On a deliberately broken task: the validator reports which cell failed.
- The record is written to `expected.json`.

### WP5. SARIF normalizer

**Owner:** Engineer
**Depends on:** WP0
**Deliverable:** `sarif.py` with one normalized schema
**Acceptance:**

- Parses SARIF 2.1.0 from Semgrep and Bandit.
- Normalizes file, line, rule, CWE, severity, and message.
- Rejects malformed input with a clear error.
- Unit tests use checked-in SARIF fixtures, not live scanner runs.

### WP6. Semgrep and Bandit adapters

**Owner:** Engineer
**Depends on:** WP5
**Deliverable:** `checkers/semgrep.py`, `checkers/bandit.py`
**Acceptance:**

- Runs each checker on a small fixture and stores normalized results.
- Records the checker version and rule-set hash.
- A missing checker produces a skip record, not a crash.

### WP7. CodeQL and cppcheck adapters

**Owner:** Engineer
**Depends on:** WP6
**Deliverable:** `checkers/codeql.py`, `checkers/cppcheck.py`
**Acceptance:**

- CodeQL creates a database with an explicit build command.
- cppcheck runs without a full build.
- Both produce normalized results.
- A failed build produces a diagnostic, not a silent zero.

### WP8. Security gate

**Owner:** Engineer
**Depends on:** WP4, WP5
**Deliverable:** `security/gate.py`
**Acceptance:**

- Accepts the developer fix on the pilot task.
- Rejects a known bad patch with a reason.
- Rejects a patch that adds a new CWE.
- Records the two-sided verdict and the evidence.

### WP9. Corpus pilot

**Owner:** Lead, with Engineer support
**Depends on:** WP4
**Deliverable:** 10 validated tasks and a rejection log
**Acceptance:**

- All 10 reproduce from a clean checkout.
- Each has a manifest, Dockerfile, PoC, tests, and provenance.
- Excluded tasks are recorded with reasons.

### WP10. Checker audit

**Owner:** Lead
**Depends on:** WP6, WP7, WP9
**Deliverable:** checker table for 10 tasks
**Acceptance:**

- `CSR`, `CPR`, `CFR`, and cost per checker.
- Per-task findings, not only aggregates.
- At least one disagreement between a checker and the PoC is documented.

### WP11. Security-regression mutator

**Owner:** Engineer
**Depends on:** WP8
**Deliverable:** rule-based mutator and mutant runner
**Acceptance:**

- Generates at least five mutant families.
- Mutants build and pass functional tests.
- Invalid mutants are recorded and excluded.
- The mutator does not use an LLM.

### WP12. Measurement and paper tables

**Owner:** Lead
**Depends on:** WP10, WP11
**Deliverable:** `SPR`, `SFR`, `FRR`, `CSR`, `CPR`, `CFR` tables
**Acceptance:**

- Every metric has a denominator.
- Exclusions are reported.
- The numbers are reproducible from the released artifact.

### WP13. Scale to 30 tasks

**Owner:** Shared
**Depends on:** WP9, WP12
**Deliverable:** full 30-task corpus and run
**Acceptance:**

- At least 60% of selected tasks reproduce.
- The full run completes within the agreed budget.
- The report is generated from one command.

## 3. Six-week plan

| Week | Engineer | Lead | Shared checkpoint |
| ---: | :--- | :--- | :--- |
| 1 | WP0, WP1 | Select 10 pilot tasks; write corpus sheet | Manifest review |
| 2 | WP2, WP3 | Validate task licenses and PoCs | First task runs end to end |
| 3 | WP4, WP5 | Draft paper intro and related work | Baseline table for 3 tasks |
| 4 | WP6, WP7 | Checker selection and rule review | Four checkers produce SARIF |
| 5 | WP8, WP11 | Checker audit design; metrics | Gate accepts gold and rejects bad |
| 6 | WP10 support | Run pilot, write results | 10-task report and paper outline |

Weeks 7 to 12 add the 30-task scale, the full measurement, and the draft. The detailed table is in
`docs/07_PAPER_OUTLINE.md`.

## 4. First week for the engineer

The engineer can start without the lead and without an LLM key.

1. Create the package skeleton from `pyproject.toml`.
2. Implement the manifest schema from `docs/01_CORPUS.md`.
3. Add tests for valid and invalid manifests.
4. Implement a local fixture repository for the loader tests.
5. Write `tooling.lock.json` with the installed checker versions.
6. Open a pull request with the schema, tests, and a short design note.

The engineer should not start with CodeQL. Semgrep and Bandit are faster and expose schema problems
earlier.

## 5. First week for the lead

1. Choose the 10 pilot tasks.
2. For each task, record the repository, commits, license, CWE, PoC command, and test command.
3. Reject tasks that cannot be built or whose PoC is not deterministic.
4. Write the one-page problem statement.
5. Prepare the related-work table: PVBench, L-AVRBench, Beyond Bypass, AutoSUIT, PATCHEVAL,
   BAC-Bench, and the benchmark-design paper.
6. Do not write the results section before the pilot data exists.

## 6. Handoff protocol

Each handoff includes:

- the work package ID;
- the branch and commit;
- the command to reproduce;
- the expected output;
- the known limitations;
- the tests that were run;
- the tests that were not run.

A handoff without a reproduction command is not complete.

## 7. Definition of done

A work package is done when:

- the code is merged;
- the tests pass;
- the documentation is updated;
- the output is reproducible from a clean checkout;
- the reviewer has run the reproduction command.

## 8. What not to split

- The paper's central claim.
- The corpus inclusion decision.
- The metric definitions.
- The final result interpretation.

These stay with the lead. The engineer can challenge them, but the lead owns them.
