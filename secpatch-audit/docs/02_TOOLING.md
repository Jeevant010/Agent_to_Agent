# 02. Tooling

## 1. Selection principle

Use mature tools for execution, parsing, and measurement. Build only the parts that carry the
research contribution.

The contribution is not a new scanner, a new repair model, or a new RAG pipeline. The contribution
is the protocol, the checker audit, and the released measurement.

## 2. Best-in-class stack for Paper 1

| Layer | Tool | Decision | Why |
| :--- | :--- | :--- | :--- |
| Language | Python 3.12 | Use | Best ecosystem for dataset and checker orchestration |
| Package manager | `uv` | Use | Fast, lockfile-based, reproducible |
| Container | Docker | Use | The task environments are already Docker-based |
| Test runner | `pytest` | Use | Standard; plugins for timeout and parallelism |
| Test plugins | `pytest-xdist`, `pytest-timeout` | Use | Parallel tasks and hanging-process protection |
| Patch parsing | `unidiff` | Use | Reliable unified-diff parsing |
| Git operations | `GitPython` | Use | Checkout, apply, diff, and commit metadata |
| Schema | `Pydantic` | Use | Typed manifests and result records |
| Data | `Polars` + `DuckDB` | Use | Fast tabular analysis; SQL for reports |
| CLI | `Typer` + `Rich` | Use | Small, typed CLI and readable output |
| Lint and types | `ruff` + `mypy` | Use | Fast feedback and strict interfaces |
| Checker: Semgrep | `semgrep` | Use | Fast, multi-language, easy to pin |
| Checker: Bandit | `bandit` | Use | Python baseline |
| Checker: CodeQL | `codeql` | Use | Deep C/C++ and Java analysis |
| Checker: cppcheck | `cppcheck` | Use | C/C++ without a full build |
| Result format | SARIF | Use | Standard for all four checkers |
| Fuzzing | `AFL++`, `libFuzzer`, `Atheris` | Optional | Needed only for breakage or PoC hardening |
| Property tests | `Hypothesis` | Optional | Useful for behavioral checks |
| Coverage | `coverage.py` | Optional | Diagnostic, not a headline metric |
| Mutation | `mutmut`, `cosmic-ray` | Optional | Paper 2; not needed for Paper 1 |
| Experiment tracking | MLflow | Optional | Useful after the first 30 tasks |
| LLM client | `litellm` + `instructor` | Optional | Not needed for Paper 1 |

## 3. Checkers in detail

### Semgrep

- **Use for:** all languages, custom CWE rules, fast iteration.
- **Why:** trivially installable, stable JSON output, easy to version.
- **Risk:** rule quality dominates results. A custom rule must be reviewed and pinned.
- **Run:** `semgrep --config <rules> --sarif --output result.sarif <path>`.

### Bandit

- **Use for:** Python tasks.
- **Why:** fast baseline with a well-known rule set.
- **Risk:** high false-positive rate on some patterns; not a complete security oracle.
- **Run:** `bandit -r <path> -f sarif -o result.sarif`.

### CodeQL

- **Use for:** Java and C/C++ tasks, deep dataflow.
- **Why:** strongest open query packs for those languages.
- **Risk:** needs a build database; Arduino and some embedded builds require explicit commands;
  query packs and CLI versions must be pinned.
- **Run:** `codeql database create ...` then `codeql database analyze ... --format=sarif-latest`.

### cppcheck

- **Use for:** C/C++ tasks, especially when a full CodeQL build is expensive.
- **Why:** no full build required; useful as an independent second opinion.
- **Risk:** limited interprocedural analysis; output needs normalization.
- **Run:** `cppcheck --xml --output-file=result.xml <path>` and convert to SARIF, or use the
  built-in SARIF output if the pinned version supports it.

## 4. What to build

| Component | Priority | Notes |
| :--- | :--- | :--- |
| Manifest schema | P0 | Pydantic model, validation, clear errors |
| Task loader | P0 | Checkout, apply patches, verify commits |
| Container runner | P0 | Build, run, timeout, capture stdout/stderr/exit code |
| Baseline validator | P0 | Four-cell check: vulnerable/fixed x PoC/tests |
| SARIF normalizer | P0 | One schema for all checkers |
| Security gate | P0 | Exploit blocked, tests pass, no new CWE |
| Checker audit runner | P1 | Vulnerable, fixed, and mutant triples |
| Security-regression mutator | P1 | Rule-based first, LLM later |
| Report generator | P1 | JSONL plus Markdown tables |
| Public-patch evaluator | P2 | Optional for Paper 1 |
| Breakage gate | Paper 2 | Do not start before Paper 1 is stable |
| RAG memory | Paper 2 | Not an oracle |

## 5. What not to build

- Another static analyzer.
- Another CodeQL wrapper presented as novelty.
- A RAG chatbot for vulnerability repair.
- An end-to-end "AI fixes vulnerabilities" product.
- A giant scraped dataset without PoCs.
- A custom SWE-bench harness.
- A Firecracker sandbox before Docker works.
- A new query language or rule engine.

## 6. Version pinning

Every run records:

- the checker name and version;
- the query pack or rule set and version;
- the Docker image digest;
- the base and fix commit SHAs;
- the Python version and lockfile hash;
- the task manifest hash.

A result without these fields is not reproducible. The report generator rejects incomplete records.

## 7. Installation

```bash
# Python environment
uv sync --all-extras

# Checkers (host-level; pin versions in CI)
pipx install semgrep
pipx install bandit
pipx install cppcheck

# CodeQL: download the pinned bundle, then
codeql pack download codeql/python-queries
codeql pack download codeql/java-queries
codeql pack download codeql/cpp-queries
```

The exact versions are recorded in `tooling.lock.json` in the first implementation milestone. The
file is committed; the bundles are not.

## 8. Why no LLM in Paper 1

The first paper measures patches and checkers. It does not need to generate patches. Developer
fixes, public patches, and rule-based security mutants are sufficient. An LLM is optional for
mutant generation and required for nothing in the core measurement.

Removing the LLM dependency makes the first paper cheaper, faster, and easier to reproduce.
