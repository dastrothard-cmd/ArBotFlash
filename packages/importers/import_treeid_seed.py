#!/usr/bin/env python3
"""Extract the finished Tree ID Trainer seed into ArbotFlash staging/app JSON.

Accepted input formats:
- the final Tree ID Trainer ZIP
- its public/index.html
- a JSON export containing a list, `species`, or `trees`

The original source is never modified. Unknown source fields are retained in
`source_payload`; product/grip experiment fields are excluded by policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

EXCLUDED_KEYWORDS = {
    "grip", "adhesion", "friction", "hand application", "formulation",
    "wa grip", "product experiment", "grip test"
}


def is_excluded(key: str) -> bool:
    lowered = key.lower().replace("_", " ")
    return any(term in lowered for term in EXCLUDED_KEYWORDS)


def first(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", []):
            return value
    return None


def parse_html(text: str) -> list[dict[str, Any]]:
    match = re.search(
        r"const\s+BUILTIN\s*=\s*(\[.*?\]);\s*\nconst\s+STORAGE_KEY",
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Could not locate the Tree ID Trainer BUILTIN dataset")
    records = json.loads(match.group(1))
    if not isinstance(records, list):
        raise ValueError("The BUILTIN dataset was not a list")
    return records


def load_records(source: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metadata: dict[str, Any] = {
        "source_filename": source.name,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    suffix = source.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(source) as archive:
            candidates = [name for name in archive.namelist() if name.endswith("public/index.html")]
            if not candidates:
                candidates = [name for name in archive.namelist() if name.endswith("index.html")]
            if not candidates:
                raise ValueError("No index.html was found in the ZIP")
            html_name = sorted(candidates, key=len)[0]
            text = archive.read(html_name).decode("utf-8")
            metadata["embedded_source_path"] = html_name
            return parse_html(text), metadata
    if suffix in {".html", ".htm"}:
        return parse_html(source.read_text(encoding="utf-8")), metadata
    payload = json.loads(source.read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else payload.get("species") or payload.get("trees") or []
    if not isinstance(records, list):
        raise ValueError("Could not find a species list in the supplied JSON")
    return records, metadata


def slug(value: str) -> str:
    normalised = unicodedata.normalize("NFKD", value)
    ascii_value = normalised.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return clean or "taxon"


def staging_record(record: dict[str, Any], index: int, metadata: dict[str, Any]) -> dict[str, Any]:
    retained = {key: value for key, value in record.items() if not is_excluded(key)}
    removed = sorted(key for key in record if is_excluded(key))
    scientific = first(record, "scientificName", "scientific_name", "binomial", "botanicalName")
    common = first(record, "commonNames", "common_names", "commonName", "common_name", "common")
    family = first(record, "family", "familyName", "family_name")
    genus = first(record, "genus") or (str(scientific).split()[0] if scientific else None)
    return {
        "source": "tree_id_trainer_v15_23_verified",
        "source_record_index": index,
        "source_sha256": metadata["source_sha256"],
        "scientific_name": scientific,
        "common_names": [common] if isinstance(common, str) else common,
        "family": family,
        "genus": genus,
        "life_status": "extant",
        "verification_status": "verified_seed_import",
        "excluded_fields": removed,
        "source_payload": retained,
    }


def app_record(record: dict[str, Any], index: int, metadata: dict[str, Any]) -> dict[str, Any]:
    scientific = str(first(record, "scientificName", "scientific_name", "binomial", "botanicalName") or "").strip()
    common = str(first(record, "commonName", "common_name", "common") or "").strip()
    family = str(first(record, "family", "familyName", "family_name") or "").strip()
    genus = scientific.split()[0] if scientific else ""
    return {
        "id": f"treeid-{slug(scientific)}",
        "sourceRecordIndex": index,
        "commonName": common,
        "scientificName": scientific,
        "domain": "Eukaryota",
        "kingdom": "Plantae",
        "phylum": "Tracheophyta",
        "class": "",
        "order": "",
        "family": family,
        "genus": genus,
        "lifeStatus": "Extant",
        "continent": [],
        "country": [],
        "region": [],
        "environment": ["Terrestrial"],
        "organisation": "Multicellular",
        "trophicMode": ["Autotroph"],
        "establishment": [],
        "plantForm": [],
        "leafArrangement": [],
        "barkType": [],
        "exudate": [],
        "verifiedImages": "Not available",
        "verification": "Verified seed import",
        "sourcePack": "Tree ID Trainer 80",
        "profile": {
            "summary": "Migrated from the finished Tree ID Trainer seed list. A sourced full profile has not yet been attached.",
            "features": "The original trainer record supplies the accepted study name, common name and family only.",
            "distribution": "Pending sourced geographic enrichment.",
            "sources": [
                "Tree ID Trainer v15.23 verified seed",
                f"Source record {index}; upload SHA-256 {metadata['source_sha256'][:12]}…"
            ]
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_source", help="Tree ID Trainer ZIP, index.html or JSON export")
    parser.add_argument("--staging-output", default="treeid-80-staging.jsonl")
    parser.add_argument("--app-output", default="treeid-seed-80.json")
    parser.add_argument("--metadata-output", default="treeid-seed-metadata.json")
    args = parser.parse_args()

    source = Path(args.input_source)
    records, metadata = load_records(source)
    staged = [staging_record(record, index, metadata) for index, record in enumerate(records, start=1)]
    app = [app_record(record, index, metadata) for index, record in enumerate(records, start=1)]

    Path(args.staging_output).write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in staged),
        encoding="utf-8",
    )
    Path(args.app_output).write_text(json.dumps(app, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metadata.update({
        "record_count": len(records),
        "unique_scientific_names": len({row["scientificName"].casefold() for row in app}),
        "family_count": len({row["family"] for row in app if row["family"]}),
        "genus_count": len({row["genus"] for row in app if row["genus"]}),
    })
    Path(args.metadata_output).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} seed records")


if __name__ == "__main__":
    main()
