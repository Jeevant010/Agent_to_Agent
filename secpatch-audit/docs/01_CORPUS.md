# 01. Corpus

## 1. Principle

The corpus is a set of executable vulnerable/fixed pairs, not a pile of vulnerable files.

A task is admitted only if it has:

1. a pinned vulnerable commit and a pinned fixed commit;
2. a reproducible build in a container;
3. a deterministic PoC that fails before the fix and passes after it;
4. a functional suite that passes on the fixed version;
5. a CWE label and a fix commit;
6. a license that permits research use;
7. an offline runtime within the budget;
8. no secrets or personal data.

A task that violates 2, 3, or 4 is excluded and recorded. A benchmark with 30 valid tasks is better
than one with 200 unverified tasks.

## 2. Four tiers

| Tier | Dataset | Scale | Role |
| :--- | :--- | :--- | :--- |
| A. Calibration | OWASP Benchmark Java | 2,740 cases: 1,415 vulnerable, 1,325 safe; 11 CWEs | Checker calibration |
| A. Calibration | Juliet C/C++ 1.3 | 64,099 cases; 118 CWEs | Checker calibration |
| A. Calibration | Juliet Java 1.3 | 28,881 cases; 112 CWEs | Checker calibration |
| B. Breadth | CVEfixes (initial release) | 5,365 CVEs; 5,495 fixes; 18,249 files; 50,322 functions; 180 CWEs | Real-world breadth |
| B. Breadth | CrossVul | 27,476 files; 13,738 pairs; 5,131 CVEs; 168 CWEs | Real-world breadth |
| B. Breadth | CWE-Bench-Java | 120 CVEs; 4 CWEs | Java checker audit |
| B. Breadth | L-AVRBench | 70 C/C++ functions with PoC and functional tests | Test-based AVR |
| C. Executable | PATCHEVAL | 1,000 CVEs; 65 CWEs; 230 Docker cases; Go, JavaScript, Python | Core Paper 1 |
| C. Executable | PVBench | 209 cases; 20 C/C++ projects; 12 CWEs | Core Paper 1 |
| C. Executable | BAC-Bench (repair) | 46 vulnerabilities; 6 web apps; Java, PHP, Go, Python | Core Paper 1 |
| C. Executable | AutoSUIT | 951 released samples; 232 CWEs; C, C++, Java, Python | Security unit tests |
| C. Executable | SusVibes | 186 tasks; 108 projects; 77 CWEs | Real Python security tasks |
| D. Breakage | SWE-bench Verified / Lite | 500 / 300 tasks | Paper 2 |
| D. Breakage | Terminal-Bench | Environment tasks | Paper 2 |

Tier A is for calibration, not for headline claims. Tier B is for breadth and retrieval. Tier C is
the core of Paper 1. Tier D belongs to Paper 2.

## 3. The 30-task slate

| Source | Count | Language | Selection rule |
| :--- | ---: | :--- | :--- |
| PATCHEVAL Verified | 10 | Python, Go, JavaScript | One Docker case per CWE family, balanced by language |
| PVBench | 10 | C/C++ | Mix of memory-safety and control-flow CWEs |
| BAC-Bench | 5 | Java, PHP, Go, Python | Logic vulnerabilities with runtime |
| CWE-Bench-Java | 5 | Java | CodeQL and Semgrep both runnable |

The first 10 tasks are a pilot. They are chosen for build reliability, not for effect size. The
pilot is complete when all 10 reproduce.

The slate expands to 60 after the pilot:

- 10 more PATCHEVAL cases in the least represented language;
- 10 more PVBench cases in the least represented CWE;
- 10 CWE-Bench-Java cases for checker comparison;
- 10 AutoSUIT or SusVibes cases for Python security tests.

## 4. Task manifest

```json
{
  "task_id": "patcheval-cve-2021-23376",
  "repo_url": "https://github.com/example/project",
  "base_commit": "<40-char sha>",
  "fix_commit": "<40-char sha>",
  "language": "python",
  "cwe": "CWE-78",
  "license": "Apache-2.0",
  "image": "ghcr.io/example/project:tag",
  "build": {
    "command": "pip install -e .",
    "timeout_sec": 600
  },
  "poc": {
    "command": "bash poc/run.sh",
    "vulnerable_exit": 0,
    "fixed_exit": 1
  },
  "tests": {
    "command": "pytest -q",
    "fixed_exit": 0
  },
  "poc_plus": {
    "command": "bash poc_plus/run.sh",
    "fixed_exit": 0
  },
  "provenance": {
    "source": "https://...",
    "retrieved": "2026-11-02",
    "sha256": "..."
  }
}
```

The exact field names are fixed in the first implementation milestone. The important property is
that every command, version, and expected result is recorded.

## 5. Task directory

```text
<task_id>/
├── manifest.json
├── Dockerfile
├── gold.patch
├── test.patch
├── poc/
├── poc_plus/
├── tests/
├── expected.json
├── provenance.json
└── README.md
```

`expected.json` records the four baseline cells:

| Cell | Expected |
| :--- | :--- |
| vulnerable + PoC | exploit works |
| fixed + PoC | exploit blocked |
| vulnerable + functional tests | may fail or pass; recorded |
| fixed + functional tests | pass |

## 6. Baseline validation

For every task, the loader must produce:

```text
vulnerable: PoC = FAIL   (the exploit succeeds)
fixed:      PoC = PASS   (the exploit is blocked)
fixed:      tests = PASS
```

If the vulnerable PoC cannot be made to fail, the task is invalid. If the fixed PoC fails, the
task is invalid. If the fixed functional suite fails, the task is invalid until the environment is
fixed.

The four cells are stored in `expected.json` and re-checked on every run.

## 7. Security-regression mutants

A security-regression mutant is a patch derived from the developer fix that:

- still passes the functional suite;
- either leaves the exploit path open, or introduces a new CWE.

The mutant is the attacker for the security verifier. It is not a random mutation. It is a
plausible incomplete fix.

Examples:

- the fix checks the input in one caller but not another;
- the fix validates a length but not the sign;
- the fix escapes one metacharacter but not its variant;
- the fix moves the check after the dangerous operation;
- the fix adds a guard that can be bypassed by an alternate encoding.

Mutants are generated by rules plus, later, an LLM. Every mutant is executed. A mutant that does
not build or does not pass the functional suite is invalid and is recorded as such.

## 8. Music Kit and embedded scope

`JacknCrack18/Music-Kit-Test` is not part of the corpus. It is a 1,863-line ESP32 firmware project
with no network, authentication, untrusted parsing, dynamic allocation, tests, or PoC. It is useful
as a build smoke test and as an example of a small attack surface. It is not a vulnerability
corpus.

An embedded pack is a separate effort:

- ESP-IDF or Arduino library CVEs with public PoCs;
- PlatformIO with `compile_commands.json`;
- CodeQL with an explicit build command, plus cppcheck and clang-tidy;
- verification that the checker models the relevant APIs;
- no claim of coverage without evidence.

## 9. Corpus risks

| Risk | Mitigation |
| :--- | :--- |
| License restrictions | Prefer Apache-2.0, MIT, CC0, CC BY; record per task |
| Flaky PoCs | Pin commits and images; fix seeds; quarantine |
| Large images | Cache layers; start with 30 tasks; parallelize |
| Contamination | Prefer post-cutoff CVEs; record dates; hold out a clean subset |
| Upstream breakage | Mirror repositories or pin commit archives |
| Missing `PoC+` | Record the missing cell; do not impute success |
