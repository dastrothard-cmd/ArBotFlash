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
ENRICHMENT = ROOT / "data" / "enrichment" / "wa-authority-slice-50.json"
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
assert enrichment["sliceKey"] == "wa-authority-slice-50"
assert len(enrichment["records"]) == 50
assert len({record["taxonId"] for record in enrichment["records"]}) == 50
assert len({record["externalIdentifiers"]["florabase"] for record in enrichment["records"]}) == 50

expected_new = {
    "treeid-callitris-columellaris",
    "treeid-corymbia-maculata",
    "treeid-eucalyptus-cladocalyx",
    "treeid-eucalyptus-grandis",
    "treeid-melaleuca-quinquenervia",
    "treeid-corymbia-citriodora",
    "treeid-casuarina-cunninghamiana",
    "treeid-callistemon-viminalis",
    "treeid-pinus-radiata",
    "treeid-pinus-pinea",
}
assert expected_new <= {record["taxonId"] for record in enrichment["records"]}

with sqlite3.connect(DB) as connection:
    connection.row_factory = sqlite3.Row
    assert connection.execute("SELECT COUNT(*) FROM taxon").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM taxon_name").fetchone()[0] == 210
    assert connection.execute("SELECT COUNT(*) FROM taxon WHERE verification_status = 'specialist_import'").fetchone()[0] == 50
    assert connection.execute("SELECT COUNT(*) FROM media_asset").fetchone()[0] == 50
    assert connection.execute("SELECT COUNT(*) FROM media_asset WHERE storage_key IS NOT NULL").fetchone()[0] == 50
    assert connection.execute("SELECT COUNT(*) FROM review_decision").fetchone()[0] == 50
    assert connection.execute("SELECT COUNT(*) FROM audit_event").fetchone()[0] == 50
    assert connection.execute("SELECT COUNT(DISTINCT taxon_id) FROM profile_section WHERE verification_status = 'specialist_import'").fetchone()[0] == 50
    assert connection.execute("SELECT COUNT(*) FROM profile_section WHERE verification_status = 'specialist_import'").fetchone()[0] >= 350
    assert connection.execute("SELECT COUNT(*) FROM taxon_search_projection WHERE profile_status = 'Seed shell only'").fetchone()[0] == 30
    assert connection.execute(
        """SELECT COUNT(*) FROM taxon_external_identifier e
           JOIN source_dataset d ON d.id = e.source_dataset_id
           WHERE d.key = 'florabase'"""
    ).fetchone()[0] == 50
    assert connection.execute(
        """SELECT COUNT(*) FROM reconciliation_queue q
           JOIN source_dataset d ON d.id = q.source_dataset_id
           WHERE d.key = 'florabase' AND q.status = 'specialist_confirmed'"""
    ).fetchone()[0] == 50
    assert json.loads(connection.execute(
        "SELECT value_json FROM app_metadata WHERE key = 'schema_version'"
    ).fetchone()[0]) == "0.10.0"
    assert json.loads(connection.execute(
        "SELECT value_json FROM app_metadata WHERE key = 'authority_slice_record_count'"
    ).fetchone()[0]) == 50
    for row in connection.execute("SELECT storage_key, creator, licence_code, source_page_url, metadata_json FROM media_asset"):
        assert row["creator"] and row["licence_code"] and row["source_page_url"]
        media_file = ROOT / "apps" / "web" / row["storage_key"].lstrip("/")
        assert media_file.exists() and media_file.stat().st_size > 1000
        metadata = json.loads(row["metadata_json"])
        assert metadata["locally_stored"] is True
        assert metadata["licence_verified"] is True
        assert metadata["local_sha256"] == sha256(media_file)

manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
assert manifest["version"] == "0.10.0"
assert manifest["coverage"] == {
    "taxonCount": 80,
    "enrichedTaxa": 50,
    "profileShells": 30,
    "localMediaCount": 50,
    "taxonomyStatus": "Specialist regional evidence for 50 taxa; global and national reconciliation remains queued.",
}

taxa = json.loads((PACK / "taxa.json").read_text(encoding="utf-8"))
profiles = json.loads((PACK / "profiles.json").read_text(encoding="utf-8"))
attributions = json.loads((PACK / "attributions.json").read_text(encoding="utf-8"))
assert len(taxa) == 80 and len(profiles) == 80
assert sum(item["profileStatus"] == "Partially enriched" for item in taxa) == 50
assert sum(item["profileStatus"] == "Seed shell only" for item in taxa) == 30
assert sum(bool(profile["media"]) for profile in profiles.values()) == 50
assert len(attributions) == 50
for record in manifest["files"]:
    path = PACK / record["path"]
    assert path.exists()
    assert path.stat().st_size == record["bytes"]
    assert sha256(path) == record["sha256"]

archive = PACK / manifest["archiveFile"]
assert archive.name == "arbotflash-tree-id-80-v0.10.0.zip"
assert archive.exists()
with zipfile.ZipFile(archive) as zipped:
    names = set(zipped.namelist())
    assert "tree-id-80/manifest.json" in names
    assert "tree-id-80/taxa.json" in names
    assert "tree-id-80/profiles.json" in names
    assert len([name for name in names if name.startswith("tree-id-80/media/") and name.endswith(".jpg")]) == 50

client = TestClient(app)
health = client.get("/api/health")
assert health.status_code == 200
health_data = health.json()
assert health_data["version"] == "0.10.0"
assert health_data["enrichedTaxa"] == 50
assert health_data["licensedMediaCount"] == 50
assert health_data["locallyStoredMediaCount"] == 50
assert health_data["profileShellCount"] == 30
assert health_data["reviewDecisionCount"] == 50
assert health_data["specialistConfirmedReconciliations"] == 50

callistemon = client.get("/api/taxa/treeid-callistemon-viminalis")
assert callistemon.status_code == 200
callistemon_data = callistemon.json()
assert callistemon_data["verification"] == "Specialist import"
assert callistemon_data["profileStatus"] == "Partially enriched"
name_pairs = {(name["name"], name["status"]) for name in callistemon_data["names"]}
assert ("Callistemon viminalis", "accepted_study_name") in name_pairs
assert ("Melaleuca viminalis", "accepted_regional_name") in name_pairs
assert len(callistemon_data["profileSections"]) >= 8
assert callistemon_data["media"][0]["licence_code"] == "CC-BY-SA-2.0"
assert callistemon_data["media"][0]["creator"] == "Ton Rulkens"
assert callistemon_data["media"][0]["storage_key"] == "/media/thumbs/treeid-callistemon-viminalis.jpg"

wa = client.get("/api/taxa", params=[("filter", "country:Australia"), ("limit", "500")])
assert wa.status_code == 200 and wa.json()["count"] == 50
introduced = client.get("/api/taxa", params=[("filter", "establishment:Introduced"), ("limit", "500")])
assert introduced.status_code == 200
assert "treeid-pinus-radiata" in {item["id"] for item in introduced.json()["items"]}
assert client.get("/api/packs/tree-id-80/manifest").json()["coverage"]["enrichedTaxa"] == 50
assert len(client.get("/api/packs/tree-id-80/taxa").json()) == 80
assert len(client.get("/api/packs/tree-id-80/profiles").json()) == 80
assert len(client.get("/api/packs/tree-id-80/download").content) == archive.stat().st_size

service_worker = (ROOT / "apps" / "web" / "sw.js").read_text(encoding="utf-8")
assert "arbotflash-v0-9-authority-slice-50" in service_worker
assert service_worker.count("./media/thumbs/") == 50
manifest_web = json.loads((ROOT / "apps" / "web" / "manifest.webmanifest").read_text(encoding="utf-8"))
assert manifest_web["id"] == "/arbotflash/"
offline_db = (ROOT / "apps" / "web" / "offline-db.js").read_text(encoding="utf-8")
assert "arbotflash-offline-v0-5" in offline_db  # schema intentionally preserved

for record in enrichment["records"]:
    assert record["source"]["url"].startswith("https://florabase.dbca.wa.gov.au/")
    assert record["media"]
    for media in record["media"]:
        assert media["creator"] and media["licenceCode"] and media["sourcePageUrl"]
    forbidden = json.dumps(record).casefold()
    for phrase in ("grip formulation", "adhesion testing", "friction testing", "hand application", "wa grip"):
        assert phrase not in forbidden

print("ArbotFlash v0.9 validation passed: 80 seed taxa, 50 curated authority profiles, 50 local licensed images, 30 transparent shells, reviewed evidence and regenerated offline pack verified.")
