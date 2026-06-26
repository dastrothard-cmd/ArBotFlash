#!/usr/bin/env python3
"""Create review candidates for seed taxa without silently changing taxonomy.

This script is intentionally conservative. It queries a pinned Catalogue of Life
ChecklistBank release or GBIF's species matcher, writes the proposed match into
`reconciliation_queue`, and stops at `review_required`. A later admin review must
approve the mapping before canonical names, classifications or external IDs change.

Network access is not required for tests: pass --fixture-dir with one JSON response
per scientific name, named with a URL-safe slug such as Eucalyptus_marginata.json.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "database" / "dev" / "arbotflash-dev.sqlite3"
RELEASES = json.loads((ROOT / "data" / "source_releases.json").read_text(encoding="utf-8"))
USER_AGENT = "ArbotFlash/0.5 taxonomy-reconciliation (development; contact configured by deployer)"


@dataclass
class Candidate:
    source_key: str
    searched_name: str
    external_id: str | None
    scientific_name: str | None
    rank: str | None
    status: str | None
    confidence: float
    classification: list[dict[str, Any]]
    raw_summary: dict[str, Any]


def request_json(url: str, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fixture_name(scientific_name: str) -> str:
    return "_".join(scientific_name.split()) + ".json"


def canonical_text(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def parse_col_response(searched_name: str, payload: dict[str, Any]) -> Candidate | None:
    candidates: list[Candidate] = []
    for item in payload.get("result", []):
        usage = item.get("usage") or {}
        name = usage.get("name") or {}
        scientific_name = name.get("scientificName") or usage.get("label") or item.get("name")
        rank = name.get("rank") or usage.get("rank")
        status = usage.get("status")
        exact = canonical_text(scientific_name) == canonical_text(searched_name)
        accepted = status in {"accepted", "provisionally accepted"}
        rank_match = str(rank or "").casefold() in {"species", "subspecies", "variety", "form"}
        confidence = 1.0 if exact and accepted and rank_match else 0.9 if exact else 0.55
        candidates.append(Candidate(
            source_key="catalogue_of_life",
            searched_name=searched_name,
            external_id=str(item.get("id") or usage.get("id") or "") or None,
            scientific_name=scientific_name,
            rank=rank,
            status=status,
            confidence=confidence,
            classification=item.get("classification") or [],
            raw_summary={
                "group": item.get("group"),
                "sectorDatasetKey": item.get("sectorDatasetKey"),
                "authorship": name.get("authorship"),
                "extinct": usage.get("extinct"),
                "environments": usage.get("environments") or [],
            },
        ))
    if not candidates:
        return None
    return sorted(candidates, key=lambda candidate: (-candidate.confidence, canonical_text(candidate.scientific_name)))[0]


def parse_gbif_response(searched_name: str, payload: dict[str, Any]) -> Candidate | None:
    if not payload or payload.get("matchType") == "NONE":
        return None
    scientific_name = payload.get("scientificName") or payload.get("canonicalName")
    confidence = float(payload.get("confidence", 0)) / 100
    classification = [
        {"rank": rank, "name": payload.get(rank)}
        for rank in ("kingdom", "phylum", "class", "order", "family", "genus", "species")
        if payload.get(rank)
    ]
    return Candidate(
        source_key="gbif",
        searched_name=searched_name,
        external_id=str(payload.get("usageKey") or payload.get("acceptedUsageKey") or "") or None,
        scientific_name=scientific_name,
        rank=payload.get("rank"),
        status=payload.get("status"),
        confidence=confidence,
        classification=classification,
        raw_summary={
            "matchType": payload.get("matchType"),
            "note": payload.get("note"),
            "synonym": payload.get("synonym"),
            "canonicalName": payload.get("canonicalName"),
        },
    )


def lookup(source: str, scientific_name: str, fixture_dir: Path | None = None) -> Candidate | None:
    if fixture_dir:
        payload = json.loads((fixture_dir / fixture_name(scientific_name)).read_text(encoding="utf-8"))
    elif source == "catalogue_of_life":
        release = RELEASES["catalogue_of_life"]
        query = urllib.parse.urlencode({"q": scientific_name, "limit": 10})
        url = f"{release['api_base']}/dataset/{release['checklistbank_dataset_key']}/nameusage/search?{query}"
        payload = request_json(url)
    elif source == "gbif":
        release = RELEASES["gbif"]
        query = urllib.parse.urlencode({"name": scientific_name})
        payload = request_json(f"{release['api_base']}/species/match?{query}")
    else:
        raise ValueError(f"Unsupported source: {source}")

    return parse_col_response(scientific_name, payload) if source == "catalogue_of_life" else parse_gbif_response(scientific_name, payload)


def queue_rows(
    connection: sqlite3.Connection,
    source: str,
    limit: int,
    scientific_name: str | None = None,
) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    sql = """SELECT q.taxon_id, q.searched_name, d.id AS source_dataset_id
             FROM reconciliation_queue q
             JOIN source_dataset d ON d.id = q.source_dataset_id
             WHERE d.key = ? AND q.status IN ('pending', 'error')"""
    params: list[Any] = [source]
    if scientific_name:
        sql += " AND q.searched_name = ?"
        params.append(scientific_name)
    sql += " ORDER BY q.searched_name COLLATE NOCASE LIMIT ?"
    params.append(limit)
    return connection.execute(sql, params).fetchall()


def save_candidate(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    candidate: Candidate | None,
    error: str | None = None,
) -> None:
    checked_at = datetime.now(timezone.utc).isoformat()
    if error:
        connection.execute(
            """UPDATE reconciliation_queue SET status='error', notes=?, checked_at=?
               WHERE taxon_id=? AND source_dataset_id=?""",
            (error, checked_at, row["taxon_id"], row["source_dataset_id"]),
        )
        return
    if candidate is None:
        connection.execute(
            """UPDATE reconciliation_queue SET status='no_match', notes=?, checked_at=?
               WHERE taxon_id=? AND source_dataset_id=?""",
            (
                "No candidate returned. Manual search required.", checked_at,
                row["taxon_id"], row["source_dataset_id"],
            ),
        )
        return
    notes = json.dumps({
        "status": candidate.status,
        "classification": candidate.classification,
        "raw_summary": candidate.raw_summary,
        "review_rule": "Candidate only; canonical record remains unchanged until approved.",
    }, ensure_ascii=False)
    connection.execute(
        """UPDATE reconciliation_queue
           SET status='review_required', proposed_external_id=?,
               proposed_scientific_name=?, proposed_rank=?, confidence=?,
               notes=?, checked_at=?
           WHERE taxon_id=? AND source_dataset_id=?""",
        (
            candidate.external_id, candidate.scientific_name, candidate.rank,
            candidate.confidence, notes, checked_at,
            row["taxon_id"], row["source_dataset_id"],
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["catalogue_of_life", "gbif"], required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--name", help="Reconcile one exact scientific name")
    parser.add_argument("--fixture-dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="Write candidates into the review queue")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between live requests")
    args = parser.parse_args()

    with sqlite3.connect(args.db) as connection:
        rows = queue_rows(connection, args.source, max(1, args.limit), args.name)
        output: list[dict[str, Any]] = []
        for row in rows:
            try:
                candidate = lookup(args.source, row["searched_name"], args.fixture_dir)
                output.append({
                    "taxon_id": row["taxon_id"],
                    "candidate": asdict(candidate) if candidate else None,
                })
                if args.apply:
                    save_candidate(connection, row, candidate)
                    connection.commit()
            except Exception as exc:  # command-line importer must preserve the queue
                output.append({"taxon_id": row["taxon_id"], "error": str(exc)})
                if args.apply:
                    save_candidate(connection, row, None, error=str(exc))
                    connection.commit()
            if not args.fixture_dir:
                time.sleep(max(0, args.delay))

    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
