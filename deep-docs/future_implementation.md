# Future Implementations & Architectural Roadmap

This document tracks planned architectural enhancements, scalability optimizations, and engine upgrades for the Autonomous Adversarial Verifier Synthesis (AAVS) framework.

---

## 1. Parallel Mutant Evaluation & Process Pooling

### Current State
[`scripts/run_local_audit.py`](file:///c:/Users/aadit/Desktop/Agent_to_Agent/scripts/run_local_audit.py) generates 8 mutants and tests them sequentially in isolated temporary subprocesses. On a local laptop, evaluating 8 lightweight mutants on a single isolated function takes 1 to 2 seconds total.

### Scalability Bottleneck
When scaling from single functions to full-scale benchmarks (such as 100+ tasks from `SWE-bench Verified` or `DeepSWE`), running tests sequentially becomes a major bottleneck:
$$\text{Total Latency} = \sum_{i=1}^{M} T_{\text{test}}(m_i)$$
In large repositories like `astropy`, `sympy`, or `django`, a single `pytest` invocation may take 15 to 45 seconds. Evaluating 20 mutants sequentially on one task would take 10 to 15 minutes per task, and over 20 hours for a 100-task benchmark run.

### Target Architecture
- **ProcessPoolExecutor:** Migrate sequential test loops to Python's `concurrent.futures.ProcessPoolExecutor`, distributing test execution across all available physical CPU cores:
  ```python
  from concurrent.futures import ProcessPoolExecutor

  with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
      futures = [executor.submit(execute_test, m["mutated_code"], test_suite) for m in mutants]
  ```
- **Shared-Nothing Worker Isolation:** Each worker process operates in its own unique temporary filesystem directory (`tempfile.TemporaryDirectory()`) to prevent state collision or race conditions during module imports.
- **Early Termination:** If evaluating a test suite against a mutant, terminate the worker immediately on the first assertion failure rather than running the full test suite.

---

## 2. Algorithmic Boundary Value Analysis (BVA) Pre-Filter

### Objective
Reduce token consumption and inference latency by resolving simple scalar boundary mutations algebraically before invoking LLM inference.

### Technical Specification
- **AST Constant Extraction:** For comparison mutations ($x < C, x \ge C$), parse the AST node to extract the identifier and threshold constant $C \in \mathbb{R}$.
- **Equivalence Partitioning:** Synthesize boundary probe values:
  $$\mathcal{T}_{\text{BVA}} = \{C - \epsilon, \; C, \; C + \epsilon\}$$
- **Hybrid Routing:**
  1. *Fast Path:* Attempt mutant kill using algorithmic BVA assertions (zero API cost, latency $< 1\text{ms}$).
  2. *Slow Path:* If BVA fails or the mutant touches non-scalar logic (stateful objects, database sessions, HTTP handlers), route to the LLM Verifier Synthesizer.

---

## 3. Patch-Aware AST Mutation (`scripts/patch_mutator.py`)

### Objective
Constrain AST mutations in repository-level benchmarks strictly to lines touched by pull requests.

### Technical Specification
- Parse Git unified diff headers (`@@ -line,count +line,count @@`) from benchmark task records.
- Filter AST tree visitors so only AST nodes whose `node.lineno` falls within the modified line ranges are mutated.
- Prevents generating hundreds of irrelevant mutants across untouched areas of large multi-thousand-line repository files.

---

## 4. Semantic Equivalent Mutant Pre-Filtering

### Objective
Eliminate unkillable equivalent mutants before test execution and synthesizer invocation.

### Technical Specification
- In software mutation testing, 5% to 15% of mutants are functionally equivalent to the original code (producing identical outputs for all valid inputs).
- Implement AST canonicalization rules to detect trivial equivalence (e.g. `x + 0 -> x`, or boundary conditions that evaluate to identical branches).
- Integrate SMT constraint solvers (Z3) for symbolic path equivalence verification.
