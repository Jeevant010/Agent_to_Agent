#!/usr/bin/env python3
"""AAVS literature harvester.

Builds a reproducible, deduplicated corpus of papers relevant to
Autonomous Adversarial Verifier Synthesis (AAVS):

  * harvest  - query arXiv + Crossref, score relevance, dedupe, write corpus
  * download - fetch open-access PDFs (arXiv first), verify magic bytes
  * extract  - convert PDFs to text with pdftotext
  * status   - print corpus / download statistics

The script is deliberately dependency-light (requests + stdlib) and caches every
query so re-runs do not hammer public APIs.

Usage:
    python scripts/literature_harvester.py harvest --target 1500
    python scripts/literature_harvester.py download --limit 1500
    python scripts/literature_harvester.py extract
    python scripts/literature_harvester.py status
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import requests

ROOT = Path(__file__).resolve().parents[2]
PAPERS = ROOT / "papers"
PDF_DIR = PAPERS / "pdf"
TEXT_DIR = PAPERS / "text"
META_DIR = PAPERS / "metadata"
CACHE_DIR = META_DIR / "query_cache"
CORPUS_PATH = META_DIR / "papers_corpus.jsonl"
RAW_PATH = META_DIR / "papers_raw.jsonl"
MANIFEST_PATH = META_DIR / "download_manifest.jsonl"
LOG_PATH = META_DIR / "harvest_log.json"

for d in (PDF_DIR, TEXT_DIR, META_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)

USER_AGENT = (
    "AAVS-Literature-Harvester/1.0 "
    "(academic literature survey; contact: github.com/Jeevant010/Agent_to_Agent)"
)
ARXIV_API = "https://export.arxiv.org/api/query"
CROSSREF_API = "https://api.crossref.org/works"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

# --------------------------------------------------------------------------- #
# Taxonomy
# --------------------------------------------------------------------------- #

CLUSTERS = {
    "C1": {
        "name": "Benchmark test inadequacy & false passes",
        "short": "benchmark-inadequacy",
        "keywords": {
            "swe-bench": 6.0, "swebench": 6.0, "test inadequacy": 6.0,
            "test adequacy": 5.0, "test suite quality": 5.0, "test effectiveness": 4.0,
            "false positive": 3.0, "false pass": 4.0, "benchmark": 1.5,
            "unit test": 2.5, "mutation testing": 2.5, "coverage": 1.5,
            "flaky test": 3.0, "test oracle": 3.0, "benchmark contamination": 5.0,
            "data contamination": 3.5, "patch correctness": 5.0, "overfitting": 2.0,
            "humaneval": 3.5, "mbpp": 3.5, "livecodebench": 3.5, "bigcodebench": 3.5,
            "test coverage": 2.5, "assertion": 2.0, "benchmark validity": 5.0,
            "benchmark audit": 5.0, "evaluation validity": 4.0,
        },
    },
    "C2": {
        "name": "Vulnerability regression & secure AI code",
        "short": "vulnerability-regression",
        "keywords": {
            "vulnerability regression": 6.0, "vulnerability": 3.0, "cwe": 5.0,
            "secure code": 5.0, "insecure code": 5.0, "security": 2.0,
            "llm-generated code": 4.0, "ai-generated code": 4.0, "security patch": 5.0,
            "automated program repair": 2.5, "sast": 3.0, "codeql": 3.0,
            "vulnerability detection": 4.0, "exploit": 2.0, "code security": 4.5,
            "security vulnerability": 5.0, "memory safety": 3.0, "cwe-": 3.0,
        },
    },
    "C3": {
        "name": "Reward hacking & specification gaming",
        "short": "reward-hacking",
        "keywords": {
            "reward hacking": 7.0, "reward hack": 7.0, "specification gaming": 7.0,
            "reward gaming": 6.0, "verifiable reward": 5.5, "rlvr": 5.5,
            "test tampering": 7.0, "test hacking": 7.0, "benchmark gaming": 6.0,
            "sandbox": 2.0, "terminal": 2.0, "agent benchmark": 3.5,
            "cheating": 4.0, "shortcut": 2.0, "goodhart": 4.5, "reward model": 2.0,
            "exploit trajectory": 6.0, "environment hacking": 6.0,
            "reward overoptimization": 6.0, "state spoofing": 6.0,
            "policy gaming": 5.0,
        },
    },
    "C4": {
        "name": "Test/verifier synthesis & execution feedback",
        "short": "verifier-synthesis",
        "keywords": {
            "test generation": 5.0, "test synthesis": 5.0, "assertion generation": 5.0,
            "test oracle": 4.0, "property-based testing": 4.0, "fuzzing": 3.0,
            "mutation testing": 4.0, "test augmentation": 4.0, "verifier": 3.0,
            "execution feedback": 4.0, "self-debug": 3.5, "self-repair": 3.5,
            "differential testing": 4.0, "metamorphic testing": 4.0, "invariant": 2.0,
            "coverage-guided": 3.0, "code generation": 2.0, "program repair": 2.0,
            "test case generation": 4.5, "oracle generation": 5.0,
            "verifier synthesis": 6.0, "execution-based": 3.5,
        },
    },
    "C5": {
        "name": "Coding agents & repository benchmarks",
        "short": "coding-agents",
        "keywords": {
            "swe-bench": 6.0, "swe-agent": 6.0, "agentless": 5.0, "openhands": 5.0,
            "coding agent": 6.0, "software engineering agent": 6.0,
            "repository-level": 4.5, "issue resolution": 4.5, "autonomous agent": 2.0,
            "code generation": 2.0, "benchmark": 2.0, "long-horizon": 2.5,
            "tool use": 2.0, "computer use": 2.5, "terminal-bench": 5.0,
            "deepswe": 6.0, "multi-swe-bench": 5.0, "software engineering": 2.0,
            "agent": 1.5, "bug fixing": 4.0, "issue resolving": 4.5,
        },
    },
    "C6": {
        "name": "Mutation testing & oracle foundations",
        "short": "mutation-foundations",
        "keywords": {
            "mutation testing": 5.0, "equivalent mutant": 7.0, "coupling effect": 6.0,
            "mutation analysis": 4.5, "mutant": 3.0, "mutation score": 4.0,
            "higher-order mutation": 5.0, "test oracle": 3.0,
            "metamorphic testing": 4.0, "invariant detection": 4.0, "daikon": 5.0,
            "fault-based": 3.0, "test effectiveness": 4.0, "mutation operator": 4.0,
            "oracle problem": 5.0, "test selection": 3.0,
        },
    },
    "C7": {
        "name": "RL, verifiers & reward models",
        "short": "rl-verifiers",
        "keywords": {
            "reinforcement learning": 2.0, "verifiable reward": 5.5, "process reward": 4.0,
            "reward model": 4.0, "rlhf": 2.0, "grpo": 4.0, "self-play": 3.0,
            "verifier": 3.0, "test-time": 2.0, "execution-guided": 4.0,
            "code generation": 2.0, "reasoning": 1.5, "outcome reward": 4.5,
            "policy optimization": 2.0, "reward signal": 3.0,
        },
    },
    "C8": {
        "name": "Automated repair & patch correctness",
        "short": "repair-correctness",
        "keywords": {
            "automated program repair": 5.0, "program repair": 4.0,
            "patch correctness": 6.0, "overfitting": 3.0, "fault localization": 4.0,
            "regression testing": 4.0, "program synthesis": 2.0, "repair": 2.0,
            "test-based": 3.0, "plausible patch": 5.0, "correct patch": 5.0,
            "bug fix": 3.0, "defect": 2.0,
        },
    },
    "C9": {
        "name": "Evaluation methodology & contamination",
        "short": "evaluation-methodology",
        "keywords": {
            "evaluation": 2.0, "benchmark": 2.0, "data contamination": 5.0,
            "benchmark leakage": 5.0, "construct validity": 5.0, "reproducibility": 3.0,
            "leaderboard": 4.0, "measurement": 2.0, "llm evaluation": 4.0,
            "benchmark design": 4.0, "evaluation framework": 3.0, "meta-evaluation": 5.0,
        },
    },
    "C10": {
        "name": "Sandbox, container & state integrity",
        "short": "sandbox-integrity",
        "keywords": {
            "container": 3.0, "sandbox": 3.0, "filesystem": 3.0, "integrity": 3.0,
            "tamper": 4.0, "trusted execution": 4.0, "state verification": 5.0,
            "checksum": 3.0, "read-only": 2.0, "isolation": 3.0,
            "state spoofing": 6.0, "environment verification": 5.0, "docker": 2.5,
        },
    },
}

MACRO_TERMS = (
    "code", "program", "test", "agent", "benchmark", "software", "verif", "repair",
    "bug", "repository", "llm", "language model", "mutation", "reward", "patch",
    "agentic", "swe", "evaluation", "developer", "compiler",
)

# A title hit on one of these is a strong signal that the paper belongs in the
# corpus even when the abstract is missing (common for Crossref records).
CORE_TITLE_PHRASES = (
    "swe-bench", "swebench", "swe-agent", "swe-smith", "swe-gym", "swe-bench+",
    "terminal-bench", "deepswe", "multi-swe-bench", "reward hack",
    "specification gaming", "test oracle", "mutation testing", "test adequacy",
    "test generation", "test synthesis", "assertion generation",
    "program repair", "patch correctness", "verifier synthesis", "test augmentation",
    "coding agent", "software engineering agent", "agentless", "openhands",
    "humaneval", "mbpp", "livecodebench", "bigcodebench", "metamorphic testing",
    "equivalent mutant", "coupling effect", "flaky test", "vulnerability regression",
    "secure code generation", "verifiable reward", "rlvr", "process reward model",
    "reward model", "execution feedback", "self-debug", "self-repair",
    "differential testing", "property-based testing", "coverage-guided",
    "fault localization", "regression testing", "data contamination",
    "benchmark contamination", "benchmark strengthening", "test inadequacy",
)

# "code" / "software" etc. are too weak on their own for the floor rule:
# biology papers say "test" constantly. These are the strong software signals.
STRONG_MACRO_TERMS = (
    "code", "program", "software", "llm", "language model", "agent", "benchmark",
    "repository", "compiler", "developer", "swe", "api", "python", "java",
    "typescript", "pytest", "source code", "pull request", "github",
)

OFFTOPIC_TERMS = {
    "phishing": 30, "malware": 25, "intrusion detection": 30, "spam detection": 25,
    "android malware": 30, "sentiment analysis": 20, "recommendation system": 20,
    "social network": 15, "medical": 20, "clinical": 25, "protein": 25,
    "gene expression": 30, "cancer": 25, "molecule": 20, "drug discovery": 25,
    "autonomous driving": 25, "remote sensing": 25, "power grid": 25,
    "speech recognition": 20, "image classification": 15, "chatbot": 10,
    "question answering": 8, "knowledge graph": 10, "federated learning": 15,
    "blockchain": 15, "smart contract": 12, "iot": 15, "wireless": 20,
}

# Title-level domain filters. These deliberately use word boundaries and are
# applied to the title only: abstracts often mention ML domains incidentally.
DOMAIN_TITLE_PATTERNS = [
    (r"\bmolecul", 38), (r"\bchemistr", 38), (r"\bcancer\b", 40),
    (r"\bprotein", 38), (r"\bgene\b|\bgenes\b|\bgenomic", 38),
    (r"\bdrug discovery\b", 40), (r"\bmaterials discovery\b", 40),
    (r"\bmedical\b", 35), (r"\bclinical\b", 35),
    (r"\bspatial transcriptomic", 45), (r"\bmarket[- ]stress\b", 45),
    (r"\bfinancial market", 40), (r"\bmachine translation\b", 35),
    (r"\bgraph neural\b", 40), (r"\bgnn\b", 40),
    (r"\bsmart contract", 30), (r"\bblockchain\b", 30), (r"\bdefi\b", 30),
    (r"\benergy consumption\b", 40), (r"\bdebloat", 40),
    (r"\bremote sensing\b", 40), (r"\bautonomous driving\b", 40),
    (r"\bwireless\b", 35), (r"\biot\b", 35), (r"\brobot", 35),
    (r"\bvision[- ]language[- ]action", 40), (r"\bembodied", 25),
    (r"\brubric", 35), (r"\binstruction following\b", 35),
    (r"\blong[- ]form qa\b", 40), (r"\bquestion answering\b", 20),
    (r"\brecommend(er|ation) system", 30), (r"\bsentiment analysis\b", 30),
    (r"\bquantum circuit", 30), (r"\bllm safety\b", 30),
    (r"\bimage classification\b", 30), (r"\bspeech recognition\b", 30),
    (r"\bsignature scheme\b", 40), (r"\bcryptograph", 35),
    (r"\bzero[- ]knowledge\b", 35), (r"\bencryption\b", 30),
    (r"\bcad\b", 35), (r"\b3d\b", 22), (r"\baudio\b", 30),
    (r"\bvideo\b", 22), (r"\bimage\b", 22), (r"\bspeech\b", 30),
    (r"\brag\b", 18), (r"\bretrieval[- ]augmented\b", 20),
    (r"\bmemory retrieval\b", 25), (r"\bcitation", 20),
    (r"\bnli\b", 30), (r"\bnatural language inference\b", 30),
    (r"\bbandit\b", 22),
    (r"\bdesignated[- ]verifier\b", 40), (r"\bsignature\b", 25),
    (r"\bquantum\b", 25), (r"\bnon[- ]malleable\b", 40),
    (r"\bextractor", 25), (r"\bdiffusion model", 30),
    (r"\bmultimodal\b", 20), (r"\bfraud\b", 30),
    (r"\badversarial patch\b", 40), (r"\baerial detection\b", 40),
    (r"\bimagenet\b", 40), (r"\bfinancial\b", 30), (r"\bfomc\b", 40),
    (r"\bomics\b", 40), (r"\blabosbench\b", 40),
    (r"\binstrument control\b", 35), (r"\bmllm\b", 30),
    (r"\bperception\b", 20), (r"\bsim[- ]to[- ]real\b", 30),
    (r"\bdocker compose\b", 35), (r"\bcontainer startup\b", 40),
    (r"\bmobile agents?\b", 30), (r"\belectric utilit", 35),
    (r"\bhuman-agent collaboration\b", 20),
]

# Titles that are foundational for AAVS. They get a relevance floor so the
# corpus cannot accidentally drop the canon due to sparse abstracts.
SEED_FRAGMENTS = [
    "swe-bench: can language models resolve",
    "swe-bench verified",
    "swe-agent: agent-computer interfaces",
    "agentless: demystifying",
    "openhands",
    "are mutants a valid substitute",
    "mutation testing advances",
    "the oracle problem in software testing",
    "coverage is not strongly correlated",
    "defects4j",
    "pynguin",
    "randoop",
    "dynamically discovering likely program invariants",
    "metamorphic testing: a new approach",
    "codamosa",
    "coverup",
    "codet: code generation with generated tests",
    "lever: learning to verify",
    "demystifying gpt self-repair",
    "competition-level code generation with alphacode",
    "evalplus",
    "is your code generated by llms really correct",
    "training verifiers to solve math word problems",
    "deepseek-r1",
    "coderl",
    "reflexion",
    "intercode",
    "osworld",
    "appworld",
    "terminal-bench",
    "terminal wrench",
    "hack-verifiable terminal bench",
    "probe to generate",
    "utboost",
    "beyond bypass",
    "repairbench",
    "chatunittest",
    "testpilot",
    "autocodeRover",
    "mutap",
    "humaneval",
    "mbpp",
    "livecodebench",
    "bigcodebench",
    "ds-1000",
    "cruxeval",
    "repoBench",
    "crosscodeeval",
    "repocoder",
    "multi-swe-bench",
    "swe-bench multilingual",
    "deepswe",
    "reward hacking",
    "specification gaming",
    "goodhart",
    "measuring coding agents",
    "benchmarking coding agents",
    "large language models for software engineering",
    "test-driven development",
    "self-debugging",
    "teaching large language models to self-debug",
    "program repair with large language models",
    "an empirical study of flaky tests",
    "assertion generation",
    "automated unit test generation",
    "mutation testing for llm",
    "llm4test",
    "testeval",
    "sec-code",
    "securecode",
    "baxbench",
    "seccodeplt",
    "cybench",
    "toolbench",
    "theagentcompany",
    "scienceagentbench",
    "mlagentbench",
    "gaia",
    "webarena",
    "mind2web",
    "swe-bench+",
    "swe-bench-java",
    "swesmith",
    "nemotron",
    "swe-rebench",
    "codeforces",
    "process reward model",
    "outcome reward model",
    "reward model overoptimization",
]

# Canonical papers that must be present even if no lexical query surfaces
# them. IDs and DOIs were verified against live arXiv/Crossref metadata.
GUARANTEED_ARXIV_IDS = [
    "2310.06770",  # SWE-bench
    "2305.01210",  # EvalPlus
    "2207.10397",  # CodeT
    "2302.08468",  # LEVER
    "2304.05128",  # Self-Debug
    "2303.11366",  # Reflexion
    "2203.07814",  # AlphaCode
    "2306.14898",  # InterCode
    "2404.07972",  # OSWorld
    "2407.18901",  # AppWorld
    "2403.07974",  # LiveCodeBench
    "2406.15877",  # BigCodeBench
    "2211.11501",  # DS-1000
    "2401.03065",  # CRUXEval
    "2306.03091",  # RepoBench
    "2310.11248",  # CrossCodeEval
    "2303.12570",  # RepoCoder
    "2407.01489",  # Agentless
    "2405.15793",  # SWE-agent
    "2407.16741",  # OpenHands
    "2504.21798",  # SWE-smith
    "2504.02605",  # Multi-SWE-bench
]

GUARANTEED_DOIS = [
    "10.1145/2635868.2635929",       # Are mutants a valid substitute for real faults?
    "10.1109/tse.2014.2372785",      # The oracle problem in software testing
    "10.1145/2568225.2568271",       # Coverage is not strongly correlated...
    "10.1145/2786805.2786858",       # Assertions are strongly correlated...
    "10.1145/2610384.2628055",       # Defects4J
    "10.1109/icse-companion55297.2022.9793730",  # Pynguin
    "10.1016/bs.adcom.2018.03.015",  # Mutation Testing Advances
    "10.1109/tse.2010.62",           # Development of mutation testing survey
    "10.1007/s10664-022-10248-w",    # Empirical study of Python test generation
]

SEED_TITLES_VERIFIED = {
    "2604.01518": {
        "actual_title": "Probe to Generate: Program Variant-Guided Test Augmentation for Repository-Level Repair Benchmarks",
        "doc_title": "Are Benchmark Tests Strong Enough? Investigating Test Inadequacy in SWE-bench",
    },
    "2506.09289": {
        "actual_title": "UTBoost: Rigorous Evaluation of Coding Agents on SWE-Bench",
        "doc_title": "UTBoost: Augmenting Unit Tests for AI Coding Benchmarks via Intramorphic Oracle Filtering",
    },
    "2604.17596": {
        "actual_title": "Terminal Wrench: A Dataset of 331 Reward-Hackable Environments and 3,632 Exploit Trajectories",
        "doc_title": "Terminal Wrench: Exposing Reward Hacking and Environmental Blind Spots in OS Agents",
    },
    "2608.22103": {
        "actual_title": "Hack-Verifiable Terminal Bench: Evaluating Reward Hacking in Terminal Tasks",
        "doc_title": "Hack-Verifiable Terminal Bench: Defending Against State Spoofing in System Agents",
    },
}

# --------------------------------------------------------------------------- #
# Query plan
# --------------------------------------------------------------------------- #

# (cluster, query). Queries are plain terms; arXiv ANDs them, Crossref uses
# bibliographic relevance. Adding a query is the intended extension point.
QUERIES = [
    # C1 benchmark inadequacy / test adequacy
    ("C1", "swe-bench test"),
    ("C1", "swe-bench evaluation"),
    ("C1", "software engineering benchmark test suite"),
    ("C1", "coding benchmark test adequacy"),
    ("C1", "unit test benchmark large language model"),
    ("C1", "code generation benchmark false positive"),
    ("C1", "test oracle large language model"),
    ("C1", "test coverage fault detection"),
    ("C1", "flaky tests benchmark"),
    ("C1", "data contamination code generation"),
    ("C1", "benchmark contamination large language model"),
    ("C1", "patch correctness benchmark"),
    ("C1", "overfitting code generation benchmark"),
    ("C1", "humaneval test correctness"),
    ("C1", "mbpp test correctness"),
    ("C1", "leaderboard code generation evaluation"),
    ("C1", "test suite effectiveness coverage"),
    # C2 vulnerability regression
    ("C2", "vulnerability regression llm code"),
    ("C2", "vulnerability llm-generated code"),
    ("C2", "secure code generation large language model"),
    ("C2", "security automated program repair"),
    ("C2", "cwe code generation"),
    ("C2", "insecure code large language model"),
    ("C2", "security patch evaluation"),
    ("C2", "vulnerability detection deep learning"),
    ("C2", "ai-generated code security"),
    ("C2", "memory safety llm code"),
    ("C2", "secure code benchmark"),
    # C3 reward hacking
    ("C3", "reward hacking language model"),
    ("C3", "reward hacking agent"),
    ("C3", "specification gaming"),
    ("C3", "verifiable rewards reinforcement learning"),
    ("C3", "rlvr language model"),
    ("C3", "reward hacking coding agent"),
    ("C3", "test tampering agent"),
    ("C3", "sandbox agent benchmark"),
    ("C3", "terminal agent benchmark"),
    ("C3", "computer use agent benchmark"),
    ("C3", "shortcut learning code generation"),
    ("C3", "goodhart benchmark language model"),
    ("C3", "reward model overoptimization"),
    ("C3", "environment exploitation agent"),
    ("C3", "benchmark gaming llm"),
    ("C3", "state spoofing agent"),
    # C4 test and verifier synthesis
    ("C4", "test generation large language model"),
    ("C4", "test synthesis code"),
    ("C4", "assertion generation"),
    ("C4", "property-based testing large language model"),
    ("C4", "fuzzing large language model"),
    ("C4", "mutation testing large language model"),
    ("C4", "test augmentation code generation"),
    ("C4", "verifier code generation"),
    ("C4", "execution feedback code generation"),
    ("C4", "self-debugging code generation"),
    ("C4", "self-repair code generation"),
    ("C4", "differential testing code"),
    ("C4", "metamorphic testing large language model"),
    ("C4", "invariant generation code"),
    ("C4", "coverage-guided test generation"),
    ("C4", "oracle generation testing"),
    ("C4", "verifier synthesis"),
    ("C4", "execution-based code evaluation"),
    ("C4", "test case generation ai"),
    # C5 agents and repository benchmarks
    ("C5", "swe-agent"),
    ("C5", "coding agent software engineering"),
    ("C5", "software engineering agent benchmark"),
    ("C5", "repository-level code generation"),
    ("C5", "issue resolution language model"),
    ("C5", "autonomous software engineering agent"),
    ("C5", "swe-bench agent"),
    ("C5", "multi-swe-bench"),
    ("C5", "deepswe"),
    ("C5", "terminal-bench"),
    ("C5", "long-horizon agent benchmark"),
    ("C5", "tool use benchmark agent"),
    ("C5", "bug fixing large language model"),
    ("C5", "openhands agent"),
    ("C5", "agentless software engineering"),
    # C6 mutation and oracle foundations
    ("C6", "mutation testing"),
    ("C6", "mutation testing survey"),
    ("C6", "equivalent mutant"),
    ("C6", "coupling effect mutation"),
    ("C6", "mutation analysis software"),
    ("C6", "higher-order mutation"),
    ("C6", "mutation score test suite"),
    ("C6", "test oracle problem"),
    ("C6", "metamorphic testing"),
    ("C6", "dynamic invariant detection"),
    ("C6", "fault-based testing"),
    ("C6", "mutation operator"),
    ("C6", "test effectiveness mutation"),
    # C7 RL and verifiers
    ("C7", "reinforcement learning verifiable reward"),
    ("C7", "process reward model code"),
    ("C7", "verifier code generation"),
    ("C7", "reward model code generation"),
    ("C7", "grpo code generation"),
    ("C7", "self-play code verification"),
    ("C7", "execution guided reinforcement learning code"),
    ("C7", "outcome reward code"),
    # C8 repair and correctness
    ("C8", "automated program repair large language model"),
    ("C8", "patch correctness automated repair"),
    ("C8", "overfitting automated program repair"),
    ("C8", "test-based program repair"),
    ("C8", "fault localization large language model"),
    ("C8", "regression testing large language model"),
    ("C8", "plausible patch correctness"),
    # C9 evaluation methodology
    ("C9", "benchmark validity large language model"),
    ("C9", "data contamination large language model"),
    ("C9", "benchmark leakage evaluation"),
    ("C9", "construct validity ai evaluation"),
    ("C9", "reproducibility machine learning benchmark"),
    ("C9", "meta-evaluation benchmark llm"),
    ("C9", "leaderboard reliability"),
    # C10 sandbox / integrity
    ("C10", "sandbox isolation agent"),
    ("C10", "container security verification"),
    ("C10", "filesystem integrity verification"),
    ("C10", "tamper evident execution"),
    ("C10", "trusted execution environment agent"),
    ("C10", "state verification benchmark"),
    ("C10", "docker reproducibility evaluation"),
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def norm_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def title_key(title: str) -> str:
    t = norm_title(title)
    return hashlib.sha1(t[:120].encode("utf-8")).hexdigest()


def norm_arxiv_id(raw: str | None) -> str:
    if not raw:
        return ""
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", raw)
    if m:
        return m.group(1)
    m = re.search(r"([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?", raw)
    if m:
        return m.group(1)
    return ""


def norm_doi(raw: str | None) -> str:
    if not raw:
        return ""
    d = raw.lower().strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d


def year_from(value: str) -> int:
    m = re.search(r"(19|20)\d{2}", value or "")
    return int(m.group(0)) if m else 0


def safe_filename(stem: str, max_len: int = 120) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_")
    return s[:max_len] or "paper"


class RateLimiter:
    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            delta = now - self._last
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
            self._last = time.monotonic()


def get_json_cached(url: str, params: dict, cache_key: str, limiter: RateLimiter,
                    timeout: int = 60, retries: int = 4) -> dict | None:
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except json.JSONDecodeError:
            cache_file.unlink(missing_ok=True)
    for attempt in range(retries):
        limiter.wait()
        try:
            r = requests.get(url, params=params, timeout=timeout,
                             headers={"User-Agent": USER_AGENT})
            if r.status_code == 200:
                data = r.json()
                cache_file.write_text(json.dumps(data))
                return data
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt + 1)
                continue
            return None
        except (requests.RequestException, ValueError):
            time.sleep(2 ** attempt + 1)
    return None


def get_text_cached(url: str, params: dict, cache_key: str, limiter: RateLimiter,
                    timeout: int = 60, retries: int = 4) -> str | None:
    cache_file = CACHE_DIR / f"{cache_key}.xml"
    if cache_file.exists():
        return cache_file.read_text()
    for attempt in range(retries):
        limiter.wait()
        try:
            r = requests.get(url, params=params, timeout=timeout,
                             headers={"User-Agent": USER_AGENT})
            if r.status_code == 200:
                cache_file.write_text(r.text)
                return r.text
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(3 * (attempt + 1))
                continue
            return None
        except requests.RequestException:
            time.sleep(3 * (attempt + 1))
    return None


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #

def parse_arxiv_xml(xml_text: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    out = []
    for entry in root.findall(f"{ATOM}entry"):
        raw_id = entry.findtext(f"{ATOM}id") or ""
        aid = norm_arxiv_id(raw_id)
        title = clean_text(entry.findtext(f"{ATOM}title"))
        if not title or not aid:
            continue
        summary = clean_text(entry.findtext(f"{ATOM}summary"))
        published = entry.findtext(f"{ATOM}published") or ""
        authors = [clean_text(a.findtext(f"{ATOM}name"))
                   for a in entry.findall(f"{ATOM}author")]
        journal_ref = clean_text(entry.findtext(f"{ARXIV_NS}journal_ref"))
        comment = clean_text(entry.findtext(f"{ARXIV_NS}comment"))
        category = ""
        prim = entry.find(f"{ARXIV_NS}primary_category")
        if prim is not None:
            category = prim.attrib.get("term", "")
        out.append({
            "source": "arxiv",
            "arxiv_id": aid,
            "doi": norm_doi(entry.findtext(f"{ARXIV_NS}doi")),
            "title": title,
            "abstract": summary,
            "authors": [a for a in authors if a],
            "year": year_from(published),
            "venue": journal_ref or "arXiv",
            "venue_detail": comment,
            "category": category,
            "url": f"https://arxiv.org/abs/{aid}",
            "pdf_url": f"https://arxiv.org/pdf/{aid}",
            "citations": None,
        })
    return out


def fetch_arxiv(query: str, limit: int = 100) -> list[dict]:
    limiter = RateLimiter(3.1)
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    key = "arxiv_" + hashlib.md5((query + str(limit)).encode()).hexdigest()
    xml_text = get_text_cached(ARXIV_API, params, key, limiter)
    return parse_arxiv_xml(xml_text) if xml_text else []


def fetch_arxiv_ids(ids: list[str]) -> list[dict]:
    limiter = RateLimiter(3.1)
    params = {"id_list": ",".join(ids), "max_results": len(ids)}
    key = "arxiv_ids_" + hashlib.md5(",".join(ids).encode()).hexdigest()
    xml_text = get_text_cached(ARXIV_API, params, key, limiter)
    return parse_arxiv_xml(xml_text) if xml_text else []


def parse_crossref_item(it: dict) -> dict | None:
    title = clean_text((it.get("title") or [""])[0])
    if not title:
        return None
    doi = norm_doi(it.get("DOI"))
    issued = it.get("issued", {}).get("date-parts", [[0]])
    year = issued[0][0] if issued and issued[0] else 0
    authors = []
    for a in it.get("author", []) or []:
        name = " ".join(x for x in [a.get("given"), a.get("family")] if x)
        if name:
            authors.append(name)
    venue = clean_text((it.get("container-title") or [""])[0])
    abstract = clean_text(it.get("abstract", ""))
    links = it.get("link", []) or []
    pdf_url = ""
    for link in links:
        if "pdf" in (link.get("content-type", "") or "").lower():
            pdf_url = link.get("URL", "")
            break
    return {
        "source": "crossref",
        "arxiv_id": "",
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "year": year,
        "venue": venue or it.get("publisher", ""),
        "venue_detail": it.get("type", ""),
        "category": it.get("type", ""),
        "url": it.get("URL") or (f"https://doi.org/{doi}" if doi else ""),
        "pdf_url": pdf_url,
        "citations": it.get("is-referenced-by-count"),
    }


def fetch_crossref(query: str, rows: int = 60) -> list[dict]:
    limiter = RateLimiter(1.0)
    params = {
        "query.bibliographic": query,
        "rows": rows,
        "filter": "from-pub-date:2010-01-01",
        "select": ("DOI,title,author,issued,container-title,abstract,"
                   "is-referenced-by-count,URL,link,type,event,publisher"),
    }
    key = "crossref_" + hashlib.md5((query + str(rows)).encode()).hexdigest()
    data = get_json_cached(CROSSREF_API, params, key, limiter)
    if not data:
        return []
    out = []
    for it in data.get("message", {}).get("items", []):
        rec = parse_crossref_item(it)
        if rec:
            out.append(rec)
    return out


def fetch_crossref_doi(doi: str) -> dict | None:
    limiter = RateLimiter(1.0)
    url = f"{CROSSREF_API}/{doi}"
    key = "crossref_doi_" + hashlib.md5(doi.encode()).hexdigest()
    data = get_json_cached(url, {}, key, limiter)
    if not data:
        return None
    return parse_crossref_item(data.get("message", {}))


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #

def tier_for(score: float) -> str:
    """Single source of truth for relevance tiers."""
    if score >= 95:
        return "A"
    if score >= 85:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def score_record(rec: dict) -> dict:
    title = rec.get("title", "")
    abstract = rec.get("abstract", "")
    hay_title = " " + norm_title(title) + " "
    hay_abs = " " + norm_title(abstract) + " "

    cluster_scores = {}
    matched = {}
    for cid, spec in CLUSTERS.items():
        ts = 0.0
        ms = []
        for phrase, weight in spec["keywords"].items():
            if not weight or ":" in phrase:
                continue
            # Match against the same normalized space-separated form used for
            # titles; otherwise hyphenated keys ("swe-bench", "self-debug")
            # can never fire.
            p = norm_title(phrase)
            if not p:
                continue
            # Cap repetition: a paper saying "benchmark" 40 times is not 40x
            # more relevant, and generic terms were stealing cluster assignment.
            t_hits = min(hay_title.count(p), 2)
            a_hits = min(hay_abs.count(p), 3)
            if t_hits or a_hits:
                ts += weight * (4.5 * t_hits + 1.0 * a_hits)
                ms.append(phrase)
        if ts > 0:
            cluster_scores[cid] = round(ts, 2)
            matched[cid] = ms

    if not cluster_scores:
        rec.update({"score": 0.0, "cluster": "", "clusters": [], "matched_terms": [],
                    "tier": "D", "reject_reason": "no_taxonomy_match", "seed": False})
        return rec

    best_cid = max(cluster_scores, key=cluster_scores.get)
    raw = cluster_scores[best_cid]

    # Secondary clusters (for multi-label browsing).
    ranked = sorted(cluster_scores.items(), key=lambda kv: kv[1], reverse=True)
    top_clusters = [c for c, s in ranked[:3] if s >= max(4.0, 0.35 * raw)]

    combined = (title + " " + abstract).lower()
    title_lower = title.lower()
    has_macro = any(term in combined for term in MACRO_TERMS)
    title_has_strong = any(t in hay_title for t in STRONG_MACRO_TERMS)
    core_title = any(norm_title(p) in hay_title for p in CORE_TITLE_PHRASES)

    penalty = 0
    hits_off = [t for t in OFFTOPIC_TERMS if t in combined]
    if hits_off:
        penalty = max(OFFTOPIC_TERMS[t] for t in hits_off)

    # Domain filters are title-only so abstracts can mention ML domains
    # incidentally without nuking a software-engineering paper.
    domain_hits = [pat for pat, _ in DOMAIN_TITLE_PATTERNS
                   if re.search(pat, title_lower)]
    for pat, weight in DOMAIN_TITLE_PATTERNS:
        if re.search(pat, title_lower):
            penalty += weight
    if len(domain_hits) >= 2:
        penalty += 15

    # Generic C9/C10 records are the main precision leak: a paper about graph
    # benchmarks or container energy use is not about software verifiers.
    if best_cid == "C9" and not title_has_strong and not core_title:
        penalty += 35
    if best_cid == "C10" and not title_has_strong and not any(
            k in hay_title for k in
            ("sandbox", "container", "filesystem", "state", "tamper",
             "integrity", "isolat", "verif")):
        penalty += 25

    score = 18.0 + min(raw, 55.0) * 1.35
    year = rec.get("year") or 0
    if year >= 2023:
        score += 5
    elif year >= 2020:
        score += 3
    elif year and year < 2010:
        score -= 5

    cites = rec.get("citations")
    if isinstance(cites, int) and cites > 0:
        score += min(8.0, 2.2 * math.log10(1 + cites))

    if not has_macro:
        score -= 35
        penalty += 10
    if penalty:
        score -= penalty

    strong_macro = any(t in combined for t in STRONG_MACRO_TERMS)
    if core_title and strong_macro and penalty < 25:
        score = max(score, 88.0)

    # Benchmark-audit language is a core AAVS signal even when the exact
    # canonical phrase is absent.
    if penalty < 30 and "benchmark" in hay_title and any(
            w in hay_title for w in
            ("adversarial", "inflated", "contamination", "gaming", "test based",
             "test suite", "verifier", "reward")):
        score = max(score, 80.0)

    seed = any(norm_title(frag) in norm_title(title) for frag in SEED_FRAGMENTS)
    if seed and penalty < 25:
        score = max(score, 88.0)

    score = round(max(0.0, min(99.0, score)), 1)
    tier = tier_for(score)

    rec.update({
        "score": score,
        "cluster": best_cid,
        "cluster_name": CLUSTERS[best_cid]["name"],
        "clusters": top_clusters,
        "cluster_scores": {k: round(v, 2) for k, v in ranked[:5]},
        "matched_terms": matched.get(best_cid, [])[:12],
        "tier": tier,
        "seed": seed,
        "offtopic_terms": hits_off,
    })
    return rec


# --------------------------------------------------------------------------- #
# Harvest
# --------------------------------------------------------------------------- #

def merge_records(a: dict, b: dict) -> dict:
    """Merge duplicate records, preferring richer metadata."""
    base = dict(a)
    for key in ("arxiv_id", "doi", "abstract", "venue", "pdf_url", "url"):
        if not base.get(key) and b.get(key):
            base[key] = b[key]
    if len(b.get("abstract", "")) > len(base.get("abstract", "")):
        base["abstract"] = b["abstract"]
    if len(b.get("authors", [])) > len(base.get("authors", [])):
        base["authors"] = b["authors"]
    if not base.get("year") and b.get("year"):
        base["year"] = b["year"]
    if (b.get("citations") or 0) > (base.get("citations") or 0):
        base["citations"] = b["citations"]
    sources = set(base.get("sources", [base.get("source", "")]))
    sources.add(b.get("source", ""))
    base["sources"] = sorted(s for s in sources if s)
    base["source"] = base.get("source") or b.get("source", "")
    base["score"] = max(base.get("score", 0), b.get("score", 0))
    if b.get("seed"):
        base["seed"] = True
    if base.get("tier") == "D" and b.get("tier") != "D":
        for k in ("tier", "cluster", "cluster_name", "clusters", "cluster_scores",
                  "matched_terms", "score"):
            base[k] = b.get(k)
    return base


def dedupe(records: list[dict]) -> list[dict]:
    by_arxiv: dict[str, dict] = {}
    by_doi: dict[str, dict] = {}
    by_title: dict[str, dict] = {}
    merged: list[dict] = []

    def register(rec):
        keys = []
        if rec.get("arxiv_id"):
            keys.append(("arxiv", rec["arxiv_id"]))
        if rec.get("doi"):
            keys.append(("doi", rec["doi"]))
        keys.append(("title", title_key(rec.get("title", ""))))
        existing = None
        for kind, key in keys:
            if kind == "arxiv" and key in by_arxiv:
                existing = by_arxiv[key]
                break
            if kind == "doi" and key in by_doi:
                existing = by_doi[key]
                break
            if kind == "title" and key in by_title:
                existing = by_title[key]
                break
        if existing is not None:
            updated = merge_records(existing, rec)
            existing.clear()
            existing.update(updated)
            target = existing
        else:
            merged.append(rec)
            target = rec
        if target.get("arxiv_id"):
            by_arxiv[target["arxiv_id"]] = target
        if target.get("doi"):
            by_doi[target["doi"]] = target
        by_title[title_key(target.get("title", ""))] = target

    for rec in records:
        register(rec)
    return merged


STATUS_FIELDS = (
    "pdf_status", "pdf_path", "pdf_bytes", "pdf_source_url", "pdf_error",
    "text_status", "text_path", "text_chars", "text_error",
)


def preserve_existing_status(records: list[dict]) -> None:
    """Carry download/extraction state across re-scores.

    Re-running harvest must not erase a night of PDF downloads just because
    scores or corpus IDs changed.
    """
    old = load_jsonl(CORPUS_PATH)
    if not old:
        return
    by_arxiv = {r.get("arxiv_id"): r for r in old if r.get("arxiv_id")}
    by_doi = {r.get("doi"): r for r in old if r.get("doi")}
    by_title = {title_key(r.get("title", "")): r for r in old}
    for rec in records:
        previous = (
            by_arxiv.get(rec.get("arxiv_id"))
            or by_doi.get(rec.get("doi"))
            or by_title.get(title_key(rec.get("title", "")))
        )
        if not previous:
            continue
        for field in STATUS_FIELDS:
            value = previous.get(field)
            if value not in (None, "", "pending"):
                rec[field] = value


def preserve_existing_ids(records: list[dict]) -> None:
    """Keep stable corpus IDs across re-scores so docs/links do not churn."""
    old = load_jsonl(CORPUS_PATH)
    by_arxiv = {r.get("arxiv_id"): r for r in old if r.get("arxiv_id")}
    by_doi = {r.get("doi"): r for r in old if r.get("doi")}
    by_title = {title_key(r.get("title", "")): r for r in old}
    used: set[str] = set()
    for rec in records:
        previous = (
            by_arxiv.get(rec.get("arxiv_id"))
            or by_doi.get(rec.get("doi"))
            or by_title.get(title_key(rec.get("title", "")))
        )
        cid = (previous or {}).get("corpus_id")
        if cid and cid not in used:
            rec["corpus_id"] = cid
            used.add(cid)

    highest = 0
    for row in old:
        cid = row.get("corpus_id", "")
        if re.fullmatch(r"P\d{4,}", cid):
            highest = max(highest, int(cid[1:]))
    next_id = highest + 1
    for rec in records:
        if rec.get("corpus_id"):
            continue
        while f"P{next_id:04d}" in used:
            next_id += 1
        rec["corpus_id"] = f"P{next_id:04d}"
        used.add(rec["corpus_id"])
        next_id += 1


def harvest(target: int = 1500, arxiv_limit: int = 100, crossref_rows: int = 60,
            refresh: bool = False) -> list[dict]:
    if refresh:
        for p in CACHE_DIR.glob("*"):
            p.unlink()
    started = datetime.now(timezone.utc)
    raw: list[dict] = []
    errors = []

    print(f"[harvest] {len(QUERIES)} queries -> arXiv + Crossref", flush=True)
    for i, (cluster, query) in enumerate(QUERIES, 1):
        print(f"  [{i}/{len(QUERIES)}] {cluster} {query!r}", flush=True)
        try:
            arxiv_recs = fetch_arxiv(query, limit=arxiv_limit)
        except Exception as exc:  # noqa: BLE001 - keep the night run alive
            errors.append({"source": "arxiv", "query": query, "error": repr(exc)})
            arxiv_recs = []
        for rec in arxiv_recs:
            rec["query_cluster"] = cluster
            rec["query"] = query
            raw.append(score_record(rec))

        try:
            cr_recs = fetch_crossref(query, rows=crossref_rows)
        except Exception as exc:  # noqa: BLE001
            errors.append({"source": "crossref", "query": query, "error": repr(exc)})
            cr_recs = []
        for rec in cr_recs:
            rec["query_cluster"] = cluster
            rec["query"] = query
            raw.append(score_record(rec))
        print(f"      arxiv={len(arxiv_recs)} crossref={len(cr_recs)} raw={len(raw)}",
              flush=True)

    # Guarantee the repository's already-cited anchor papers are represented
    # with their live metadata, even if no query surfaced them.
    print("[harvest] fetching verified anchor IDs directly", flush=True)
    try:
        anchor_recs = fetch_arxiv_ids(list(SEED_TITLES_VERIFIED))
    except Exception as exc:  # noqa: BLE001
        errors.append({"source": "arxiv_ids", "error": repr(exc)})
        anchor_recs = []
    for rec in anchor_recs:
        rec["query_cluster"] = "ANCHOR"
        rec["query"] = "verified docs citation"
        scored = score_record(rec)
        scored["seed"] = True
        scored["score"] = max(scored.get("score", 0), 92.0)
        scored["tier"] = "A"
        raw.append(scored)
    print(f"      anchors={len(anchor_recs)}", flush=True)

    # Canonical seeds: guarantee the foundational literature is present even
    # when lexical search ranks newer papers above it.
    print("[harvest] fetching guaranteed seed records", flush=True)
    seed_recs: list[dict] = []
    try:
        seed_recs.extend(fetch_arxiv_ids(GUARANTEED_ARXIV_IDS))
    except Exception as exc:  # noqa: BLE001
        errors.append({"source": "arxiv_seed_ids", "error": repr(exc)})
    for doi in GUARANTEED_DOIS:
        try:
            rec = fetch_crossref_doi(doi)
        except Exception as exc:  # noqa: BLE001
            errors.append({"source": "crossref_doi", "doi": doi, "error": repr(exc)})
            rec = None
        if rec:
            seed_recs.append(rec)
    for rec in seed_recs:
        rec["query_cluster"] = "SEED"
        rec["query"] = "guaranteed canonical record"
        scored = score_record(rec)
        scored["seed"] = True
        scored["score"] = max(scored.get("score", 0), 95.0)
        scored["tier"] = "A"
        raw.append(scored)
    print(f"      canonical seeds={len(seed_recs)}", flush=True)

    print(f"[harvest] deduplicating {len(raw)} raw records...", flush=True)
    merged = dedupe(raw)

    # Enforce the four verified anchor papers even if their live metadata scores
    # oddly (they are central to the repository's thesis).
    for aid in SEED_TITLES_VERIFIED:
        for rec in merged:
            if rec.get("arxiv_id") == aid:
                rec["seed"] = True
                rec["score"] = max(rec.get("score", 0), 97.0)

    # Merge can combine a high score with a stale tier; normalize once here.
    for rec in merged:
        rec["tier"] = tier_for(rec.get("score", 0))

    accepted = [r for r in merged if r.get("tier") in ("A", "B", "C")]
    accepted.sort(key=lambda r: (r.get("score", 0), r.get("year", 0)), reverse=True)
    if len(accepted) > target:
        # Keep all seeds, then fill by score.
        seeds = [r for r in accepted if r.get("seed")]
        rest = [r for r in accepted if not r.get("seed")]
        accepted = (seeds + rest)[:target]
        accepted.sort(key=lambda r: (r.get("score", 0), r.get("year", 0)),
                      reverse=True)

    preserve_existing_status(accepted)
    preserve_existing_ids(accepted)

    for rec in accepted:
        rec.setdefault("sources", [rec.get("source", "")])
        rec.setdefault("pdf_status", "pending")
        rec.setdefault("text_status", "pending")

    CORPUS_PATH.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                   for r in accepted))
    RAW_PATH.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                for r in merged))
    log = {
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "queries": len(QUERIES),
        "raw_records": len(raw),
        "deduped_records": len(merged),
        "accepted_records": len(accepted),
        "target": target,
        "errors": errors,
        "tiers": {t: sum(1 for r in accepted if r.get("tier") == t)
                  for t in ("A", "B", "C")},
        "sources": {
            s: sum(1 for r in accepted if s in (r.get("sources") or [r.get("source")]))
            for s in ("arxiv", "crossref")
        },
        "seeds_matched": sum(1 for r in accepted if r.get("seed")),
    }
    LOG_PATH.write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2), flush=True)
    return accepted


# --------------------------------------------------------------------------- #
# Download / extract
# --------------------------------------------------------------------------- #

def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    tmp.replace(path)


def is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(5) == b"%PDF-"
    except OSError:
        return False


def paper_stem(rec: dict) -> str:
    if rec.get("arxiv_id"):
        return "arxiv_" + safe_filename(rec["arxiv_id"])
    if rec.get("doi"):
        return "doi_" + safe_filename(rec["doi"].replace("/", "_"))
    return "title_" + title_key(rec.get("title", ""))[:16]


def download_one(rec: dict, limiter: RateLimiter, timeout: int = 90) -> dict:
    stem = paper_stem(rec)
    pdf_path = PDF_DIR / f"{stem}.pdf"
    rec["pdf_path"] = str(pdf_path.relative_to(ROOT))
    if pdf_path.exists() and is_pdf(pdf_path):
        rec["pdf_status"] = "ok"
        rec["pdf_bytes"] = pdf_path.stat().st_size
        return rec

    urls = []
    if rec.get("arxiv_id"):
        urls.append(f"https://arxiv.org/pdf/{rec['arxiv_id']}")
    if rec.get("pdf_url"):
        urls.append(rec["pdf_url"])
    # Deliberately no DOI-landing-page fallback: doi.org usually redirects to
    # an HTML paywall, so trying it only burns time and yields false failures.

    last_error = ""
    for url in urls:
        for attempt in range(3):
            limiter.wait()
            try:
                r = requests.get(url, timeout=timeout, stream=True,
                                 headers={"User-Agent": USER_AGENT},
                                 allow_redirects=True)
                if r.status_code != 200:
                    last_error = f"HTTP {r.status_code}"
                    if r.status_code in (403, 429, 503):
                        time.sleep(4 * (attempt + 1))
                        continue
                    break
                ctype = r.headers.get("content-type", "").lower()
                chunk = next(r.iter_content(1024), b"")
                if chunk[:5] != b"%PDF-" and "pdf" not in ctype:
                    last_error = f"not_pdf ({ctype or 'unknown'})"
                    break
                tmp = pdf_path.with_suffix(".part")
                size = 0
                with tmp.open("wb") as fh:
                    fh.write(chunk)
                    size += len(chunk)
                    for block in r.iter_content(64 * 1024):
                        if block:
                            fh.write(block)
                            size += len(block)
                if size < 10_000 or not is_pdf(tmp):
                    tmp.unlink(missing_ok=True)
                    last_error = f"too_small_or_bad_pdf ({size} bytes)"
                    break
                tmp.replace(pdf_path)
                rec["pdf_status"] = "ok"
                rec["pdf_bytes"] = size
                rec["pdf_source_url"] = url
                return rec
            except requests.RequestException as exc:
                last_error = repr(exc)[:180]
                time.sleep(2 * (attempt + 1))
    rec["pdf_status"] = "failed"
    rec["pdf_error"] = last_error
    return rec


def download(limit: int = 1500, workers: int = 4, only_missing: bool = True) -> None:
    corpus = load_jsonl(CORPUS_PATH)
    if not corpus:
        print("No corpus. Run harvest first.")
        return
    # Mark metadata-only records once, so the report does not treat them as
    # transient failures.
    for rec in corpus:
        if not rec.get("arxiv_id") and not rec.get("pdf_url"):
            if rec.get("pdf_status") in (None, "", "pending", "failed"):
                rec["pdf_status"] = "metadata_only"

    def priority(rec: dict) -> tuple:
        if rec.get("arxiv_id"):
            return (0, -rec.get("score", 0))
        if rec.get("pdf_url"):
            return (1, -rec.get("score", 0))
        return (2, -rec.get("score", 0))

    corpus.sort(key=priority)
    candidates = [r for r in corpus if r.get("arxiv_id") or r.get("pdf_url")]
    selected = candidates[:limit]
    if only_missing:
        selected = [r for r in selected if not (
            r.get("pdf_status") == "ok"
            and (ROOT / r.get("pdf_path", "")).exists())]
    print(f"[download] {len(selected)} papers, {workers} workers", flush=True)
    limiter = RateLimiter(float(os.environ.get("AAVS_DOWNLOAD_INTERVAL", "0.45")))
    done = 0
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_one, r, limiter): r for r in selected}
        for fut in as_completed(futures):
            rec = fut.result()
            done += 1
            if rec.get("pdf_status") != "ok":
                failures.append({"corpus_id": rec.get("corpus_id"),
                                 "title": rec.get("title"),
                                 "error": rec.get("pdf_error")})
            if done % 25 == 0 or done == len(selected):
                ok = sum(1 for r in corpus if r.get("pdf_status") == "ok")
                print(f"  {done}/{len(selected)} this run | {ok} PDFs on disk",
                      flush=True)
    # Persist statuses, preserving any records not selected.
    by_id = {r.get("corpus_id"): r for r in corpus}
    for rec in selected:
        by_id[rec.get("corpus_id")] = rec
    updated = [by_id[r.get("corpus_id")] for r in corpus]
    updated.sort(key=lambda r: r.get("corpus_id", ""))
    write_jsonl(CORPUS_PATH, updated)
    write_jsonl(MANIFEST_PATH, [
        {"corpus_id": r.get("corpus_id"), "title": r.get("title"),
         "status": r.get("pdf_status"), "path": r.get("pdf_path"),
         "bytes": r.get("pdf_bytes"), "arxiv_id": r.get("arxiv_id"),
         "doi": r.get("doi")}
        for r in updated
    ])
    print(f"[download] done: {sum(1 for r in updated if r.get('pdf_status')=='ok')} "
          f"/ {len(updated)} PDFs; {len(failures)} failures this run", flush=True)
    if failures:
        (META_DIR / "download_failures.json").write_text(json.dumps(failures, indent=2))


def extract_one(rec: dict) -> dict:
    pdf_rel = rec.get("pdf_path")
    if not pdf_rel:
        rec["text_status"] = "no_pdf"
        return rec
    pdf_path = ROOT / pdf_rel
    stem = Path(pdf_rel).stem
    txt_path = TEXT_DIR / f"{stem}.txt"
    rec["text_path"] = str(txt_path.relative_to(ROOT))
    if rec.get("pdf_status") != "ok" or not pdf_path.exists():
        rec["text_status"] = "no_pdf"
        return rec
    if txt_path.exists() and txt_path.stat().st_size > 500:
        rec["text_status"] = "ok"
        rec["text_chars"] = txt_path.stat().st_size
        return rec
    if not shutil.which("pdftotext"):
        rec["text_status"] = "pdftotext_missing"
        return rec
    try:
        # Plain reading order beats -layout for prose extraction; -layout
        # interleaves multi-column PDFs into unreadable fragments.
        proc = subprocess.run(
            ["pdftotext", str(pdf_path), str(txt_path)],
            capture_output=True, timeout=120, check=False,
        )
        if proc.returncode == 0 and txt_path.exists():
            chars = txt_path.stat().st_size
            rec["text_chars"] = chars
            rec["text_status"] = "ok" if chars > 500 else "low_text"
        else:
            rec["text_status"] = "extract_failed"
    except (subprocess.TimeoutExpired, OSError) as exc:
        rec["text_status"] = "extract_error"
        rec["text_error"] = repr(exc)[:160]
    return rec


def extract(workers: int = 8, force: bool = False) -> None:
    corpus = load_jsonl(CORPUS_PATH)
    if not corpus:
        print("No corpus. Run harvest first.")
        return
    if force:
        removed = 0
        for txt in TEXT_DIR.glob("*.txt"):
            txt.unlink()
            removed += 1
        print(f"[extract] removed {removed} old text files", flush=True)
    for rec in corpus:
        if rec.get("pdf_status") != "ok":
            rec["text_status"] = "no_pdf"
    selected = [r for r in corpus if r.get("pdf_status") == "ok"]
    print(f"[extract] {len(selected)} PDFs with {workers} workers", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(extract_one, r): r for r in selected}
        for fut in as_completed(futures):
            fut.result()
            done += 1
            if done % 50 == 0 or done == len(selected):
                print(f"  {done}/{len(selected)}", flush=True)
    write_jsonl(CORPUS_PATH, sorted(corpus, key=lambda r: r.get("corpus_id", "")))
    ok = sum(1 for r in corpus if r.get("text_status") == "ok")
    print(f"[extract] text extracted for {ok} / {len(corpus)}", flush=True)


def status() -> None:
    corpus = load_jsonl(CORPUS_PATH)
    if not corpus:
        print("No corpus yet.")
        return
    pdf_ok = sum(1 for r in corpus if r.get("pdf_status") == "ok")
    txt_ok = sum(1 for r in corpus if r.get("text_status") == "ok")
    print(f"corpus records : {len(corpus)}")
    print(f"PDFs on disk   : {pdf_ok}")
    print(f"text extracted : {txt_ok}")
    print(f"total PDF MB   : {sum(r.get('pdf_bytes', 0) or 0 for r in corpus) / 1e6:.1f}")
    print("tiers          :", {t: sum(1 for r in corpus if r.get('tier') == t)
                              for t in ("A", "B", "C")})
    print("clusters       :", {c: sum(1 for r in corpus if r.get('cluster') == c)
                              for c in CLUSTERS})
    print("years          :", min((r.get('year', 9999) for r in corpus), default=0),
          "-", max((r.get('year', 0) for r in corpus), default=0))
    print("sources        :", {s: sum(1 for r in corpus if s in (r.get('sources') or []))
                              for s in ("arxiv", "crossref")})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_harvest = sub.add_parser("harvest")
    p_harvest.add_argument("--target", type=int, default=1500)
    p_harvest.add_argument("--arxiv-limit", type=int, default=100)
    p_harvest.add_argument("--crossref-rows", type=int, default=60)
    p_harvest.add_argument("--refresh", action="store_true")

    p_dl = sub.add_parser("download")
    p_dl.add_argument("--limit", type=int, default=1500)
    p_dl.add_argument("--workers", type=int, default=4)

    p_ex = sub.add_parser("extract")
    p_ex.add_argument("--workers", type=int, default=8)
    p_ex.add_argument("--force", action="store_true",
                      help="Re-extract every PDF (use after changing pdftotext flags)")

    sub.add_parser("status")

    args = parser.parse_args()
    if args.command == "harvest":
        harvest(args.target, args.arxiv_limit, args.crossref_rows, args.refresh)
    elif args.command == "download":
        download(args.limit, args.workers)
    elif args.command == "extract":
        extract(args.workers, args.force)
    elif args.command == "status":
        status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
