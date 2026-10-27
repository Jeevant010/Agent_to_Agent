#!/usr/bin/env python3
"""Fill missing abstracts from Semantic Scholar's batch endpoint.

Only records with no abstract and a DOI are touched. The script preserves the
corpus ordering and records `abstract_source` so the provenance is explicit.

Usage:
    python scripts/enrich_abstracts.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "papers" / "metadata" / "papers_corpus.jsonl"
URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
FIELDS = "title,abstract,year,venue,externalIds"
BATCH = 100


def load() -> list[dict]:
    return [json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()]


def save(rows: list[dict]) -> None:
    tmp = CORPUS.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    tmp.replace(CORPUS)


def fetch(ids: list[str]) -> list[dict | None]:
    payload = {"ids": ids}
    for attempt in range(5):
        try:
            r = requests.post(URL, params={"fields": FIELDS}, json=payload,
                              timeout=90,
                              headers={"User-Agent": "AAVS-Literature/1.0"})
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(6 * (attempt + 1))
                continue
            print(f"  HTTP {r.status_code}: {r.text[:120]}")
            time.sleep(3 * (attempt + 1))
        except requests.RequestException as exc:
            print(f"  error: {exc}")
            time.sleep(3 * (attempt + 1))
    return []


def main() -> None:
    rows = load()
    targets = [r for r in rows if not r.get("abstract") and r.get("doi")]
    print(f"targets: {len(targets)}")
    filled = 0
    for start in range(0, len(targets), BATCH):
        chunk = targets[start:start + BATCH]
        ids = ["DOI:" + r["doi"] for r in chunk]
        results = fetch(ids)
        print(f"  batch {start}-{start + len(chunk) - 1}: {len(results)} results")
        for rec, item in zip(chunk, results):
            if not item:
                continue
            abstract = (item.get("abstract") or "").strip()
            if len(abstract) < 60:
                continue
            rec["abstract"] = abstract
            rec["abstract_source"] = "semantic_scholar"
            if item.get("venue") and not rec.get("venue"):
                rec["venue"] = item["venue"]
            filled += 1
        time.sleep(3)
    save(rows)
    print(f"filled {filled} abstracts; remaining missing: "
          f"{sum(1 for r in rows if not r.get('abstract'))}")


if __name__ == "__main__":
    main()
