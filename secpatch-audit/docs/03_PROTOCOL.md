# 03. Protocol

## 1. Task tuple

```text
T = (repo, base_commit, fix_commit, build, poc, poc_plus, tests, cwe, license, image)
```

- `repo`: repository URL.
- `base_commit`: the vulnerable revision.
- `fix_commit`: the developer fix, or the commit that contains it.
- `build`: command and timeout.
- `poc`: exploit command and expected exit codes.
- `poc_plus`: developer tests added with the fix, when available.
- `tests`: functional suite.
- `cwe`: normalized CWE label.
- `license`: license identifier.
- `image`: pinned container image or Dockerfile.

The reference fix is `p*`. A candidate patch is `p`.

## 2. Artifact mode

```text
verdict(T, p) = (security, behavior, provenance)
```

Procedure:

1. Check out `base_commit`.
2. Apply `p`.
3. Build.
4. Run `poc`.
5. Run `poc_plus`, if present.
6. Run `tests`.
7. Run the checker.
8. Record the result and provenance.

The result is not a single pass/fail. It is a pair of verdicts plus the evidence.

## 3. Checker mode

```text
audit(T, K) = (recall_vulnerable, precision_fixed, false_repair_rate, cost)
```

Procedure:

1. Run checker `K` on `base_commit`.
2. Run `K` on `base_commit + p*`.
3. Run `K` on security-regression mutants.
4. Run `K` on benign refactors of the fixed version.
5. Compare findings with the ground truth.

Checker mode is the "audit the auditor" layer. It is the main cross-workstream asset.

## 4. Security gate

### Baseline

| Cell | Requirement |
| :--- | :--- |
| `base_commit` + PoC | PoC fails (the exploit works) |
| `base_commit + p*` + PoC | PoC passes (the exploit is blocked) |
| `base_commit + p*` + tests | tests pass |
| `base_commit + p*` + checker | no new CWE |

### Candidate

A candidate `p` is accepted only if:

1. `P0`: the PoC passes on `base_commit + p`.
2. `P1`: the functional suite passes.
3. `P2`: the checker reports no new CWE.
4. `P3`: `poc_plus` passes, when present.

If `p*` fails `P0` through `P3`, the task is mis-specified or the gate is too strict. Both are
recorded. The gate is not allowed to silently drop the task.

## 5. Two-sided matrix

| | Behavior passes | Behavior fails |
| :--- | :--- | :--- |
| **Security passes** | Acceptable | Dangerous: security-only fix |
| **Security fails** | Security theater | Obvious reject |

The matrix is the main presentation device. Every patch is placed in exactly one cell.

## 6. Metrics

| Metric | Definition | Purpose |
| :--- | :--- | :--- |
| `SPR` | Candidate patches that block the PoC / candidates | Basic success rate |
| `SFR` | Candidates that block the PoC but fail `PoC+` or add a CWE / candidates | Hidden failure rate |
| `FRR` | Valid developer fixes rejected by the gate / valid fixes | False rejection |
| `CSR` | Vulnerable cases flagged by checker `K` / vulnerable cases | Checker recall |
| `CPR` | Fixed cases not flagged by checker `K` / fixed cases | Checker precision |
| `CFR` | Patches that pass `K` but fail the PoC / patches | Checker false-repair rate |
| `CR` | Checker runtime and cost per task | Practicality |

Every metric is reported with:

- numerator and denominator;
- number of excluded tasks and the exclusion reasons;
- confidence interval, where meaningful;
- per-checker and aggregate values.

No metric is reported as a single number without a denominator.

## 7. Result record

```json
{
  "task_id": "patcheval-cve-2021-23376",
  "mode": "artifact",
  "patch_source": "developer",
  "patch_hash": "sha256:...",
  "security": {
    "poc": "pass",
    "poc_plus": "pass",
    "new_cwe": "none",
    "verdict": "pass"
  },
  "behavior": {
    "tests": "pass",
    "verdict": "pass"
  },
  "checker": {
    "name": "semgrep",
    "version": "x.y.z",
    "ruleset_hash": "sha256:...",
    "findings": 0
  },
  "provenance": {
    "base_commit": "...",
    "fix_commit": "...",
    "image_digest": "sha256:...",
    "run_id": "..."
  }
}
```

The schema is versioned. A schema change requires a migration note and a re-run of the affected
tasks.

## 8. Reproducibility rules

1. Every task runs in a container.
2. The container image is pinned by digest.
3. The repository is pinned by commit.
4. The checker and rule set are pinned by version or hash.
5. The evaluation runs offline.
6. Timeouts are explicit.
7. Flaky tasks are quarantined, not averaged.
8. The report includes the command lines and exit codes.
9. A clean checkout can reproduce the table with one command.
10. Excluded tasks and their reasons are part of the artifact.

## 9. Security-regression mutant protocol

A mutant is valid only if:

1. it applies to `base_commit`;
2. it builds;
3. it passes the functional suite;
4. it fails the PoC or introduces a new CWE.

A mutant that does not build or breaks functional tests is invalid. Invalid mutants are recorded
but excluded from the denominator.

The mutator is not allowed to generate random syntax changes. It targets plausible incomplete
fixes:

- partial validation;
- wrong comparison boundary;
- alternate encoding path;
- check in the wrong caller;
- check after the dangerous operation;
- guard that can be bypassed.

## 10. What the protocol does not claim

- It does not prove a patch is secure.
- It does not prove a checker is complete.
- It does not eliminate false positives or false negatives.
- It does not generalize to every language or every CWE.

It measures both directions of error on a pinned, executable task set. That is the claim.
