#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "dev" / "arbotflash-dev.sqlite3"
PACK = ROOT / "packs" / "tree-id-80"
ENRICHMENT = ROOT / "data" / "enrichment" / "authority-slice-70.json"
sys.path.insert(0, str(ROOT))

from apps.api.main import app  # noqa: E402
from scripts.build_dev_db import build  # noqa: E402
from scripts.build_offline_pack import main as build_pack  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


build(DB)
build_pack()
enrichment = json.loads(ENRICHMENT.read_text(encoding="utf-8"))
assert enrichment["sliceKey"] == "authority-slice-70"
assert len(enrichment["records"]) == 70
assert len({record["taxonId"] for record in enrichment["records"]}) == 70

new_ids = {
    "treeid-allocasuarina-littoralis",
    "treeid-angophora-costata",
    "treeid-callistemon-citrinus",
    "treeid-cinnamomum-camphora",
    "treeid-cupressus-sempervirens",
    "treeid-eucalyptus-sideroxylon",
    "treeid-fraxinus-angustifolia",
    "treeid-fraxinus-excelsior",
    "treeid-grevillea-robusta",
    "treeid-liquidambar-styraciflua",
}
records_by_id = {record["taxonId"]: record for record in enrichment["records"]}
assert new_ids <= records_by_id.keys()
for taxon_id in new_ids:
    record = records_by_id[taxon_id]
    assert record["source"]["key"] == "wikipedia"
    assert record["source"]["citation"]
    assert len(record.get("secondarySources", [])) == 1
    assert record["secondarySources"][0]["key"] == "plants_of_the_world_online"
    assert record["media"][0]["creator"]
    assert record["media"][0]["licenceCode"]
    assert record["media"][0]["sourcePageUrl"].startswith("https://commons.wikimedia.org/wiki/File:")

with sqlite3.connect(DB) as connection:
    connection.row_factory = sqlite3.Row
    assert connection.execute("SELECT COUNT(*) FROM taxon").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM taxon WHERE verification_status = 'specialist_import'").fetchone()[0] == 70
    assert connection.execute("SELECT COUNT(*) FROM media_asset").fetchone()[0] == 70
    assert connection.execute("SELECT COUNT(*) FROM media_asset WHERE storage_key IS NOT NULL").fetchone()[0] == 70
    assert connection.execute("SELECT COUNT(*) FROM review_decision").fetchone()[0] == 70
    assert connection.execute("SELECT COUNT(*) FROM audit_event").fetchone()[0] == 70
    assert connection.execute("SELECT COUNT(DISTINCT taxon_id) FROM profile_section WHERE verification_status = 'specialist_import'").fetchone()[0] == 70
    assert connection.execute("SELECT COUNT(*) FROM taxon_search_projection WHERE profile_status = 'Seed shell only'").fetchone()[0] == 10
    assert json.loads(connection.execute("SELECT value_json FROM app_metadata WHERE key = 'schema_version'").fetchone()[0]) == "0.11.0"
    assert json.loads(connection.execute("SELECT value_json FROM app_metadata WHERE key = 'authority_slice_record_count'").fetchone()[0]) == 70

    powo_ids = connection.execute(
        """SELECT COUNT(*) FROM taxon_external_identifier e
           JOIN source_dataset d ON d.id = e.source_dataset_id
           WHERE d.key = 'plants_of_the_world_online'"""
    ).fetchone()[0]
    powo_citations = connection.execute(
        """SELECT COUNT(*) FROM source_citation c
           JOIN source_release r ON r.id = c.source_release_id
           JOIN source_dataset d ON d.id = r.source_dataset_id
           WHERE d.key = 'plants_of_the_world_online'"""
    ).fetchone()[0]
    assert powo_ids == 10
    assert powo_citations == 10

    for taxon_id, study_name, accepted_name in [
        ("treeid-callistemon-citrinus", "Callistemon citrinus", "Melaleuca citrina"),
        ("treeid-cinnamomum-camphora", "Cinnamomum camphora", "Camphora officinarum"),
    ]:
        names = {(row["name"], row["status"]) for row in connection.execute(
            "SELECT name, status FROM taxon_name WHERE taxon_id = ?", (taxon_id,)
        )}
        assert (study_name, "accepted_study_name") in names
        assert (accepted_name, "accepted_regional_name") in names
        assert connection.execute("SELECT canonical_scientific_name FROM taxon WHERE id = ?", (taxon_id,)).fetchone()[0] == study_name

    for row in connection.execute("SELECT storage_key, creator, licence_code, source_page_url, metadata_json FROM media_asset"):
        assert row["creator"] and row["licence_code"] and row["source_page_url"]
        media_file = ROOT / "apps" / "web" / row["storage_key"].lstrip("/")
        assert media_file.exists() and media_file.stat().st_size > 1000
        metadata = json.loads(row["metadata_json"])
        assert metadata["locally_stored"] is True
        assert metadata["licence_verified"] is True
        assert metadata["local_sha256"] == sha256(media_file)

manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
assert manifest["version"] == "0.11.0"
assert manifest["coverage"] == {
    "taxonCount": 80,
    "enrichedTaxa": 70,
    "profileShells": 10,
    "localMediaCount": 70,
    "taxonomyStatus": "Specialist regional evidence for 70 taxa; global and national reconciliation remains queued.",
}
taxa = json.loads((PACK / "taxa.json").read_text(encoding="utf-8"))
profiles = json.loads((PACK / "profiles.json").read_text(encoding="utf-8"))
attributions = json.loads((PACK / "attributions.json").read_text(encoding="utf-8"))
assert len(taxa) == 80 and len(profiles) == 80
assert sum(item["profileStatus"] == "Partially enriched" for item in taxa) == 70
assert sum(item["profileStatus"] == "Seed shell only" for item in taxa) == 10
assert sum(bool(profile["media"]) for profile in profiles.values()) == 70
assert len(attributions) == 70
for record in manifest["files"]:
    path = PACK / record["path"]
    assert path.exists() and path.stat().st_size == record["bytes"]
    assert sha256(path) == record["sha256"]

archive = PACK / manifest["archiveFile"]
assert archive.name == "arbotflash-tree-id-80-v0.11.0.zip"
with zipfile.ZipFile(archive) as zipped:
    names = set(zipped.namelist())
    assert "tree-id-80/manifest.json" in names
    assert len([name for name in names if name.startswith("tree-id-80/media/") and name.endswith(".jpg")]) == 70

client = TestClient(app)
health = client.get("/api/health")
assert health.status_code == 200
health_data = health.json()
assert health_data["version"] == "0.11.0"
assert health_data["enrichedTaxa"] == 70
assert health_data["licensedMediaCount"] == 70
assert health_data["locallyStoredMediaCount"] == 70
assert health_data["profileShellCount"] == 10
assert health_data["reviewDecisionCount"] == 70
assert health_data["specialistConfirmedReconciliations"] == 70

for taxon_id in ("treeid-callistemon-citrinus", "treeid-cinnamomum-camphora", "treeid-eucalyptus-sideroxylon"):
    response = client.get(f"/api/taxa/{taxon_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["profileStatus"] == "Partially enriched"
    assert payload["media"][0]["storage_key"] == f"/media/thumbs/{taxon_id}.jpg"
    assert any(citation["source_title"].startswith("Plants of the World Online") for citation in payload["citations"])

assert client.get("/api/packs/tree-id-80/manifest").json()["coverage"]["enrichedTaxa"] == 70
assert len(client.get("/api/packs/tree-id-80/download").content) == archive.stat().st_size

service_worker = (ROOT / "apps" / "web" / "sw.js").read_text(encoding="utf-8")
assert "arbotflash-v0-11-authority-slice-70" in service_worker
assert service_worker.count("./media/thumbs/") == 70
manifest_web = json.loads((ROOT / "apps" / "web" / "manifest.webmanifest").read_text(encoding="utf-8"))
assert manifest_web["id"] == "/arbotflash/"
offline_db = (ROOT / "apps" / "web" / "offline-db.js").read_text(encoding="utf-8")
assert "arbotflash-offline-v0-5" in offline_db

for phrase in ("grip formulation", "adhesion testing", "friction testing", "hand application", "wa grip"):
    assert phrase not in json.dumps(enrichment).casefold()

print("ArbotFlash v0.11 validation passed: 80 taxa, 70 enriched profiles, 70 reviewed local images, 10 transparent shells, accepted-name mappings and POWO source separation verified.")
