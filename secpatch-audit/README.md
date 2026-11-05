# SecPatch Audit

Two-sided verification of security patches.

**Status:** Paper 1 workspace. Pre-implementation. This directory is staged as the root of a
separate repository; it is not yet initialized as one.

---

## What this is

SecPatch Audit is a measurement harness for security patches. It answers two questions for the
same change:

1. **Security:** does the patch block the exploit, pass the developer's `PoC+` tests, and avoid
   introducing a new weakness?
2. **Verification quality:** do the static checkers used as oracles actually distinguish the
   vulnerable version, the fixed version, and a patch that only looks fixed?

The harness has two modes:

- **Artifact mode:** evaluate a candidate patch.
- **Checker mode:** evaluate a static checker or test suite used as an oracle.

The same task record supports both. This is the core design idea.

---

## What this is not

- Not another automated vulnerability repair model.
- Not another static analyzer.
- Not a wrapper around CodeQL.
- Not a giant scraped dataset without PoCs and tests.
- Not a claim that a dynamic gate is sound.

---

## Paper 1 in one paragraph

Recent work shows that security patches can pass basic tests and still leave the vulnerability
open, and that LLM-generated tests can encode faults. The missing measurement is a two-sided,
checker-agnostic audit on executable tasks. Paper 1 contributes a released harness, 30 executable
security tasks, and a table of false-pass and false-rejection rates for patches and for the static
checkers used as oracles.

---

## The 30-task slate

| Source | Count | Language | Why |
| :--- | ---: | :--- | :--- |
| PATCHEVAL Verified | 10 | Python, Go, JavaScript | Dockerized PoC plus unit tests |
| PVBench | 10 | C/C++ | Basic tests plus developer `PoC+` tests |
| BAC-Bench | 5 | Java, PHP, Go, Python | Logic vulnerabilities with runtime |
| CWE-Bench-Java | 5 | Java | Real Java CVEs for CodeQL and Semgrep |

The slate expands to 60 tasks after the first 30 are reproducible.

---

## Repository layout

```text
secpatch-audit/
├── README.md
├── docs/
│   ├── 00_GOAL.md
│   ├── 01_CORPUS.md
│   ├── 02_TOOLING.md
│   ├── 03_PROTOCOL.md
│   ├── 04_WORKSPLIT.md
│   ├── 05_EXPLAINER.md
│   ├── 06_NOVELTY.md
│   └── 07_PAPER_OUTLINE.md
├── corpus/
│   └── manifests/
├── src/
│   └── secpatch_audit/
├── tests/
├── pyproject.toml
├── Makefile
└── .gitignore
```

---

## Read order

1. `docs/00_GOAL.md`: the problem, the research questions, and the scope.
2. `docs/01_CORPUS.md`: the four-tier corpus and the 30-task slate.
3. `docs/02_TOOLING.md`: the best-in-class stack and the build-versus-use decisions.
4. `docs/03_PROTOCOL.md`: the task tuple, the gates, and the metrics.
5. `docs/04_WORKSPLIT.md`: the lead and engineer split, with acceptance criteria.
6. `docs/05_EXPLAINER.md`: how to explain the project to a collaborator or reviewer.
7. `docs/06_NOVELTY.md`: what is crowded, what is open, and what not to claim.
8. `docs/07_PAPER_OUTLINE.md`: the Paper 1 section structure.

---

## Quick start

The implementation has not started. Once the package exists:

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run mypy src
```

The first milestone is not a full run. It is one PATCHEVAL task that reproduces:

- vulnerable version fails the PoC;
- fixed version passes the PoC;
- fixed version passes the functional suite.

---

## Definition of done for Paper 1

- 30 tasks reproduce from a clean checkout.
- Four checkers produce normalized results: Semgrep, Bandit, CodeQL, cppcheck.
- The security gate accepts the developer fix and rejects known bad patches.
- The measurement table reports `SPR`, `SFR`, `FRR`, `CSR`, `CPR`, and `CFR` with denominators.
- The harness runs from one command.
- The paper draft and the artifact are ready for review.
