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
ENRICHMENT = ROOT / "data" / "enrichment" / "wa-authority-slice-20.json"
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
assert enrichment["sliceKey"] == "wa-authority-slice-20"
assert len(enrichment["records"]) == 20
assert len({record["taxonId"] for record in enrichment["records"]}) == 20
assert len({record["externalIdentifiers"]["florabase"] for record in enrichment["records"]}) == 20

expected_new = {
    "treeid-acacia-acuminata",
    "treeid-acacia-cyclops",
    "treeid-acacia-saligna",
    "treeid-banksia-grandis",
    "treeid-banksia-ilicifolia",
    "treeid-banksia-littoralis",
    "treeid-banksia-menziesii",
    "treeid-banksia-prionotes",
    "treeid-eucalyptus-accedens",
    "treeid-eucalyptus-patens",
}
assert expected_new <= {record["taxonId"] for record in enrichment["records"]}

with sqlite3.connect(DB) as connection:
    connection.row_factory = sqlite3.Row
    assert connection.execute("SELECT COUNT(*) FROM taxon").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM taxon_name").fetchone()[0] == 180
    assert connection.execute("SELECT COUNT(*) FROM taxon WHERE verification_status = 'specialist_import'").fetchone()[0] == 20
    assert connection.execute("SELECT COUNT(*) FROM media_asset").fetchone()[0] == 20
    assert connection.execute("SELECT COUNT(*) FROM media_asset WHERE storage_key IS NOT NULL").fetchone()[0] == 20
    assert connection.execute("SELECT COUNT(*) FROM review_decision").fetchone()[0] == 20
    assert connection.execute("SELECT COUNT(*) FROM audit_event").fetchone()[0] == 20
    assert connection.execute("SELECT COUNT(DISTINCT taxon_id) FROM profile_section WHERE verification_status = 'specialist_import'").fetchone()[0] == 20
    assert connection.execute("SELECT COUNT(*) FROM profile_section WHERE verification_status = 'specialist_import'").fetchone()[0] >= 140
    assert connection.execute("SELECT COUNT(*) FROM taxon_search_projection WHERE profile_status = 'Seed shell only'").fetchone()[0] == 60
    assert connection.execute(
        """SELECT COUNT(*) FROM taxon_external_identifier e
           JOIN source_dataset d ON d.id = e.source_dataset_id
           WHERE d.key = 'florabase'"""
    ).fetchone()[0] == 20
    assert connection.execute(
        """SELECT COUNT(*) FROM reconciliation_queue q
           JOIN source_dataset d ON d.id = q.source_dataset_id
           WHERE d.key = 'florabase' AND q.status = 'specialist_confirmed'"""
    ).fetchone()[0] == 20
    assert json.loads(connection.execute(
        "SELECT value_json FROM app_metadata WHERE key = 'schema_version'"
    ).fetchone()[0]) == "0.6.0"
    assert json.loads(connection.execute(
        "SELECT value_json FROM app_metadata WHERE key = 'authority_slice_record_count'"
    ).fetchone()[0]) == 20
    for row in connection.execute("SELECT storage_key, creator, licence_code, source_page_url, metadata_json FROM media_asset"):
        assert row["creator"] and row["licence_code"] and row["source_page_url"]
        media_file = ROOT / "apps" / "web" / row["storage_key"].lstrip("/")
        assert media_file.exists() and media_file.stat().st_size > 1000
        metadata = json.loads(row["metadata_json"])
        assert metadata["locally_stored"] is True
        assert metadata["licence_verified"] is True
        assert metadata["local_sha256"] == sha256(media_file)

manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
assert manifest["version"] == "0.6.0"
assert manifest["coverage"] == {
    "taxonCount": 80,
    "enrichedTaxa": 20,
    "profileShells": 60,
    "localMediaCount": 20,
    "taxonomyStatus": "Specialist regional evidence for 20 taxa; global and national reconciliation remains queued.",
}

taxa = json.loads((PACK / "taxa.json").read_text(encoding="utf-8"))
profiles = json.loads((PACK / "profiles.json").read_text(encoding="utf-8"))
attributions = json.loads((PACK / "attributions.json").read_text(encoding="utf-8"))
assert len(taxa) == 80 and len(profiles) == 80
assert sum(item["profileStatus"] == "Partially enriched" for item in taxa) == 20
assert sum(item["profileStatus"] == "Seed shell only" for item in taxa) == 60
assert sum(bool(profile["media"]) for profile in profiles.values()) == 20
assert len(attributions) == 20
for record in manifest["files"]:
    path = PACK / record["path"]
    assert path.exists()
    assert path.stat().st_size == record["bytes"]
    assert sha256(path) == record["sha256"]

archive = PACK / manifest["archiveFile"]
assert archive.name == "arbotflash-tree-id-80-v0.6.0.zip"
assert archive.exists()
with zipfile.ZipFile(archive) as zipped:
    names = set(zipped.namelist())
    assert "tree-id-80/manifest.json" in names
    assert "tree-id-80/taxa.json" in names
    assert "tree-id-80/profiles.json" in names
    assert len([name for name in names if name.startswith("tree-id-80/media/") and name.endswith(".jpg")]) == 20

client = TestClient(app)
health = client.get("/api/health")
assert health.status_code == 200
health_data = health.json()
assert health_data["version"] == "0.6.0"
assert health_data["enrichedTaxa"] == 20
assert health_data["licensedMediaCount"] == 20
assert health_data["locallyStoredMediaCount"] == 20
assert health_data["profileShellCount"] == 60
assert health_data["reviewDecisionCount"] == 20
assert health_data["specialistConfirmedReconciliations"] == 20

blackbutt = client.get("/api/taxa/treeid-eucalyptus-patens")
assert blackbutt.status_code == 200
blackbutt_data = blackbutt.json()
assert blackbutt_data["verification"] == "Specialist import"
assert blackbutt_data["profileStatus"] == "Partially enriched"
assert any(name["authorship"] == "Benth." for name in blackbutt_data["names"])
assert len(blackbutt_data["profileSections"]) >= 7
assert blackbutt_data["media"][0]["licence_code"] == "CC-BY-SA-4.0"
assert blackbutt_data["media"][0]["creator"] == "Geoff Derrin"
assert blackbutt_data["media"][0]["storage_key"] == "/media/thumbs/treeid-eucalyptus-patens.jpg"

wa = client.get("/api/taxa", params=[("filter", "country:Australia"), ("limit", "500")])
assert wa.status_code == 200 and wa.json()["count"] == 20
wet = client.get("/api/taxa", params=[("filter", "habitat:Seasonally damp areas"), ("limit", "500")])
assert wet.status_code == 200
assert [item["id"] for item in wet.json()["items"]] == ["treeid-banksia-littoralis"]
assert client.get("/api/packs/tree-id-80/manifest").json()["coverage"]["enrichedTaxa"] == 20
assert len(client.get("/api/packs/tree-id-80/taxa").json()) == 80
assert len(client.get("/api/packs/tree-id-80/profiles").json()) == 80
assert len(client.get("/api/packs/tree-id-80/download").content) == archive.stat().st_size

service_worker = (ROOT / "apps" / "web" / "sw.js").read_text(encoding="utf-8")
assert "arbotflash-v0-6-authority-slice-20" in service_worker
assert service_worker.count("./media/thumbs/") == 20
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

print("ArbotFlash v0.6 validation passed: 80 seed taxa, 20 curated authority profiles, 20 local licensed images, 60 transparent shells, reviewed evidence and regenerated offline pack verified.")
