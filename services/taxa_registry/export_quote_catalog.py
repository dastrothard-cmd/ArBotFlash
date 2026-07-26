#!/usr/bin/env python3
"""Export a compact reviewed taxon search snapshot for ARBOT Quote.

The export contains search/display fields only. Full evidence, source records,
media and taxonomy history stay in the registry service.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def export_catalog(args: argparse.Namespace) -> int:
    database = Path(args.db).resolve()
    output = Path(args.output).resolve()
    if not database.is_file():
        raise FileNotFoundError(database)

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        clauses = ["arboreal_status IN ('tree','tree-like')"]
        parameters: list[object] = []
        if args.region:
            clauses.append("(',' || region_codes || ',') LIKE ?")
            parameters.append(f"%,{args.region},%")
        if args.authority_profile:
            clauses.append("authority_profile = ?")
            parameters.append(args.authority_profile)
        parameters.append(args.limit)
        rows = connection.execute(
            f"""
            SELECT concept_id, accepted_name, accepted_authorship, common_name,
                   aliases, family, genus, rank, arboreal_status, region_codes,
                   authority_profile, profile_status, updated_at
            FROM taxon_search_projection
            WHERE {' AND '.join(clauses)}
            ORDER BY accepted_name COLLATE NOCASE
            LIMIT ?
            """,
            parameters,
        ).fetchall()
        release_rows = connection.execute(
            """
            SELECT id, source_id, source_version, archive_sha256, licence, citation
            FROM registry_releases
            WHERE status IN ('reviewed','published')
            ORDER BY source_id, source_version
            """
        ).fetchall()
    finally:
        connection.close()

    taxa = [
        {
            "id": row["concept_id"],
            "binomial": row["accepted_name"],
            "authorship": row["accepted_authorship"],
            "common": row["common_name"],
            "aliases": [value for value in row["aliases"].split("|") if value],
            "family": row["family"],
            "genus": row["genus"],
            "rank": row["rank"],
            "arborealStatus": row["arboreal_status"],
            "regions": [value for value in row["region_codes"].split(",") if value],
            "authorityProfile": row["authority_profile"],
            "profileStatus": row["profile_status"],
            "updatedAt": row["updated_at"],
        }
        for row in rows
    ]
    releases = [dict(row) for row in release_rows]
    payload = {
        "schemaVersion": 1,
        "product": "ARBOT Quote taxon search snapshot",
        "generatedAt": utc_now(),
        "filters": {
            "region": args.region or None,
            "authorityProfile": args.authority_profile or None,
            "arborealStatus": ["tree", "tree-like"],
        },
        "count": len(taxa),
        "truncated": len(taxa) >= args.limit,
        "registryReleases": releases,
        "taxa": taxa,
    }
    encoded = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    manifest = output.with_suffix(output.suffix + ".manifest.json")
    manifest.write_text(json.dumps({
        "file": output.name,
        "sha256": digest,
        "bytes": len(encoded),
        "count": len(taxa),
        "generatedAt": payload["generatedAt"],
        "registryReleaseIds": [release["id"] for release in releases],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "manifest": str(manifest),
        "sha256": digest,
        "count": len(taxa),
        "truncated": payload["truncated"],
    }, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--db", required=True)
    result.add_argument("--output", required=True)
    result.add_argument("--region", default="")
    result.add_argument("--authority-profile", default="")
    result.add_argument("--limit", type=int, default=50_000)
    return result


def main() -> int:
    try:
        return export_catalog(parser().parse_args())
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"quote catalogue export failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
