#!/usr/bin/env python3
"""Run conservative taxonomy candidate collection across the pending seed queue.

The command never changes accepted names. With --apply it only moves source
responses into review_required/no_match/error states for later human decisions.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from packages.importers.reconcile_taxonomy import DEFAULT_DB, lookup, queue_rows, save_candidate

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--sources", nargs="+", choices=["catalogue_of_life", "gbif"], default=["catalogue_of_life", "gbif"])
    parser.add_argument("--limit-per-source", type=int, default=80)
    parser.add_argument("--fixture-root", type=Path, help="Directory containing source-named fixture subdirectories")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--report", type=Path, default=ROOT / "data" / "reconciliation" / "authority-batch-report.json")
    args = parser.parse_args()

    report = {"generatedAt": datetime.now(timezone.utc).isoformat(), "apply": args.apply, "sources": {}, "safety": "Candidates only; canonical taxonomy is not mutated."}
    with sqlite3.connect(args.db) as connection:
        for source in args.sources:
            fixture_dir = args.fixture_root / source if args.fixture_root else None
            rows = queue_rows(connection, source, max(1, args.limit_per_source))
            items = []
            for row in rows:
                try:
                    candidate = lookup(source, row["searched_name"], fixture_dir)
                    items.append({"taxonId": row["taxon_id"], "searchedName": row["searched_name"], "candidate": asdict(candidate) if candidate else None})
                    if args.apply:
                        save_candidate(connection, row, candidate)
                        connection.commit()
                except Exception as exc:
                    items.append({"taxonId": row["taxon_id"], "searchedName": row["searched_name"], "error": str(exc)})
                    if args.apply:
                        save_candidate(connection, row, None, error=str(exc))
                        connection.commit()
                if not fixture_dir:
                    time.sleep(max(0, args.delay))
            report["sources"][source] = {"processed": len(items), "items": items}

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "apply": args.apply, "processed": {key: value["processed"] for key, value in report["sources"].items()}}, indent=2))


if __name__ == "__main__":
    main()
