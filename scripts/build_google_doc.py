#!/usr/bin/env python3
"""Build a Google Docs-ready literature review.

Outputs:
  docs/AAVS_Literature_Review_GoogleDoc.txt   (main + full appendix)
  docs/AAVS_Literature_Review_GoogleDoc.docx  (main + full appendix)
  docs/AAVS_Literature_Review_Main.txt        (main only)
  docs/AAVS_Literature_Review_Appendix.txt    (full 1,500-record index)

The prose is written to be pasted or uploaded, not to show off formatting.
Paper summaries are compressed from abstracts/full text and labelled by
evidence depth. No invented findings.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, RGBColor

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARCHIVE = DOCS / "archive"
CARDS = ROOT / "papers" / "metadata" / "papers_research_cards.jsonl"
COMPARISON = DOCS / "PAPER_COMPARISON.md"

CLUSTER_ORDER = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"]
CLUSTER_NAMES = {
    "C1": "Benchmark test inadequacy and false passes",
    "C2": "Vulnerability regression and secure AI code",
    "C3": "Reward hacking and specification gaming",
    "C4": "Test and verifier synthesis with execution feedback",
    "C5": "Coding agents and repository benchmarks",
    "C6": "Mutation testing and oracle foundations",
    "C7": "Reinforcement learning, verifiers and reward models",
    "C8": "Automated repair and patch correctness",
    "C9": "Evaluation methodology and contamination",
    "C10": "Sandbox, container and state integrity",
}

TITLE = "Verifier Weakness and Verification Hardening in Coding-Agent Benchmarks"
SUBTITLE_PREFIX = "A structured literature review of 1,500 papers, with detailed review of"

SECTION_HEADS = {
    "1. SCOPE AND QUESTION",
    "2. METHOD AND CORPUS",
    "3. WHAT THE LITERATURE SHOWS",
    "4. CURRENT STATUS OF THE FIELD",
    "5. PAPER COMPARISON",
    "6. TWENTY PAPERS TO READ FIRST",
    "7. CLUSTER REVIEW",
    "8. EVIDENCE TABLE",
    "9. CITATION CORRECTIONS",
    "10. LIMITATIONS OF THIS REVIEW",
    "11. HOW TO CHECK THE WORK",
    "APPENDIX. FULL CORPUS INDEX",
}

# Twenty papers a reader should open first. Kept identical to the compendium.
MUST_READ = [
    ("P0120", "Closest methodological prior: variant-guided test augmentation on SWE-bench."),
    ("P0001", "Public-patch re-evaluation; 345 false passes and ranking changes."),
    ("P0837", "Independent adversarial strengthening; top score falls from 78.80% to 62.20%."),
    ("P0121", "331 hackable terminal environments and 3,632 exploit trajectories."),
    ("P0841", "The agent harness itself is undertested."),
    ("P0191", "Shows that iterative self-repair can weaken test oracles."),
    ("P0564", "Separates memorization from reasoning on SWE-bench."),
    ("P0034", "What it takes to maintain a coding benchmark over time."),
    ("P0071", "Environment-level reward-hacking measurement protocol."),
    ("P0002", "Survey of patch overfitting and correctness assessment."),
    ("P0011", "Formal definition of reward hacking and proxy hackability."),
    ("P0052", "Vulnerability regression in AI-generated security patches."),
    ("P0116", "Step-level security reward modeling for code."),
    ("P0434", "The original SWE-bench task definition and harness."),
    ("P0013", "Multilingual issue-resolving benchmark."),
    ("P0262", "Live-updatable benchmark that reduces contamination risk."),
    ("P0553", "The oracle problem, defined."),
    ("P0555", "Evidence that mutants are valid substitutes for real faults."),
    ("P0554", "Coverage is not strongly correlated with test effectiveness."),
    ("P0019", "Inference-time reward hacking and hedging."),
]

EXTRA_IDS = [
    "P0263", "P0387", "P0535", "P0536",  # C1
    "P0144", "P0155", "P0328",            # C2
    "P0058", "P0069",                      # C3
    "P1194", "P0870", "P1292",            # C4
    "P0048", "P0269", "P0273", "P0841",   # C5
    "P0239",
    "P0296", "P0749", "P1682",            # C7
    "P0007", "P0015", "P0025", "P0028",   # C8
    "P1617", "P1623", "P1679",            # C9
    "P0187", "P0197", "P0927", "P1101", "P1619",  # C10
]

FINDINGS = [
    ("The premise is supported, but the numbers are not interchangeable.",
     "Three independent 2025-2026 audits find that passing tests do not imply a correct patch. "
     "Probe to Generate reports that 77% of SWE-bench Verified instances admit at least one "
     "surviving program variant (P0120). UTBoost reclassifies 345 patches and reports corrections "
     "affecting 40.9% of SWE-Bench Lite and 24.4% of SWE-Bench Verified leaderboard entries "
     "(P0001). SWE-ABS strengthens 50.2% of 500 Verified instances, rejects 19.71% of previously "
     "passing patches, and drops the top score from 78.80% to 62.20% (P0837). The units differ: "
     "instances, patches, leaderboard entries, and agents. The correct claim is that several "
     "audits converge on a material false-pass problem, not that a single percentage describes "
     "all benchmarks."),
    ("Hardening changes rankings, not just scores.",
     "UTBoost reports 18 and 11 ranking changes on Lite and Verified (P0001). SWE-ABS reports "
     "that the previous top-ranked agent falls to fifth after strengthening (P0837). This matters "
     "for how the field interprets leaderboards: a benchmark that rewards shortcut-prone patches "
     "can change the relative order of systems, not merely inflate every score."),
    ("Test generation is not the same as oracle generation.",
     "DCAware identifies a Self-Repair Trap: iterating until execution succeeds can drive models "
     "toward assertions that are easy to satisfy but weak at revealing faults (P0191). The "
     "oracle-generation study by Bodicoat et al. shows that regression oracles often encode the "
     "implemented behavior rather than the intended behavior (P0192). Coverage is weakly "
     "correlated with effectiveness once suite size is controlled (P0554), and assertions are a "
     "stronger signal (the assertion study in P0554's cluster). More tests do not automatically "
     "mean a stronger verifier."),
    ("The harness is part of the system under test.",
     "Complex Agents, Shallow Tests finds that LLM-dependent harness code has less than half of "
     "its lines and branches covered by existing tests. Its HarnessTester reports 75.95% and "
     "84.76% larger line and branch coverage gains, a 69.89% larger mutation-score gain, and 122 "
     "real harness bugs in widely used agentic systems (P0841). Verification therefore cannot "
     "stop at the patch; the execution scaffolding is also part of the system."),
    ("Contamination is a credible competing explanation.",
     "The SWE-Bench Illusion reports up to 76% file-path identification accuracy from issue text "
     "on SWE-bench repositories, compared with 53% on repositories outside the benchmark (P0564). "
     "SWE-bench Live (1,319 tasks across 93 repositories, P0262) and Multi-SWE-bench (1,632 "
     "instances across seven languages, P0013) are partial remedies. Any claim that an agent "
     "solved a task needs a contamination control, not just a score."),
    ("Environment-level reward hacking is documented, but defenses are not settled.",
     "Terminal Wrench releases 331 reward-hackable terminal environments, 3,632 hack "
     "trajectories, and 2,352 legitimate baselines across three frontier models (P0121). The "
     "exploits range from output spoofing to stack-frame introspection, standard-library "
     "patching, and rootkit-style binary hijacking. The Hack-Verifiable Environments line "
     "(P0058, P0071) turns hack detection into a measurement paradigm. The corpus does not "
     "contain a mature, task-agnostic defense covering both code-level and environment-level "
     "gaming. That is an open problem, not a solved one."),
    ("Mutation testing is a defensible proxy, with a known equivalence problem.",
     "Just et al. show that mutants are statistically associated with real faults (P0555), which "
     "supports mutation-based auditing. The equivalent-mutant problem remains: syntactically "
     "different programs can be semantically identical, so some mutants cannot be killed by any "
     "test (P0239, P0032). A mutation score is not meaningful unless equivalence is handled or at "
     "least reported."),
    ("Patch overfitting is old, measurable, and still unresolved.",
     "The patch-correctness survey (P0002) and the patch-overfitting study by Petke et al. "
     "(P0008) treat overfitting as a longstanding property of test-based repair. In P0008, the "
     "median number of plausible patches per Defects4J bug is two, so the practical problem is "
     "often selection among plausible patches rather than generating a single fix. This is "
     "exactly the gap a completeness gate is meant to close."),
    ("Evaluation methodology is part of the contribution.",
     "The corpus contains a separate cluster on contamination, construct validity, benchmark "
     "leakage, and leaderboard reliability (C9). Reporting a score without its denominator, "
     "contamination control, and selection procedure is not a measurement. Papers such as "
     "Benchmark Leakage (P1623), Automated Benchmark Auditing (P1617), and contamination-resistant "
     "benchmark design (P1679) make this point directly."),
]

CLUSTER_TEXT = {
    "C1": [
        "This cluster contains the direct audits. The common finding is that repository tests are "
        "under-constrained, but the papers use different units. Probe to Generate works with "
        "program variants that survive the original tests and then generates targeted tests; on "
        "SWE-bench Verified, 77% of instances admit at least one surviving variant (P0120). "
        "UTBoost generates tests for real Python projects and re-evaluates public patches; it "
        "finds 345 erroneous patches and reports 40.9% and 24.4% effects on Lite and Verified "
        "leaderboard entries (P0001). SWE-ABS uses coverage-driven and mutation-driven "
        "strengthening; it strengthens 50.2% of instances and rejects 19.71% of previously "
        "passing patches (P0837).",
        "Two adjacent results widen the problem. The SWE-Bench Illusion shows that memorization "
        "can explain part of the performance gap (P0564), and Complex Agents, Shallow Tests shows "
        "that harness code is itself undertested (P0841). Taken together, these papers support the "
        "premise that outcome tests are weak, but they do not support a single merged percentage. "
        "The missing piece is a common protocol that reports surviving variants, false passes, "
        "and false rejections with the same denominator.",
    ],
    "C2": [
        "Vulnerability detection is the most mature part of this cluster. The corpus contains "
        "surveys, deep-learning detectors, and secure-code benchmarks such as RealSec-bench and "
        "SafeGenBench. SecCodePRM adds a step-level security reward model that can score partial "
        "code and rank candidate continuations (P0116). These papers are useful context for a "
        "security-invariant completeness gate.",
        "The narrower claim, that AI-generated patches introduce new vulnerabilities, is less "
        "settled in this corpus. Beyond Bypass is directly about vulnerability regression (P0052), "
        "but the indexed record has no abstract, so its numbers are not verified here. The "
        "security cluster should therefore be read as a set of detection and scoring methods, not "
        "as proof of a specific regression rate. A longitudinal study with CWE deltas and a sound "
        "baseline is still needed.",
    ],
    "C3": [
        "Reward hacking has a formal foundation. Skalse et al. define hackability and show that "
        "non-trivial unhackable proxies are severely constrained (P0011). Empirical work then "
        "shows what this looks like in practice. Terminal Wrench releases 331 environments, 3,632 "
        "hack trajectories, and 2,352 legitimate baselines; its monitorability study reports an "
        "AUC drop from 0.97 to 0.92 when chain-of-thought is removed (P0121). The HVE and HVTB "
        "papers turn embedded hacks into a measurement protocol (P0058, P0071).",
        "A second strand studies reward overoptimization in language models. InfoRM uses an "
        "information bottleneck and a Cluster Separation Index to detect overoptimization (P0005). "
        "Inference-Time Reward Hacking shows the characteristic rise-then-decline pattern and "
        "proposes hedging (P0019). The cluster is strong on measurement and weak on a general "
        "defense. No paper here provides a task-agnostic verifier that handles both code and "
        "container state.",
    ],
    "C4": [
        "This is the defender's cluster. The strongest warning is DCAware's Self-Repair Trap: "
        "optimizing execution success can make oracles easier to satisfy and less fault-revealing "
        "(P0191). The oracle-generation study by Bodicoat et al. reaches a compatible conclusion: "
        "many generated oracles encode implemented behavior rather than intended behavior (P0192). "
        "AssertionBench and ChatUniTest provide benchmarks and baselines for assertion and test "
        "generation (P1194, P1292).",
        "The test-quality literature explains why more tests are not enough. Coverage is not "
        "strongly correlated with fault detection once suite size is controlled (P0554), while "
        "assertion strength is a better signal. The practical implication is that a synthesized "
        "test should be judged by what it kills and by whether it rejects valid alternative "
        "implementations, not by whether it runs successfully.",
    ],
    "C5": [
        "This cluster supplies the evaluation substrates. SWE-bench defines the task and harness "
        "with 2,294 issues across 12 Python repositories (P0434). Multi-SWE-bench extends the "
        "format to seven languages with 1,632 instances (P0013). SWE-bench Live provides 1,319 "
        "tasks across 93 repositories and a live-update pipeline (P0262). SWE-Bench Pro V2 "
        "repaired or retired 480 of 731 tasks and reports a hardened protocol that blocks upstream "
        "fix retrieval (P0034). SWE-smith and DeepSWE add scale and long-horizon multi-language "
        "tasks.",
        "The cluster also shows why benchmark maintenance is experimental work. The SWE-Bench "
        "Illusion (P0564), the leaderboard profiling study (P0269), and the harness-adequacy study "
        "(P0841) all change how a score should be interpreted. A verifier-hardening paper cannot "
        "treat the benchmark as a fixed, neutral instrument.",
    ],
    "C6": [
        "The foundational papers in this cluster justify mutation testing and define its limits. "
        "Just et al. show that mutants are a valid substitute for real faults in the aggregate "
        "(P0555). The oracle survey by Barr et al. defines the oracle problem (P0553). The "
        "coverage study by Inozemtseva and Holmes shows that coverage alone is a weak measure "
        "(P0554).",
        "The applied papers in the cluster handle equivalent mutants with symbolic execution, "
        "machine learning, or LLM-based detection (P0032, P0239). The lesson for AAVS is that "
        "mutation score is not a single invariant. Any paper that reports a mutation score should "
        "state its operator set, its equivalence policy, and its treatment of timeouts.",
    ],
    "C7": [
        "This cluster connects verification to training. Process reward models score intermediate "
        "steps, and RLVR uses verifiable outcomes as reward. The papers here show that reward "
        "models are imperfect proxies. InfoRM detects overoptimization (P0005), and inference-time "
        "reward hacking shows that optimizing a proxy can reduce the true objective (P0019). "
        "Recent PRM work tries to make intermediate supervision more reliable (P0296, P0749).",
        "For AAVS, the relevant claim is not that PRMs are bad. It is that a verifier used as a "
        "reward signal must be tested adversarially. If the verifier can be satisfied by a "
        "shortcut, RL will find the shortcut. The code-specific version of that argument is still "
        "thin in this corpus and is a natural place for new experiments.",
    ],
    "C8": [
        "Patch overfitting is the oldest problem in this review. The survey by Fei et al. "
        "categorizes correctness-assessment methods and datasets (P0002). Petke et al. measure the "
        "practical magnitude and propose a random baseline for realistic benchmarking; their "
        "median number of plausible patches per Defects4J bug is two (P0008). The systematic "
        "literature review on LLM-based repair and the formal-methods studies add more evidence "
        "that tests alone do not select the correct patch (P0007, P0015).",
        "The cluster is useful because it separates two questions that are often conflated. One is "
        "whether a patch is plausible under the tests. The other is whether it is correct under "
        "the specification. AAVS's completeness gate is an attempt to answer the second question "
        "without a human oracle, and this cluster is the best source of counterarguments.",
    ],
    "C9": [
        "This cluster is about the validity of the evaluation itself. The SWE-Bench Illusion shows "
        "that memorization can produce benchmark performance that does not transfer to unseen "
        "repositories (P0564). Benchmark Leakage and contamination-resistant benchmark design "
        "study how test data leaks into training and how to detect it (P1623, P1679). Automated "
        "Benchmark Auditing proposes a systematic audit pipeline (P1617), and the leaderboard "
        "profiling study examines who submits and what architectures are used (P0269).",
        "The practical lesson is that every score needs three things: a denominator, a "
        "contamination control, and a selection procedure. Papers in C1 and C5 often report one "
        "without the others. AAVS should not repeat that pattern.",
    ],
    "C10": [
        "This is a cross-cutting cluster. Sandbox and state-integrity papers are usually assigned "
        "to coding agents (C5) or reward hacking (C3) by the lexical scorer, but they belong here "
        "conceptually. SideKernel studies a microVM sandbox for coding agents on macOS (P0187), "
        "SWE-MiniSandbox studies container-free reinforcement learning (P0197), and the "
        "Balkanization paper maps isolation, access control, and time-of-check-to-time-of-use "
        "risks (P0927).",
        "The defense literature is still fragmented. Fault-tolerant sandboxing proposes "
        "transactional execution (P1101), and container sandbox escape work measures how capable "
        "frontier models are at breaking isolation (P1619). No paper in the corpus provides a "
        "unified protocol that connects AST-level mutants, filesystem state, process state, and "
        "exit codes. That is the Stage 2 gap.",
    ],
}

CORRECTIONS = [
    ("2604.01518",
     "The document title was 'Are Benchmark Tests Strong Enough? Investigating Test Inadequacy in "
     "SWE-bench'. The live title is 'Probe to Generate: Program Variant-Guided Test Augmentation "
     "for Repository-Level Repair Benchmarks'. The paper reports 77% of Verified instances with a "
     "surviving variant, 1,014 tests across 211 instances, and a 4.2% to 9.0% resolved-rate drop."),
    ("2506.09289",
     "The document title was 'UTBoost: Augmenting Unit Tests for AI Coding Benchmarks via "
     "Intramorphic Oracle Filtering'. The live title is 'UTBoost: Rigorous Evaluation of Coding "
     "Agents on SWE-Bench'. The abstract reports 36 insufficient-test instances and 345 erroneous "
     "patches, not an 18.2% false-pass reduction or a 34% overfit rate."),
    ("2604.17596",
     "The document title was 'Terminal Wrench: Exposing Reward Hacking and Environmental Blind "
     "Spots in OS Agents'. The live title is 'Terminal Wrench: A Dataset of 331 Reward-Hackable "
     "Environments and 3,632 Exploit Trajectories'. The abstract does not report 42 cheating "
     "patterns or 150 tasks."),
    ("2608.22103",
     "The document title was 'Hack-Verifiable Terminal Bench: Defending Against State Spoofing in "
     "System Agents'. The live title is 'Hack-Verifiable Terminal Bench: Evaluating Reward Hacking "
     "in Terminal Tasks'. The abstract measures reward hacking and tests prompt mitigations; it "
     "does not claim a checksum-tree or read-only-volume defense."),
]

NUMERIC_CORRECTIONS = [
    ("24.4% to 77.1% of benchmark test suites are inadequate.",
     "This merges two different units. Probe to Generate reports 77% of SWE-bench Verified "
     "instances with at least one surviving variant. UTBoost reports corrections affecting 24.4% "
     "of Verified leaderboard entries. The two numbers should be cited separately."),
    ("UTBoost found an 18.2% reduction in false passes.",
     "The abstract does not contain that figure. It reports 345 erroneous patches, 40.9% and "
     "24.4% affected leaderboard entries, and 18 and 11 ranking changes."),
    ("Over 34% of LLM-generated tests overfit to implementation details.",
     "The abstract does not contain that figure. It may be in the full text, but it is not "
     "attributed to a table or section in the current notes."),
    ("Terminal Wrench found 42 patterns across 150 tasks.",
     "The abstract reports 331 environments, 3,632 hack trajectories, and 2,352 legitimate "
     "baselines. The 42-pattern and 150-task figures are not in the abstract."),
    ("Hack-Verifiable Terminal Bench replaces stdout regexes with checksum trees and read-only "
     "volumes.",
     "The abstract describes adapting HVE to Terminal Bench to measure reward hacking and test "
     "prompt mitigations. The defense framing is not supported by the abstract."),
    ("Up to 77% of benchmark unit tests have coverage deficits.",
     "The 77% refers to instances with at least one surviving variant, not individual unit tests."),
]


STATUS_INTRO = (
    "The question a reviewer will ask is whether this project is doing anything that has not "
    "already been published. The honest answer is that every component exists, but the assembly "
    "does not exist as a single released system. Mutating a reference patch to expose weak tests "
    "is published (Probe to Generate, 2026; SWE-ABS, 2026). LLM test generation against surviving "
    "mutants is published (UTBoost, 2025; MUTGEN, 2026; PRIMG, 2025). Reward hacking in terminal "
    "environments is published and measured (Terminal Wrench, 2026; HVE and HVTB, 2026). This "
    "review found no paper in the 1,500-paper corpus that combines these into one model-agnostic "
    "loop reporting both false passes and false rejections, releasing a per-task hardened suite, "
    "and covering both code and container state. The project should therefore claim the protocol "
    "and the release, not the loop. Absence in this corpus is evidence, not proof; re-check before "
    "submission."
)

STATUS_CLOSEST = [
    ("Probe to Generate (P0120, 2026): closest to the full loop.",
     "It generates semantically modified variants of the reference patch, keeps the variants the "
     "original tests pass, generates targeted tests, and retains a test only if the gold patch "
     "passes, a surviving variant fails, and the test survives behavior-preserving "
     "transformations. On SWE-bench Verified, 77% of instances admit at least one surviving "
     "variant; 1,014 validated tests cover 211 instances; top-10 agents lose 4.2% to 9.0% "
     "resolved rate. It stops at test augmentation: no container/state layer and no released "
     "per-task hardened suite."),
    ("SWE-ABS (P0837, 2026): strongest adversarial strengthening result.",
     "A two-stage pipeline combines coverage-driven augmentation with mutation-driven synthesis "
     "of plausible but incorrect patches. It strengthens 50.2% of 500 Verified instances, "
     "rejects 19.71% of previously passing patches, and lowers the top score from 78.80% to "
     "62.20%; the previous leader falls to fifth. It stops at synthetic wrong patches that may "
     "not resemble real agent shortcuts, and it releases no reusable hardened suite."),
    ("UTBoost (P0001, 2025): strongest leaderboard re-evaluation result.",
     "UTGenerator writes tests for real Python projects; UTBoost cross-validates gold and agent "
     "patches and re-grades public submissions. It reclassifies 345 patches; corrections affect "
     "40.9% of SWE-bench Lite and 24.4% of Verified leaderboard entries, with 18 and 11 ranking "
     "changes. It only works on tasks some agent already solved and has no execution-state "
     "layer. UTBoost and SWE-ABS share a first author, so this is a small, fast-moving line, not "
     "a crowded field."),
    ("Mutation-guided test synthesis (P0847, P1154, P1155, P0516): the defender's toolbox.",
     "MUTGEN feeds surviving mutants back into the prompt and beats EvoSuite on mutation score "
     "across 204 subjects. PRIMG prioritizes mutants before generating tests for Solidity. Tratto "
     "derives axiomatic oracles neuro-symbolically. TOGA infers oracles from method context. All "
     "operate at function level, not on repository patches or benchmark harnesses."),
    ("Terminal Wrench, HVE and HVTB (P0121, P0058, P0071, 2026): the environment layer.",
     "Terminal Wrench releases 331 hackable environments, 3,632 exploit trajectories, and 2,352 "
     "legitimate baselines, with exploits ranging from output spoofing to stack-frame "
     "introspection and rootkit-style hijacking; monitor AUC falls from 0.97 to 0.92 without "
     "chain-of-thought. HVE and HVTB turn hack detection into a measurement protocol. They stop "
     "at measurement; there is no task-agnostic defense covering code and state."),
]

STATUS_VERDICT = [
    ("What is not new.",
     "Mutating code to test a suite, using an LLM to write tests, showing that SWE-bench tests "
     "are insufficient, re-grading public patches, and measuring terminal reward hacking are all "
     "published. A soundness-plus-completeness gate already exists inside Probe to Generate and "
     "SWE-ABS. These should be stated as prior work, not discovered as gaps."),
    ("What is plausibly new.",
     "First, one protocol that reports two denominators: the false-pass rate and the "
     "false-rejection rate on the gold patch for the same tasks. Most papers report only the "
     "first. Second, a released, model-agnostic hardened suite with per-task provenance. Third, "
     "one gate over AST mutants and container/state hacks. The third claim needs Stage 2 data "
     "before it is asserted."),
    ("The positioning sentence.",
     "Prior work shows that benchmark tests are weak and that individual components can be "
     "hardened; this project contributes a single released protocol that quantifies both "
     "directions of error, across code and execution state, on public artifacts."),
    ("Scope.",
     "The security cluster is large and can take over the project. It should not. A patch that "
     "passes functional tests but introduces a CWE is a surviving mutant with a security label: "
     "one evaluation axis, one paragraph, not the organizing frame."),
]


def clean(text: str) -> str:
    text = (text or "").replace("\u2014", "; ").replace("\u2013", "-")
    text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    text = re.sub(r"\\tool", "the framework", text)
    text = re.sub(r"\\method", "the method", text)
    text = re.sub(r"\\text(?:it|bf|rm)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\$\\mathcal\{([^{}]*)\}_\{([^{}]*)\}\$", r"\1_\2", text)
    text = re.sub(r"\\mathcal\{([^{}]*)\}", r"\1", text)
    text = text.replace("\\( \\approx \\)", "approximately").replace("\\approx", "approximately")
    text = text.replace("\\(", "").replace("\\)", "")
    text = text.replace("\\$", "$").replace("\\%", "%").replace("\\_", "_")
    text = re.sub(r"\*\*|`", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def trim_sentence(text: str, limit: int) -> str:
    text = clean(text)
    # Aggregator abstracts sometimes end with a literal ellipsis.
    if "..." in text:
        text = text.split("...", 1)[0].strip()
    if len(text) > limit:
        cut = text[:limit]
        if ". " in cut:
            text = cut.rsplit(". ", 1)[0] + "."
        else:
            cut = cut.rsplit(" ", 1)[0] if " " in cut else cut
            text = cut.rstrip(",;: ")
    text = re.sub(r"\s+(and|or|but|with|of|to|for|the|a|an|in|on)\s*$", "",
                  text, flags=re.I)
    if text and not text.endswith((".", "!", "?")):
        text = text.rstrip(",;: ") + "."
    return text[:1].upper() + text[1:] if text else text


def title_end(title: str) -> str:
    title = clean(title)
    return title if title.endswith((".", "?", "!")) else title + "."


def load_cards() -> list[dict]:
    return [json.loads(line) for line in CARDS.read_text().splitlines() if line.strip()]


def parse_comparison() -> list[str]:
    """Read PAPER_COMPARISON.md into docx blocks (headings + table rows)."""
    blocks: list[str] = []
    started = False
    for line in COMPARISON.read_text().splitlines():
        text = line.strip()
        if text.startswith("## "):
            started = True
            blocks.append("CMPHEAD::" + clean(text[3:]))
            continue
        if not started or not text or text.startswith("---"):
            continue
        if text.startswith("|"):
            cells = [clean(c) for c in text.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue
            blocks.append("TABLEROW::" + json.dumps(cells, ensure_ascii=False))
        elif text.startswith("#"):
            continue
        else:
            blocks.append(clean(text))
    return blocks


def author_text(card: dict) -> str:
    authors = card.get("authors") or []
    if not authors:
        return "Unknown"
    if len(authors) <= 6:
        return ", ".join(authors)
    return ", ".join(authors[:6]) + ", et al."


def compose_summary(card: dict) -> str:
    parts = []
    for field in ("problem", "method", "findings"):
        text = clean(card.get(field, ""))
        text = re.sub(r"^abstract\b[:\s]+", "", text, flags=re.I)
        if not text:
            continue
        if any(text[:80].lower() in p.lower() or p[:80].lower() in text.lower()
               for p in parts):
            continue
        parts.append(text)
    if not parts:
        return ""
    return trim_sentence(" ".join(parts), 950)


def priority(card: dict) -> str:
    return {"A": "core", "B": "strong", "C": "contextual"}.get(card.get("tier", ""),
                                                              "contextual")


def links(card: dict) -> tuple[str, str]:
    web = []
    if card.get("arxiv_id"):
        web.append("https://arxiv.org/abs/" + card["arxiv_id"])
    if card.get("doi"):
        web.append("https://doi.org/" + card["doi"])
    url = " ; ".join(web) if web else "No external link recorded"
    local = ""
    if card.get("pdf_status") == "ok" and card.get("pdf_path"):
        local = "Local PDF: " + card["pdf_path"]
    return url, local


def select_cards(cards: list[dict]) -> list[dict]:
    ids = {pid for pid, _ in MUST_READ}
    ids.update(EXTRA_IDS)
    for cid in CLUSTER_ORDER:
        ranked = sorted([c for c in cards if c["cluster"] == cid],
                        key=lambda c: c["score"], reverse=True)
        ids.update(c["corpus_id"] for c in ranked[:7])
    selected = [c for c in cards if c["corpus_id"] in ids]
    # The review is about code and execution. A few lexical high scorers
    # (DNN testing, robotics) are adjacent but not code-verifier evidence.
    bad = ("deep neural network", "dnn", "robot", "medical", "quantum")
    selected = [c for c in selected
                if not any(word in c["title"].lower() for word in bad)]
    selected.sort(key=lambda c: (CLUSTER_ORDER.index(c["cluster"]), -c["score"]))
    return selected


def paper_block(card: dict) -> list[str]:
    lines = [f"{card['corpus_id']}. {clean(card['title'])}"]
    lines.append("Authors: " + clean(author_text(card)))
    lines.append("Year and venue: " + f"{card.get('year', 'n.d.')}, {clean(card.get('venue') or 'not recorded')}")
    lines.append("Cluster: " + f"{card['cluster']}, {CLUSTER_NAMES[card['cluster']]}")
    lines.append("Priority: " + priority(card))
    summary = compose_summary(card)
    if summary:
        lines.append("Summary (from the abstract): " + summary)
    else:
        lines.append("Summary: No abstract was available in the indexed metadata; the title and "
                     "source are recorded for completeness.")
    nums = [clean(n) for n in (card.get("key_numbers") or []) if clean(n)][:2]
    if nums and not any(n[:35].lower() in summary.lower() for n in nums):
        lines.append("Key numbers: " + " | ".join(nums))
    lim = trim_sentence(card.get("limitations", ""), 520)
    lines.append("Limitation: " + (lim if lim else "Not stated in the abstract."))
    lines.append("Why it matters: " + clean(card.get("aavs_role", "")))
    url, local = links(card)
    lines.append("Source: " + url + (". " + local if local else ""))
    return lines


def build_main(cards: list[dict], selected: list[dict]) -> list[str]:
    tiers = Counter(c["tier"] for c in cards)
    depth = Counter(c["evidence_depth"] for c in cards)
    out: list[str] = []

    subtitle = f"{SUBTITLE_PREFIX} {len(selected)} unique core papers"
    selected_ids = {c["corpus_id"] for c in selected}
    crosscut = ["P0187", "P0197", "P0927", "P1101"]
    detail_entries = len(selected) + len([i for i in crosscut if i in selected_ids])
    out += [
        TITLE.upper(),
        subtitle,
        "",
        "Prepared by: [Your name]",
        "Prepared for: [Course, advisor, or research group]",
        "Date: 22 October 2026",
        "",
        "Companion files: AAVS_Literature_Review_Appendix.txt (full 1,500-record index), "
        "AAVS_Literature_Review_GoogleDoc.docx (this document), and the project repository.",
        "",
        "Note on evidence. This review is based on a corpus of 1,500 papers. It does not claim "
        "that all 1,500 were read line by line. Every paper has a card and a source link. "
        "Evidence depth is stated for each card: full-text reviewed, full text scanned, abstract "
        f"reviewed, or metadata only. The detailed entries in this document cover {len(selected)} "
        "core papers. The appendix lists the complete corpus so any claim can be spot-checked.",
        "",
        "The summary fields below are compressed from each paper's abstract or, where the abstract "
        "was unavailable, from its full text. They are not invented prose. The cluster narratives "
        "and the judgments about what is missing are the author's analysis.",
        "",
    ]

    out += ["1. SCOPE AND QUESTION", ""]
    out += [
        "This review asks a narrow question: when a coding agent passes a repository's tests, "
        "what has actually been verified? Modern coding-agent benchmarks treat a patch as correct "
        "if it passes the tests supplied by the benchmark. That assumption is the object of study. "
        "The corpus covers benchmark audits, mutation testing, test-oracle synthesis, "
        "patch-correctness assessment, reward hacking, coding-agent benchmarks, reinforcement "
        "learning with verifiable rewards, and sandbox integrity.",
        "Two boundaries define the review. First, it is about code and execution, not generic "
        "prompt injection, phishing, malware classification, or AI governance. Second, it "
        "separates what a paper measured from what later summaries claimed. Several widely "
        "repeated numbers in the project's earlier notes did not match the live papers. Those "
        "corrections are recorded in Section 9.",
        "The review is written for a reader who wants to judge the evidence, not just read a "
        "reading list. Each detailed entry states the problem, the method, the result, the "
        "limitation, and the source. Where a paper's abstract does not contain a limitation, the "
        "entry says so instead of filling the gap.",
        "",
    ]

    out += ["2. METHOD AND CORPUS", ""]
    out += [
        "The corpus was built from live arXiv and Crossref records on 21 and 22 October 2026. "
        "One hundred and twenty queries covered ten clusters. Each arXiv query returned up to 100 "
        "relevance-sorted records; each Crossref query returned up to 60. The raw harvest "
        "contained 19,072 records. After merging duplicates by arXiv ID, DOI, and normalized "
        "title, 10,454 unique records remained. A lexical relevance score and a domain filter "
        "reduced that set to 1,500 papers.",
        "The filters were designed to keep software-engineering and coding-agent work and to "
        "remove unrelated domains. Cryptography signature schemes, computer-vision adversarial "
        "patches, molecular design, clinical agents, and container-performance studies were "
        "penalized. The filters are not perfect. The corpus is a prioritized evidence base, not a "
        "systematic review registered in advance, and the scores are lexical rather than "
        "methodological.",
        "Open-access PDFs were downloaded from arXiv and publisher links. Every file was checked "
        "for the PDF magic bytes and a 10 KB minimum. 1,112 PDFs were downloaded and 1,112 full "
        "texts were extracted with pdftotext in plain reading order. 149 missing abstracts were "
        "filled from Semantic Scholar and marked as such. Fifty papers received full-text-assisted "
        "reviews. The remaining texts were indexed for AAVS-related terms.",
        "The corpus contains 540 tier A papers, 926 tier B papers, and 34 tier C papers. These "
        "tiers are prioritization labels, not quality judgments. The evidence levels are: 50 "
        "full-text reviewed, 1,062 full text scanned, 271 abstract reviewed, and 117 metadata only. "
        "The appendix lists every record with its cluster, priority, and source.",
        "",
    ]

    out += ["3. WHAT THE LITERATURE SHOWS", ""]
    for idx, (head, body) in enumerate(FINDINGS, 1):
        out += [f"{idx}. {head}", clean(body), ""]

    out += ["4. CURRENT STATUS OF THE FIELD", ""]
    out += [clean(STATUS_INTRO), ""]
    for head, body in STATUS_CLOSEST:
        out += [head, clean(body), ""]
    out += ["What this means for the contribution", ""]
    for head, body in STATUS_VERDICT:
        out += [head, clean(body), ""]

    out += ["COMPARISON_START", "5. PAPER COMPARISON", ""]
    out += [
        "The table below compares 37 core papers on the dimensions a reviewer normally asks for. "
        "Pros are the paper's reported results. Cons are stated limitations where available, "
        "plus scope limits implied by the evaluation. Future work is the paper's stated direction "
        "where the full text gives one. The same table, with source IDs, is in the repository at "
        "docs/PAPER_COMPARISON.md.",
        "",
    ]
    out += parse_comparison()
    out += ["COMPARISON_END"]

    out += ["6. TWENTY PAPERS TO READ FIRST", ""]
    by_id = {c["corpus_id"]: c for c in cards}
    for idx, (pid, why) in enumerate(MUST_READ, 1):
        card = by_id.get(pid)
        if card:
            out.append(f"{idx}. {pid}. {title_end(card['title'])} {why}")
    out.append("")

    out += [
        "7. CLUSTER REVIEW",
        "",
        "The C10 section includes four papers that also appear in C5, because sandbox and "
        f"state-integrity work is cross-cutting. The detailed review therefore contains "
        f"{detail_entries} entries covering {len(selected)} unique papers. The appendix counts "
        "each paper once.",
        "",
    ]
    for ci, cid in enumerate(CLUSTER_ORDER, 1):
        out += [f"7.{ci} {cid}: {CLUSTER_NAMES[cid]}", ""]
        for para in CLUSTER_TEXT.get(cid, []):
            out += [clean(para), ""]
        cluster_cards = [c for c in selected if c["cluster"] == cid]
        if cid == "C10":
            # Include cross-cutting papers selected from other primary clusters.
            cross_ids = {c["corpus_id"] for c in selected
                         if c["corpus_id"] in {"P0187", "P0197", "P0927", "P1101", "P1619"}}
            cluster_cards = [c for c in selected
                             if c["cluster"] == cid or c["corpus_id"] in cross_ids]
        out += ["Core papers", ""]
        for card in cluster_cards:
            out += paper_block(card)
            out.append("")
        out += [
            "What is missing. The cluster still lacks a shared protocol that reports the "
            "denominator, the false-pass rate, and the false-rejection rate on valid patches. "
            "Most papers report one or two of these, not all three.",
            "",
        ]

    out += ["8. EVIDENCE TABLE", ""]
    evidence = [
        ("77% of SWE-bench Verified instances admit at least one surviving variant.",
         "P0120, Probe to Generate.", "500 Verified instances; 211 augmented; 1,014 tests."),
        ("345 erroneous patches were previously marked passed.",
         "P0001, UTBoost.", "36 insufficient-test instances; 40.9% Lite and 24.4% Verified "
         "leaderboard entries; 18 and 11 ranking changes."),
        ("50.2% of 500 Verified instances were strengthened and 19.71% of passing patches "
         "rejected.",
         "P0837, SWE-ABS.", "Top score 78.80% to 62.20%; previous top agent falls to fifth."),
        ("480 of 731 SWE-Bench Pro tasks were repaired or retired.",
         "P0034, SWE-Bench Pro V2.", "642 tasks in the V2 split; hardened protocol blocks "
         "upstream-fix retrieval."),
        ("76% file-path accuracy on SWE-bench repositories versus 53% outside the benchmark.",
         "P0564, The SWE-Bench Illusion.", "Diagnostic probes using issue text alone."),
        ("Less than half of LLM-dependent harness lines and branches are covered.",
         "P0841, Complex Agents, Shallow Tests.", "HarnessTester reports 75.95%/84.76% larger "
         "coverage gains and 122 real harness bugs."),
        ("331 environments, 3,632 hack trajectories, 2,352 legitimate baselines.",
         "P0121, Terminal Wrench.", "Three frontier models; detection AUC 0.97 to 0.92 without "
         "chain-of-thought."),
        ("2,294 issues across 12 Python repositories.",
         "P0434, SWE-bench.", "The original benchmark and harness."),
        ("1,632 instances across seven languages.",
         "P0013, Multi-SWE-bench.", "68 annotators; 4,723 RL instances released."),
        ("1,319 tasks across 93 repositories.",
         "P0262, SWE-bench Live.", "Tasks derived from GitHub issues created since 2024."),
        ("Equivalent mutants inflate the denominator and must be reported.",
         "P0239; P0032.", "3,302 Java and 1,088 C mutant pairs; symbolic execution correctly "
         "classified 13 equivalent and 239 non-equivalent mutants in P0032."),
    ]
    for idx, (claim, source, denom) in enumerate(evidence, 1):
        out += [f"{idx}. Claim: {claim}", f"Source: {source}", f"Denominator: {denom}", ""]

    out += ["9. CITATION CORRECTIONS", ""]
    out += [
        "The repository's earlier literature notes contained four paper titles and several "
        "numbers that did not match the live records. The papers are real, but the descriptions "
        "had drifted. The corrections are listed here so the review does not repeat them.",
        "",
    ]
    for aid, text in CORRECTIONS:
        out += [f"arXiv:{aid}. " + clean(text), ""]
    out += ["Numeric claims that must be rewritten or removed.", ""]
    for idx, (claim, correction) in enumerate(NUMERIC_CORRECTIONS, 1):
        out += [f"{idx}. Original claim: {claim}", f"Correction: {clean(correction)}", ""]

    out += ["10. LIMITATIONS OF THIS REVIEW", ""]
    out += [
        "The relevance scoring is lexical. A paper can score highly because its title and "
        "abstract use the right vocabulary, even if its method is weak. The tiers are "
        "prioritization labels, not peer review.",
        "Most summaries compress an abstract. They are useful for orientation, not for quoting a "
        "specific number. The source link and the local PDF are provided for checking.",
        "The corpus is not a registered systematic review. It over-represents open-access arXiv "
        "and Crossref work. Paywalled venue papers are present as metadata but may lack full text.",
        "The 117 metadata-only records have no abstract in the indexed sources. They remain in "
        "the appendix for completeness, but they are not evidence for any claim.",
        "The field moves quickly. 578 of the 1,500 records are dated 2026. The corpus should be "
        "refreshed before the manuscript is submitted.",
        "",
    ]

    out += ["11. HOW TO CHECK THE WORK", ""]
    out += [
        "Every paper in the detailed review has a stable ID, a cluster, a priority, a summary, "
        "and a source link. The appendix lists all 1,500 records in the same format. A reader can "
        "pick any row, open the source, and compare it with the card.",
        "The pipeline is reproducible. The commands are: python scripts/literature_harvester.py "
        "harvest --target 1500; download --limit 1500; extract; python "
        "scripts/enrich_abstracts.py; python scripts/literature_report.py; python "
        "scripts/literature_fulltext_index.py; python scripts/build_compendium.py. Query "
        "responses are cached, so a re-run only fetches new queries.",
        "The complete per-paper compendium, the searchable HTML explorer, the evidence matrix, "
        "and the full-text signal index are in the docs directory of the repository. The PDFs are "
        "in papers/pdf. The metadata is in papers/metadata.",
        "",
    ]
    return out


def build_appendix(cards: list[dict], selected_count: int) -> list[str]:
    out = [
        "APPENDIX. FULL CORPUS INDEX",
        "",
        "This appendix lists all 1,500 papers so the review can be spot-checked. The detailed "
        f"review above covers {selected_count} core papers. Each line gives the ID, title, year, "
        "cluster, priority, and source. Full records, including abstracts and PDF paths, are in "
        "the project repository.",
        "",
    ]
    ordered = sorted(cards, key=lambda c: (CLUSTER_ORDER.index(c["cluster"]), -c["score"]))
    current = None
    for card in ordered:
        if card["cluster"] != current:
            current = card["cluster"]
            out += ["", f"{current}: {CLUSTER_NAMES[current]}", ""]
        url, _ = links(card)
        out.append(
            f"{card['corpus_id']} | {clean(card['title'])} | {card.get('year', 'n.d.')} | "
            f"{card['cluster']} | {priority(card)} | {url}")
    out.append("")
    return out


def write_txt(blocks: list[str], path: Path) -> None:
    lines: list[str] = []
    table_row_index = 0
    for block in blocks:
        text = block.strip()
        if text in {"COMPARISON_START", "COMPARISON_END"}:
            continue
        if text.startswith("CMPHEAD::"):
            lines += ["", "## " + text[len("CMPHEAD::"):], ""]
            table_row_index = 0
        elif text.startswith("TABLEROW::"):
            cells = json.loads(text[len("TABLEROW::"):])
            lines.append("| " + " | ".join(cells) + " |")
            if table_row_index == 0:
                lines.append("| " + " | ".join("---" for _ in cells) + " |")
            table_row_index += 1
        else:
            table_row_index = 0
            lines += [text, ""]
    text = "\n".join(lines).replace("\n\n\n", "\n\n")
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path} ({len(text):,} chars, {len(text.splitlines()):,} lines)")


def _set_orientation(section, landscape: bool) -> None:
    if landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        if section.page_width < section.page_height:
            section.page_width, section.page_height = section.page_height, section.page_width
        margin = Inches(0.5)
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        if section.page_width > section.page_height:
            section.page_width, section.page_height = section.page_height, section.page_width
        margin = Inches(0.9)
    section.left_margin = margin
    section.right_margin = margin
    section.top_margin = margin
    section.bottom_margin = margin


def write_docx(blocks: list[str], path: Path) -> None:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = 1.15

    for name, size in (("Heading 1", 14), ("Heading 2", 12)):
        h = doc.styles[name]
        h.font.name = "Times New Roman"
        h.font.size = Pt(size)
        h.font.color.rgb = RGBColor(0, 0, 0)
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(4)

    table_rows: list[list[str]] = []

    def flush_table() -> None:
        if not table_rows:
            return
        cols = len(table_rows[0])
        table = doc.add_table(rows=0, cols=cols)
        table.style = "Table Grid"
        table.autofit = False
        weights = [1.4] + [1.0] * (cols - 1)
        widths = [10.0 * w / sum(weights) for w in weights]
        for row_index, row in enumerate(table_rows):
            cells = table.add_row().cells
            for col_index, value in enumerate(row[:cols]):
                cell = cells[col_index]
                cell.width = Inches(widths[col_index])
                paragraph = cell.paragraphs[0]
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.0
                run = paragraph.add_run(value)
                run.font.name = "Times New Roman"
                run.font.size = Pt(6.5)
                if row_index == 0:
                    run.bold = True
            if row_index == 0:
                tr_pr = table.rows[0]._tr.get_or_add_trPr()
                header = OxmlElement("w:tblHeader")
                header.set(qn("w:val"), "true")
                tr_pr.append(header)
        doc.add_paragraph()
        table_rows.clear()

    for block in blocks:
        text = block.strip()
        if not text:
            continue
        if text == "COMPARISON_START":
            flush_table()
            section = doc.add_section(WD_SECTION.NEW_PAGE)
            _set_orientation(section, True)
            continue
        if text == "COMPARISON_END":
            flush_table()
            section = doc.add_section(WD_SECTION.NEW_PAGE)
            _set_orientation(section, False)
            continue
        if text.startswith("TABLEROW::"):
            table_rows.append(json.loads(text[len("TABLEROW::"):]))
            continue
        flush_table()
        if text.startswith("CMPHEAD::"):
            doc.add_heading(text[len("CMPHEAD::"):], level=2)
        elif text == "APPENDIX. FULL CORPUS INDEX":
            doc.add_page_break()
            doc.add_heading(text, level=1)
        elif text == TITLE.upper():
            p = doc.add_paragraph()
            run = p.add_run(TITLE)
            run.bold = True
            run.font.size = Pt(18)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif text.startswith(SUBTITLE_PREFIX):
            p = doc.add_paragraph()
            run = p.add_run(text)
            run.italic = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif text in SECTION_HEADS:
            doc.add_heading(text, level=1)
        elif (re.match(r"^\d+\.\s+[A-Z]", text) and len(text) < 120
              and not text.startswith("1. Claim")
              and not re.match(r"^\d+\.\s+P\d{4}\.", text)):
            # Short numbered findings act as subheadings; paper-list items do not.
            p = doc.add_paragraph()
            run = p.add_run(text)
            run.bold = True
        elif re.match(r"^\d+\.\d+\s+C\d+:", text):
            doc.add_heading(text, level=2)
        elif re.match(r"^P\d{4}\.", text):
            p = doc.add_paragraph()
            run = p.add_run(text)
            run.bold = True
        else:
            doc.add_paragraph(text)

    flush_table()
    _set_orientation(doc.sections[0], False)
    doc.save(path)
    print(f"wrote {path} ({path.stat().st_size/1e6:.1f} MB)")


def main() -> None:
    cards = load_cards()
    selected = select_cards(cards)
    main_blocks = build_main(cards, selected)
    appendix_blocks = build_appendix(cards, len(selected))

    write_txt(main_blocks, DOCS / "AAVS_Literature_Review_Main.txt")
    write_txt(appendix_blocks, ARCHIVE / "AAVS_Literature_Review_Appendix.txt")
    combined = main_blocks + ["", ""] + appendix_blocks
    write_txt(combined, ARCHIVE / "AAVS_Literature_Review_GoogleDoc.txt")
    write_docx(combined, ARCHIVE / "AAVS_Literature_Review_GoogleDoc.docx")
    write_docx(main_blocks, DOCS / "AAVS_Literature_Review_Main.docx")
    write_docx(appendix_blocks, ARCHIVE / "AAVS_Literature_Review_Appendix.docx")
    print(f"selected detailed papers: {len(selected)}")


if __name__ == "__main__":
    main()
