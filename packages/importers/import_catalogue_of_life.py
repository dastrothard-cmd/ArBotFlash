#!/usr/bin/env python3
"""Catalogue of Life import foundation.

This intentionally imports a selected release or subtree into a staging JSONL file.
It does not write directly to production tables. API endpoint details may evolve, so
pin and test the endpoint against the selected ChecklistBank release before a bulk run.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Iterable

import requests


def fetch_pages(url: str, params: dict[str, Any], delay: float = 0.25) -> Iterable[dict[str, Any]]:
    session = requests.Session()
    session.headers.update({"User-Agent": "ArbotFlash-importer/0.1 (contact configured by operator)"})
    offset = 0
    limit = int(params.get("limit", 500))
    while True:
        page_params = {**params, "offset": offset, "limit": limit}
        response = session.get(url, params=page_params, timeout=60)
        response.raise_for_status()
        payload = response.json()
        records = payload.get("result") or payload.get("results") or []
        for record in records:
            yield record
        if len(records) < limit:
            break
        offset += limit
        time.sleep(delay)


def normalise(record: dict[str, Any], release_key: str) -> dict[str, Any]:
    return {
        "source": "catalogue_of_life",
        "release_key": release_key,
        "external_id": record.get("id") or record.get("key"),
        "scientific_name": record.get("name") or record.get("scientificName"),
        "rank": record.get("rank"),
        "status": record.get("status"),
        "parent_external_id": record.get("parentId") or record.get("parent"),
        "raw": record,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True, help="Pinned ChecklistBank/COL endpoint")
    parser.add_argument("--release", required=True, help="Release key, DOI or dataset key")
    parser.add_argument("--taxon", help="Optional root taxon external ID")
    parser.add_argument("--output", default="col-staging.jsonl")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    params: dict[str, Any] = {"limit": args.limit}
    if args.taxon:
        params["taxon"] = args.taxon

    output = Path(args.output)
    count = 0
    with output.open("w", encoding="utf-8") as handle:
        for record in fetch_pages(args.endpoint, params):
            handle.write(json.dumps(normalise(record, args.release), ensure_ascii=False) + "\n")
            count += 1
    print(f"Wrote {count} staged records to {output}")


if __name__ == "__main__":
    main()
