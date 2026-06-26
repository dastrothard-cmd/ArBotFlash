#!/usr/bin/env python3
"""Build the first versioned ArbotFlash regional offline pack.

The pack is deliberately honest about coverage. It contains all 80 study taxa,
complete database payloads for offline use, and only locally stored media whose
file-level licence metadata has already been reviewed.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "dev" / "arbotflash-dev.sqlite3"
PACK_KEY = "tree-id-80"
PACK_VERSION = "0.12.0"
PACK_DIR = ROOT / "packs" / PACK_KEY
WEB_DIR = ROOT / "apps" / "web"
FILTERS = WEB_DIR / "data" / "filter-definitions.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def projection_to_taxon(row: sqlite3.Row) -> dict[str, Any]:
    traits = json.loads(row["traits_json"] or "{}")
    result: dict[str, Any] = {
        "id": row["taxon_id"],
        "scientificName": row["scientific_name"],
        "commonName": row["common_name"],
        "domain": row["domain_name"] or "",
        "kingdom": row["kingdom_name"] or "",
        "phylum": row["phylum_name"] or "",
        "class": row["class_name"] or "",
        "order": row["order_name"] or "",
        "family": row["family_name"] or "",
        "genus": row["genus_name"] or "",
        "lifeStatus": (row["life_status"] or "uncertain").replace("_", " ").title(),
        "verification": (row["verification_status"] or "unverified").replace("_", " ").title(),
        "sourcePack": row["source_pack"] or "",
        "taxonomyReconciliation": row["reconciliation_status"] or "",
        "profileStatus": row["profile_status"] or "",
        "verifiedImages": row["image_status"] or "",
    }
    for key, values in traits.items():
        if key in result:
            continue
        result[key] = values[0] if isinstance(values, list) and len(values) == 1 else values
    return result


def full_profile(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    taxon_id = row["taxon_id"]
    taxon = projection_to_taxon(row)
    source_row = connection.execute("SELECT canonical_rank, source_record_index FROM taxon WHERE id = ?", (taxon_id,)).fetchone()
    taxon["canonicalRank"] = source_row["canonical_rank"]
    taxon["sourceRecordIndex"] = source_row["source_record_index"]
    taxon["classifications"] = [dict(item) for item in connection.execute(
        "SELECT rank, name, verification_status FROM taxon_classification WHERE taxon_id = ? ORDER BY CASE rank WHEN 'domain' THEN 1 WHEN 'kingdom' THEN 2 WHEN 'phylum' THEN 3 WHEN 'class' THEN 4 WHEN 'order' THEN 5 WHEN 'family' THEN 6 WHEN 'genus' THEN 7 ELSE 99 END",
        (taxon_id,),
    )]
    taxon["names"] = [dict(item) for item in connection.execute(
        "SELECT name, authorship, status, language_code, region_code, verification_status FROM taxon_name WHERE taxon_id = ? ORDER BY status, name",
        (taxon_id,),
    )]
    taxon["profileSections"] = [dict(item) for item in connection.execute(
        "SELECT section_key, language_code, body_markdown, verification_status, assertion_status, licence_code, source_revision FROM profile_section WHERE taxon_id = ? ORDER BY section_key",
        (taxon_id,),
    )]
    taxon["citations"] = [dict(item) for item in connection.execute(
        """SELECT c.citation_text, c.source_url, c.retrieved_at, c.licence_code,
                  d.title AS source_title, r.release_key
           FROM source_citation c
           LEFT JOIN source_release r ON r.id = c.source_release_id
           LEFT JOIN source_dataset d ON d.id = r.source_dataset_id
           WHERE c.taxon_id = ? ORDER BY c.citation_text""",
        (taxon_id,),
    )]
    taxon["reconciliation"] = [dict(item) for item in connection.execute(
        """SELECT d.key AS source_key, d.title AS source_title, q.status,
                  q.searched_name, q.proposed_external_id, q.proposed_scientific_name,
                  q.proposed_rank, q.confidence, q.notes, q.checked_at
           FROM reconciliation_queue q JOIN source_dataset d ON d.id = q.source_dataset_id
           WHERE q.taxon_id = ? ORDER BY d.key""",
        (taxon_id,),
    )]
    media = [dict(item) for item in connection.execute(
        """SELECT m.id, COALESCE(m.storage_key, m.original_url) AS display_url,
                  m.storage_key, m.original_url, m.title, m.creator, m.source_page_url,
                  m.licence_code, m.licence_url, mt.category, mt.caption,
                  mt.diagnostic_notes, mt.is_primary, m.verification_status,
                  m.captured_at, m.metadata_json
           FROM media_taxon mt JOIN media_asset m ON m.id = mt.media_asset_id
           WHERE mt.taxon_id = ? ORDER BY mt.is_primary DESC, mt.category""",
        (taxon_id,),
    )]
    for item in media:
        if item["storage_key"]:
            item["display_url"] = f"./media/{taxon_id}.jpg"
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
    taxon["media"] = media
    return taxon


def main() -> None:
    if not DB_PATH.exists():
        from scripts.build_dev_db import build
        build(DB_PATH)

    if PACK_DIR.exists():
        shutil.rmtree(PACK_DIR)
    (PACK_DIR / "media").mkdir(parents=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM taxon_search_projection ORDER BY scientific_name COLLATE NOCASE"
        ).fetchall()
        taxa = [projection_to_taxon(row) for row in rows]
        profiles = {row["taxon_id"]: full_profile(connection, row) for row in rows}
        sources = [dict(row) for row in connection.execute(
            """SELECT d.key, d.title, d.publisher, d.homepage_url, d.licence_code,
                      d.licence_url, d.authority_role, d.enabled,
                      r.release_key, r.issued_on, r.doi, r.imported_at
               FROM source_dataset d LEFT JOIN source_release r ON r.source_dataset_id = d.id
               ORDER BY d.title, r.release_key"""
        )]
        attributions = [dict(row) for row in connection.execute(
            """SELECT p.scientific_name, p.common_name, m.storage_key, m.title,
                      m.creator, m.source_page_url, m.licence_code, m.licence_url
               FROM media_asset m JOIN media_taxon mt ON mt.media_asset_id = m.id
               JOIN taxon_search_projection p ON p.taxon_id = mt.taxon_id
               WHERE m.storage_key IS NOT NULL ORDER BY p.scientific_name"""
        )]

    for taxon_id, profile in profiles.items():
        for media in profile["media"]:
            if not media.get("storage_key"):
                continue
            source = WEB_DIR / media["storage_key"].lstrip("/")
            target = PACK_DIR / "media" / f"{taxon_id}.jpg"
            if not source.exists():
                raise FileNotFoundError(f"Missing locally reviewed media: {source}")
            shutil.copy2(source, target)

    write_json(PACK_DIR / "taxa.json", taxa)
    write_json(PACK_DIR / "profiles.json", profiles)
    shutil.copy2(FILTERS, PACK_DIR / "filter-definitions.json")
    write_json(PACK_DIR / "sources.json", sources)
    write_json(PACK_DIR / "attributions.json", attributions)
    (PACK_DIR / "README.txt").write_text(
        "ArbotFlash Tree ID 80 offline pack v0.12.0\n\n"
        "Coverage: 80 study taxa; 80 source-enriched profiles with locally stored, individually licensed images; "
        "0 seed profile shells. Catalogue of Life, GBIF and Australian Plant Census review is not complete.\n\n"
        "This pack is independent from the hosted Tree ID Trainer. See attributions.json and sources.json before redistributing media or source-derived content.\n",
        encoding="utf-8",
    )

    data_files = [
        PACK_DIR / "taxa.json", PACK_DIR / "profiles.json", PACK_DIR / "filter-definitions.json",
        PACK_DIR / "sources.json", PACK_DIR / "attributions.json", PACK_DIR / "README.txt",
        *sorted((PACK_DIR / "media").glob("*.jpg")),
    ]
    file_records = [{
        "path": str(path.relative_to(PACK_DIR)).replace("\\", "/"),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    } for path in data_files]
    enriched_count = sum(taxon.get("profileStatus") != "Seed shell only" for taxon in taxa)
    local_media_count = len(list((PACK_DIR / "media").glob("*.jpg")))
    archive_name = f"arbotflash-tree-id-80-v{PACK_VERSION}.zip"
    manifest = {
        "format": "arbotflash-offline-pack-v1",
        "packKey": PACK_KEY,
        "title": "Tree ID Trainer seed — 80 trees",
        "version": PACK_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "description": "The complete original 80-tree study set in ArbotFlash's versioned offline format.",
        "coverage": {
            "taxonCount": len(taxa),
            "enrichedTaxa": enriched_count,
            "profileShells": len(taxa) - enriched_count,
            "localMediaCount": local_media_count,
            "taxonomyStatus": f"Specialist regional evidence for {enriched_count} taxa; global and national reconciliation remains queued.",
        },
        "files": file_records,
        "archiveFile": archive_name,
        "downloadUrl": f"/api/packs/{PACK_KEY}/download",
        "installEndpoints": {
            "manifest": f"/api/packs/{PACK_KEY}/manifest",
            "taxa": f"/api/packs/{PACK_KEY}/taxa",
            "profiles": f"/api/packs/{PACK_KEY}/profiles",
        },
    }
    write_json(PACK_DIR / "manifest.json", manifest)

    archive_path = PACK_DIR / archive_name
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACK_DIR.rglob("*")):
            if path.is_file() and path != archive_path and not path.name.endswith(".sha256"):
                archive.write(path, Path(PACK_KEY) / path.relative_to(PACK_DIR))
    (PACK_DIR / f"{archive_name}.sha256").write_text(f"{sha256(archive_path)}  {archive_name}\n", encoding="utf-8")
    print(json.dumps({"pack": PACK_KEY, "taxa": len(taxa), "enriched": enriched_count, "media": local_media_count, "archive": str(archive_path)}, indent=2))


if __name__ == "__main__":
    main()
