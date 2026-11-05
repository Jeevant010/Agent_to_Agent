# Corpus Manifests

Each subdirectory is one task. The manifest is the contract between the corpus and the runner.

A task directory contains:

```text
<task_id>/
├── manifest.json
├── Dockerfile
├── gold.patch
├── test.patch
├── poc/
├── tests/
├── expected.json
├── provenance.json
└── README.md
```

The manifest schema is defined in `docs/01_CORPUS.md` and implemented in
`src/secpatch_audit/manifest.py` in the first implementation milestone.

No task is committed until it satisfies the baseline:

- vulnerable version fails the PoC;
- fixed version passes the PoC;
- fixed version passes the functional suite;
- the task runs offline within the time budget.

Tasks that fail the baseline are recorded in `corpus/rejected/` with the reason. They are evidence,
not failures to hide.
