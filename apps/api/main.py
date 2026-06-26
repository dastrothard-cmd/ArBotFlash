from __future__ import annotations

import json
import os
import random
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "dev" / "arbotflash-dev.sqlite3"
WEB_DIR = ROOT / "apps" / "web"
ADMIN_DIR = ROOT / "apps" / "admin"
FILTER_DEFINITIONS_PATH = WEB_DIR / "data" / "filter-definitions.json"
PACKS_DIR = ROOT / "packs"
CORE_FILTER_COLUMNS = {
    "domain": "domain_name",
    "kingdom": "kingdom_name",
    "phylum": "phylum_name",
    "class": "class_name",
    "order": "order_name",
    "family": "family_name",
    "genus": "genus_name",
    "lifeStatus": "life_status",
    "verification": "verification_status",
    "sourcePack": "source_pack",
    "verifiedImages": "image_status",
    "profileStatus": "profile_status",
    "taxonomyReconciliation": "reconciliation_status",
}


def ensure_database() -> None:
    if DB_PATH.exists():
        return
    from scripts.build_dev_db import build

    build(DB_PATH)


def connect() -> sqlite3.Connection:
    ensure_database()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def definitions() -> list[dict[str, Any]]:
    return json.loads(FILTER_DEFINITIONS_PATH.read_text(encoding="utf-8"))


def display_life_status(value: str | None) -> str:
    return (value or "uncertain").replace("_", " ").title()


def display_verification(value: str | None) -> str:
    labels = {
        "verified_seed_import": "Verified seed import",
        "authoritative_import": "Authoritative import",
        "specialist_import": "Specialist import",
        "expert_verified": "Expert verified",
        "community_submitted": "Community submitted",
        "ai_assisted_draft": "AI-assisted draft",
        "unverified": "Unverified",
        "disputed": "Disputed",
        "superseded": "Superseded",
    }
    return labels.get(value or "unverified", (value or "unverified").replace("_", " ").title())


def parse_filter_tokens(tokens: list[str]) -> dict[str, list[str]]:
    parsed: dict[str, list[str]] = {}
    valid_keys = {definition["key"] for definition in definitions()}
    for token in tokens:
        if ":" not in token:
            raise HTTPException(status_code=400, detail=f"Invalid filter token: {token!r}")
        key, value = token.split(":", 1)
        key, value = key.strip(), value.strip()
        if not key or not value:
            raise HTTPException(status_code=400, detail=f"Invalid filter token: {token!r}")
        if key not in valid_keys:
            raise HTTPException(status_code=400, detail=f"Unknown filter key: {key}")
        parsed.setdefault(key, [])
        if value not in parsed[key]:
            parsed[key].append(value)
    return parsed


def projection_to_taxon(row: sqlite3.Row) -> dict[str, Any]:
    traits = json.loads(row["traits_json"] or "{}")
    output: dict[str, Any] = {
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
        "lifeStatus": display_life_status(row["life_status"]),
        "verification": display_verification(row["verification_status"]),
        "sourcePack": row["source_pack"] or "",
        "taxonomyReconciliation": row["reconciliation_status"] or "",
        "profileStatus": row["profile_status"] or "",
        "verifiedImages": row["image_status"] or "",
    }
    for key, values in traits.items():
        if key in output:
            continue
        if not isinstance(values, list):
            output[key] = values
        elif len(values) == 1 and key in {"organisation", "verifiedImages", "verification", "sourcePack", "profileStatus", "taxonomyReconciliation"}:
            output[key] = values[0]
        else:
            output[key] = values
    return output


def taxon_values(taxon: dict[str, Any], key: str) -> list[str]:
    value = taxon.get(key)
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def normalise_filter_value(key: str, value: str) -> str:
    if key == "lifeStatus":
        return value.lower().replace(" ", "_")
    if key == "verification":
        reverse = {
            "Verified seed import": "verified_seed_import",
            "Authoritative import": "authoritative_import",
            "Specialist import": "specialist_import",
            "Expert verified": "expert_verified",
            "Community submitted": "community_submitted",
            "AI-assisted draft": "ai_assisted_draft",
            "Unverified": "unverified",
            "Disputed": "disputed",
            "Superseded": "superseded",
        }
        return reverse.get(value, value.lower().replace(" ", "_"))
    return value


def query_projection(
    connection: sqlite3.Connection,
    search: str,
    filters: dict[str, list[str]],
) -> list[sqlite3.Row]:
    clauses: list[str] = []
    parameters: list[Any] = []
    if search.strip():
        clauses.append("searchable_text LIKE ?")
        parameters.append(f"%{search.strip().casefold()}%")

    for key, selected_values in filters.items():
        if key in CORE_FILTER_COLUMNS:
            column = CORE_FILTER_COLUMNS[key]
            placeholders = ",".join("?" for _ in selected_values)
            clauses.append(f"{column} IN ({placeholders})")
            parameters.extend(normalise_filter_value(key, value) for value in selected_values)
        else:
            placeholders = ",".join("?" for _ in selected_values)
            clauses.append(
                "EXISTS (SELECT 1 FROM json_each(json_extract(traits_json, ?)) "
                f"WHERE CAST(value AS TEXT) IN ({placeholders}))"
            )
            parameters.append(f'$."{key}"')
            parameters.extend(selected_values)

    sql = "SELECT * FROM taxon_search_projection"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY scientific_name COLLATE NOCASE, common_name COLLATE NOCASE"
    return connection.execute(sql, parameters).fetchall()


def facet_counts(taxa: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for taxon in taxa:
        for value in set(taxon_values(taxon, key)):
            counts[value] = counts.get(value, 0) + 1
    return [
        {"value": value, "count": count}
        for value, count in sorted(counts.items(), key=lambda item: (str(item[0]).casefold(), str(item[0])))
    ]


def build_facets(taxa: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        definition["key"]: counts
        for definition in definitions()
        if (counts := facet_counts(taxa, definition["key"]))
    }


def build_disjunctive_facets(
    connection: sqlite3.Connection,
    search: str,
    filters: dict[str, list[str]],
) -> dict[str, list[dict[str, Any]]]:
    """Build EUCLID-style facets.

    Each facet ignores its own active values but respects all other filters. This
    lets a user add a second family/genus value instead of the selected facet
    collapsing to one option. A production global deployment would calculate
    this in the indexed search service rather than issuing one query per facet.
    """
    all_rows = query_projection(connection, search, {})
    all_taxa = [projection_to_taxon(row) for row in all_rows]
    populated_keys = {
        definition["key"]
        for definition in definitions()
        if facet_counts(all_taxa, definition["key"])
    }
    output: dict[str, list[dict[str, Any]]] = {}
    for key in populated_keys:
        other_filters = {name: values for name, values in filters.items() if name != key}
        rows = query_projection(connection, search, other_filters)
        counts = facet_counts([projection_to_taxon(row) for row in rows], key)
        if counts:
            output[key] = counts
    return output


def metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for row in connection.execute("SELECT key, value_json FROM app_metadata"):
        output[row["key"]] = json.loads(row["value_json"])
    output["databasePath"] = str(DB_PATH.relative_to(ROOT))
    output["taxonCount"] = connection.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
    output["pendingReconciliations"] = connection.execute(
        "SELECT COUNT(*) FROM reconciliation_queue WHERE status = 'pending'"
    ).fetchone()[0]
    output["specialistConfirmedReconciliations"] = connection.execute(
        "SELECT COUNT(*) FROM reconciliation_queue WHERE status = 'specialist_confirmed'"
    ).fetchone()[0]
    output["enrichedTaxa"] = connection.execute(
        "SELECT COUNT(*) FROM taxon WHERE verification_status IN ('specialist_import', 'authoritative_import', 'expert_verified')"
    ).fetchone()[0]
    output["licensedMediaCount"] = connection.execute("SELECT COUNT(*) FROM media_asset").fetchone()[0]
    output["locallyStoredMediaCount"] = connection.execute(
        "SELECT COUNT(*) FROM media_asset WHERE storage_key IS NOT NULL AND storage_key != ''"
    ).fetchone()[0]
    output["profileShellCount"] = connection.execute(
        "SELECT COUNT(*) FROM taxon_search_projection WHERE profile_status = 'Seed shell only'"
    ).fetchone()[0]
    output["packCount"] = len(list(PACKS_DIR.glob("*/manifest.json"))) if PACKS_DIR.exists() else 0
    output["reviewDecisionCount"] = connection.execute("SELECT COUNT(*) FROM review_decision").fetchone()[0]
    output["filterDefinitionCount"] = connection.execute("SELECT COUNT(*) FROM trait_definition").fetchone()[0]
    return output


class DeckPreviewRequest(BaseModel):
    search: str = ""
    filters: dict[str, list[str]] = Field(default_factory=dict)
    size: int | str = "all"
    selectionMode: str = "random"
    progress: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ReconciliationDecisionRequest(BaseModel):
    decision: str
    rationale: str = ""
    reviewer: str = "ArbotFlash administrator"


app = FastAPI(
    title="ArbotFlash Development API",
    version="0.12.0",
    description="Database-backed development API for the separate ArbotFlash project.",
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    with connect() as connection:
        return {"status": "ok", "version": "0.12.0", **metadata(connection)}


@app.get("/api/bootstrap")
def bootstrap() -> dict[str, Any]:
    with connect() as connection:
        rows = query_projection(connection, "", {})
        taxa = [projection_to_taxon(row) for row in rows]
        return {
            "version": "0.12.0",
            "meta": metadata(connection),
            "definitions": definitions(),
            "taxa": taxa,
            "facets": build_facets(taxa),
        }


@app.get("/api/taxa")
def list_taxa(
    search: str = "",
    filter: list[str] = Query(default=[]),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    parsed = parse_filter_tokens(filter)
    with connect() as connection:
        rows = query_projection(connection, search, parsed)
        all_taxa = [projection_to_taxon(row) for row in rows]
        return {
            "count": len(all_taxa),
            "offset": offset,
            "limit": limit,
            "items": all_taxa[offset : offset + limit],
            "facets": build_disjunctive_facets(connection, search, parsed),
            "appliedFilters": parsed,
            "search": search,
        }


@app.get("/api/taxa/{taxon_id}")
def get_taxon(taxon_id: str) -> dict[str, Any]:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM taxon_search_projection WHERE taxon_id = ?", (taxon_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Taxon not found")
        taxon = projection_to_taxon(row)
        taxon_row = connection.execute("SELECT * FROM taxon WHERE id = ?", (taxon_id,)).fetchone()
        classifications = [dict(item) for item in connection.execute(
            "SELECT rank, name, verification_status FROM taxon_classification WHERE taxon_id = ? ORDER BY CASE rank WHEN 'domain' THEN 1 WHEN 'kingdom' THEN 2 WHEN 'phylum' THEN 3 WHEN 'class' THEN 4 WHEN 'order' THEN 5 WHEN 'family' THEN 6 WHEN 'genus' THEN 7 ELSE 99 END",
            (taxon_id,),
        )]
        names = [dict(item) for item in connection.execute(
            "SELECT name, authorship, status, language_code, region_code, verification_status FROM taxon_name WHERE taxon_id = ? ORDER BY status, name",
            (taxon_id,),
        )]
        sections = [dict(item) for item in connection.execute(
            "SELECT section_key, language_code, body_markdown, verification_status, assertion_status, licence_code, source_revision FROM profile_section WHERE taxon_id = ? ORDER BY section_key",
            (taxon_id,),
        )]
        citations = [dict(item) for item in connection.execute(
            """SELECT c.citation_text, c.source_url, c.retrieved_at, c.licence_code,
                      d.title AS source_title, r.release_key
               FROM source_citation c
               LEFT JOIN source_release r ON r.id = c.source_release_id
               LEFT JOIN source_dataset d ON d.id = r.source_dataset_id
               WHERE c.taxon_id = ? ORDER BY c.citation_text""",
            (taxon_id,),
        )]
        reconciliation = [dict(item) for item in connection.execute(
            """SELECT d.key AS source_key, d.title AS source_title, q.status,
                      q.searched_name, q.proposed_external_id,
                      q.proposed_scientific_name, q.proposed_rank,
                      q.confidence, q.notes, q.checked_at
               FROM reconciliation_queue q
               JOIN source_dataset d ON d.id = q.source_dataset_id
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
        return {
            **taxon,
            "canonicalRank": taxon_row["canonical_rank"],
            "sourceRecordIndex": taxon_row["source_record_index"],
            "classifications": classifications,
            "names": names,
            "profileSections": sections,
            "citations": citations,
            "reconciliation": reconciliation,
            "media": media,
        }


@app.get("/api/sources")
def list_sources() -> dict[str, Any]:
    with connect() as connection:
        rows = connection.execute(
            """SELECT d.key, d.title, d.publisher, d.homepage_url, d.licence_code,
                      d.licence_url, d.authority_role, d.enabled,
                      COUNT(r.id) AS release_count
               FROM source_dataset d
               LEFT JOIN source_release r ON r.source_dataset_id = d.id
               GROUP BY d.id ORDER BY d.authority_role, d.title"""
        ).fetchall()
        return {"items": [dict(row) for row in rows]}


@app.get("/api/reconciliation/summary")
def reconciliation_summary() -> dict[str, Any]:
    with connect() as connection:
        by_status = {
            row["status"]: row["count"]
            for row in connection.execute(
                "SELECT status, COUNT(*) AS count FROM reconciliation_queue GROUP BY status"
            )
        }
        by_source = [dict(row) for row in connection.execute(
            """SELECT d.key AS source_key, d.title AS source_title, q.status, COUNT(*) AS count
               FROM reconciliation_queue q
               JOIN source_dataset d ON d.id = q.source_dataset_id
               GROUP BY d.key, d.title, q.status ORDER BY d.key, q.status"""
        )]
        return {"byStatus": by_status, "bySource": by_source}


@app.get("/api/admin/overview")
def admin_overview() -> dict[str, Any]:
    with connect() as connection:
        queue_by_status = {
            row["status"]: row["count"]
            for row in connection.execute(
                "SELECT status, COUNT(*) AS count FROM reconciliation_queue GROUP BY status ORDER BY status"
            )
        }
        profile_counts = {
            row["verification_status"]: row["count"]
            for row in connection.execute(
                "SELECT verification_status, COUNT(DISTINCT taxon_id) AS count FROM profile_section GROUP BY verification_status"
            )
        }
        return {
            "version": "0.12.0",
            "meta": metadata(connection),
            "queueByStatus": queue_by_status,
            "profileTaxaByVerification": profile_counts,
            "writeModeConfigured": bool(os.getenv("ARBOTFLASH_ADMIN_TOKEN")),
            "sourceWarning": json.loads(
                connection.execute(
                    "SELECT value_json FROM app_metadata WHERE key = 'authority_slice_source_warning'"
                ).fetchone()[0]
            ),
        }


@app.get("/api/admin/reconciliation")
def admin_reconciliation(
    status: str | None = None,
    source: str | None = None,
    limit: int = Query(default=250, ge=1, le=1000),
) -> dict[str, Any]:
    clauses: list[str] = []
    parameters: list[Any] = []
    if status:
        clauses.append("q.status = ?")
        parameters.append(status)
    if source:
        clauses.append("d.key = ?")
        parameters.append(source)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connect() as connection:
        rows = connection.execute(
            f"""SELECT q.taxon_id, p.common_name, p.scientific_name,
                       d.key AS source_key, d.title AS source_title,
                       q.status, q.searched_name, q.proposed_external_id,
                       q.proposed_scientific_name, q.proposed_rank,
                       q.confidence, q.notes, q.checked_at,
                       (SELECT COUNT(*) FROM review_decision rd
                        WHERE rd.taxon_id = q.taxon_id
                          AND rd.source_dataset_id = q.source_dataset_id) AS decision_count
                FROM reconciliation_queue q
                JOIN source_dataset d ON d.id = q.source_dataset_id
                JOIN taxon_search_projection p ON p.taxon_id = q.taxon_id
                {where}
                ORDER BY CASE q.status
                    WHEN 'review_required' THEN 1 WHEN 'pending' THEN 2
                    WHEN 'deferred' THEN 3 WHEN 'specialist_confirmed' THEN 4
                    ELSE 5 END,
                    p.scientific_name COLLATE NOCASE, d.key
                LIMIT ?""",
            [*parameters, limit],
        ).fetchall()
        return {"count": len(rows), "items": [dict(row) for row in rows]}


@app.post("/api/admin/reconciliation/{taxon_id}/{source_key}/decision")
def decide_reconciliation(
    taxon_id: str,
    source_key: str,
    payload: ReconciliationDecisionRequest,
    x_arbotflash_admin_token: str | None = Header(default=None),
) -> dict[str, Any]:
    configured_token = os.getenv("ARBOTFLASH_ADMIN_TOKEN")
    if not configured_token:
        raise HTTPException(
            status_code=503,
            detail="Admin write mode is disabled. Set ARBOTFLASH_ADMIN_TOKEN to enable reviewed changes.",
        )
    if not x_arbotflash_admin_token or not secrets.compare_digest(
        configured_token, x_arbotflash_admin_token
    ):
        raise HTTPException(status_code=401, detail="Invalid administrator token")

    decision_to_status = {
        "approve": "approved",
        "reject": "rejected",
        "defer": "deferred",
    }
    if payload.decision not in decision_to_status:
        raise HTTPException(status_code=400, detail="Decision must be approve, reject or defer")
    new_status = decision_to_status[payload.decision]
    decided_at = datetime.now(timezone.utc).isoformat()

    with connect() as connection:
        row = connection.execute(
            """SELECT q.*, d.id AS dataset_id, d.key AS source_key
               FROM reconciliation_queue q
               JOIN source_dataset d ON d.id = q.source_dataset_id
               WHERE q.taxon_id = ? AND d.key = ?""",
            (taxon_id, source_key),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Reconciliation record not found")

        before = dict(row)
        connection.execute(
            """UPDATE reconciliation_queue SET status = ?, notes = ?, checked_at = ?
               WHERE taxon_id = ? AND source_dataset_id = ?""",
            (
                new_status,
                payload.rationale or row["notes"],
                decided_at,
                taxon_id,
                row["source_dataset_id"],
            ),
        )
        connection.execute(
            """INSERT INTO review_decision
               (id, taxon_id, source_dataset_id, decision, reviewer,
                rationale, previous_status, new_status, decided_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()), taxon_id, row["source_dataset_id"],
                payload.decision, payload.reviewer, payload.rationale,
                row["status"], new_status, decided_at,
            ),
        )
        if payload.decision == "approve" and row["proposed_external_id"]:
            connection.execute(
                """INSERT OR IGNORE INTO taxon_external_identifier
                   (taxon_id, source_dataset_id, external_id, source_release_id)
                   VALUES (?, ?, ?, NULL)""",
                (taxon_id, row["source_dataset_id"], row["proposed_external_id"]),
            )
        after = {**before, "status": new_status, "notes": payload.rationale or row["notes"], "checked_at": decided_at}
        connection.execute(
            """INSERT INTO audit_event
               (id, actor, action, entity_type, entity_id, before_json, after_json, created_at)
               VALUES (?, ?, 'reconciliation_decision', 'reconciliation_queue', ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()), payload.reviewer,
                f"{taxon_id}:{source_key}", json.dumps(before), json.dumps(after), decided_at,
            ),
        )
        from scripts.build_dev_db import rebuild_projection

        rebuild_projection(connection)
        connection.commit()
        return {
            "taxonId": taxon_id,
            "sourceKey": source_key,
            "previousStatus": row["status"],
            "status": new_status,
            "decision": payload.decision,
            "decidedAt": decided_at,
        }


@app.post("/api/decks/preview")
def preview_deck(payload: DeckPreviewRequest = Body(...)) -> dict[str, Any]:
    tokens = [f"{key}:{value}" for key, values in payload.filters.items() for value in values]
    parsed = parse_filter_tokens(tokens)
    with connect() as connection:
        rows = query_projection(connection, payload.search, parsed)
        taxa = [projection_to_taxon(row) for row in rows]

    def progress_for(taxon: dict[str, Any]) -> dict[str, Any]:
        return payload.progress.get(taxon["id"], {"attempts": 0, "correct": 0, "incorrect": 0})

    mode = payload.selectionMode
    if mode == "alphabetical":
        taxa.sort(key=lambda item: (item["scientificName"].casefold(), item["commonName"].casefold()))
    elif mode == "new":
        taxa = [item for item in taxa if int(progress_for(item).get("attempts", 0)) == 0]
        taxa.sort(key=lambda item: item["scientificName"].casefold())
    elif mode == "incorrect":
        taxa = [item for item in taxa if int(progress_for(item).get("incorrect", 0)) > 0]
        taxa.sort(key=lambda item: (-int(progress_for(item).get("incorrect", 0)), item["scientificName"].casefold()))
    elif mode == "least":
        taxa.sort(key=lambda item: (int(progress_for(item).get("attempts", 0)), item["scientificName"].casefold()))
    elif mode == "difficult":
        def difficulty(item: dict[str, Any]) -> tuple[float, str]:
            progress = progress_for(item)
            attempts = int(progress.get("attempts", 0))
            correct = int(progress.get("correct", 0))
            ratio = correct / attempts if attempts else 1.0
            return ratio, item["scientificName"].casefold()
        taxa.sort(key=difficulty)
    else:
        random.shuffle(taxa)

    requested_size = len(taxa) if payload.size == "all" else max(1, int(payload.size))
    deck = taxa[: min(requested_size, len(taxa))]
    return {
        "count": len(deck),
        "matchingCount": len(rows),
        "selectionMode": mode,
        "items": deck,
    }


def _pack_directory(pack_key: str) -> Path:
    if not pack_key or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for character in pack_key.lower()):
        raise HTTPException(status_code=400, detail="Invalid pack key")
    directory = (PACKS_DIR / pack_key).resolve()
    if PACKS_DIR.resolve() not in directory.parents:
        raise HTTPException(status_code=400, detail="Invalid pack key")
    if not (directory / "manifest.json").exists():
        raise HTTPException(status_code=404, detail="Offline pack not found")
    return directory


def _pack_manifest(directory: Path) -> dict[str, Any]:
    return json.loads((directory / "manifest.json").read_text(encoding="utf-8"))


@app.get("/api/packs")
def list_offline_packs() -> dict[str, Any]:
    items = []
    if PACKS_DIR.exists():
        for manifest_path in sorted(PACKS_DIR.glob("*/manifest.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            items.append({
                "packKey": manifest["packKey"],
                "title": manifest["title"],
                "version": manifest["version"],
                "taxonCount": manifest["coverage"]["taxonCount"],
                "enrichedTaxa": manifest["coverage"]["enrichedTaxa"],
                "profileShells": manifest["coverage"]["profileShells"],
                "localMediaCount": manifest["coverage"]["localMediaCount"],
                "downloadUrl": manifest.get("downloadUrl"),
                "generatedAt": manifest["generatedAt"],
            })
    return {"count": len(items), "items": items}


@app.get("/api/packs/{pack_key}/manifest")
def get_offline_pack_manifest(pack_key: str) -> dict[str, Any]:
    return _pack_manifest(_pack_directory(pack_key))


@app.get("/api/packs/{pack_key}/taxa")
def get_offline_pack_taxa(pack_key: str) -> Any:
    directory = _pack_directory(pack_key)
    return json.loads((directory / "taxa.json").read_text(encoding="utf-8"))


@app.get("/api/packs/{pack_key}/profiles")
def get_offline_pack_profiles(pack_key: str) -> Any:
    directory = _pack_directory(pack_key)
    return json.loads((directory / "profiles.json").read_text(encoding="utf-8"))


@app.get("/api/packs/{pack_key}/download")
def download_offline_pack(pack_key: str) -> FileResponse:
    directory = _pack_directory(pack_key)
    manifest = _pack_manifest(directory)
    archive = directory / manifest["archiveFile"]
    if not archive.exists():
        raise HTTPException(status_code=404, detail="Offline pack archive has not been built")
    return FileResponse(archive, media_type="application/zip", filename=archive.name)


@app.exception_handler(sqlite3.DatabaseError)
def database_error_handler(_, exc: sqlite3.DatabaseError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": f"Database error: {exc}"})


if ADMIN_DIR.exists():
    app.mount("/admin", StaticFiles(directory=ADMIN_DIR, html=True), name="admin")
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.api.main:app", host="127.0.0.1", port=8080, reload=False)
