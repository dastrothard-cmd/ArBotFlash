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
sys.path.insert(0, str(ROOT))
from apps.api.main import app  # noqa: E402

ENRICHMENT = ROOT / "data" / "enrichment" / "authority-slice-80.json"
FINAL_TEN = {
    "treeid-acacia-websteriana": ("Acacia websteriana", "Acacia websteri"),
    "treeid-corymbia-eximia": ("Corymbia eximia", None),
    "treeid-eucalyptus-norsemanica": ("Eucalyptus norsemanica", "Eucalyptus websteriana"),
    "treeid-lophostemon-confertus": ("Lophostemon confertus", None),
    "treeid-platanus-acerifolia": ("Platanus × acerifolia", None),
    "treeid-populus-alba": ("Populus alba", None),
    "treeid-syzygium-australe": ("Syzygium australe", None),
    "treeid-tristaniopsis-laurina": ("Tristaniopsis laurina", None),
    "treeid-ulmus-procera": ("Ulmus procera", None),
    "treeid-washingtonia-robusta": ("Washingtonia robusta", None),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


enrichment = json.loads(ENRICHMENT.read_text(encoding="utf-8"))
assert enrichment["sliceKey"] == "authority-slice-80"
assert len(enrichment["records"]) == 80
assert len({r["taxonId"] for r in enrichment["records"]}) == 80

with sqlite3.connect(DB) as connection:
    connection.row_factory = sqlite3.Row
    assert connection.execute("SELECT COUNT(*) FROM taxon").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM taxon_search_projection WHERE profile_status = 'Partially enriched'").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM taxon_search_projection WHERE profile_status = 'Seed shell only'").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM media_asset").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM media_taxon").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM review_decision").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM reconciliation_queue WHERE status = 'specialist_confirmed'").fetchone()[0] == 80
    schema = json.loads(connection.execute("SELECT value_json FROM app_metadata WHERE key = 'schema_version'").fetchone()[0])
    assert schema == "0.12.0"

    for taxon_id, (study_name, accepted_name) in FINAL_TEN.items():
        projection = connection.execute("SELECT * FROM taxon_search_projection WHERE taxon_id = ?", (taxon_id,)).fetchone()
        assert projection is not None
        assert projection["scientific_name"] == study_name
        assert projection["profile_status"] == "Partially enriched"
        assert projection["image_status"] == "Available"
        assert connection.execute("SELECT canonical_scientific_name FROM taxon WHERE id = ?", (taxon_id,)).fetchone()[0] == study_name
        names = {(r["name"], r["status"]) for r in connection.execute("SELECT name, status FROM taxon_name WHERE taxon_id = ?", (taxon_id,))}
        assert (study_name, "accepted_study_name") in names
        if accepted_name:
            assert (accepted_name, "accepted_regional_name") in names

    for row in connection.execute("SELECT storage_key, creator, licence_code, source_page_url, metadata_json FROM media_asset"):
        assert row["creator"] and row["licence_code"] and row["source_page_url"]
        media_file = ROOT / "apps" / "web" / row["storage_key"].lstrip("/")
        assert media_file.exists() and media_file.stat().st_size > 1000
        metadata = json.loads(row["metadata_json"])
        assert metadata["locally_stored"] is True
        assert metadata["licence_verified"] is True
        assert metadata["local_sha256"] == sha256(media_file)

manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
assert manifest["version"] == "0.12.0"
assert manifest["coverage"] == {
    "taxonCount": 80,
    "enrichedTaxa": 80,
    "profileShells": 0,
    "localMediaCount": 80,
    "taxonomyStatus": "Specialist regional evidence for 80 taxa; global and national reconciliation remains queued.",
}
taxa = json.loads((PACK / "taxa.json").read_text(encoding="utf-8"))
profiles = json.loads((PACK / "profiles.json").read_text(encoding="utf-8"))
attributions = json.loads((PACK / "attributions.json").read_text(encoding="utf-8"))
assert len(taxa) == len(profiles) == len(attributions) == 80
assert sum(item["profileStatus"] == "Partially enriched" for item in taxa) == 80
assert sum(bool(profile["media"]) for profile in profiles.values()) == 80
for record in manifest["files"]:
    path = PACK / record["path"]
    assert path.exists() and path.stat().st_size == record["bytes"]
    assert sha256(path) == record["sha256"]

archive = PACK / manifest["archiveFile"]
assert archive.name == "arbotflash-tree-id-80-v0.12.0.zip"
assert sha256(archive) == (PACK / f"{archive.name}.sha256").read_text().split()[0]
with zipfile.ZipFile(archive) as zipped:
    names = set(zipped.namelist())
    assert "tree-id-80/manifest.json" in names
    assert len([n for n in names if n.startswith("tree-id-80/media/") and n.endswith(".jpg")]) == 80

client = TestClient(app)
health = client.get("/api/health")
assert health.status_code == 200
health_data = health.json()
assert health_data["version"] == "0.12.0"
assert health_data["enrichedTaxa"] == 80
assert health_data["licensedMediaCount"] == 80
assert health_data["locallyStoredMediaCount"] == 80
assert health_data["profileShellCount"] == 0
assert health_data["reviewDecisionCount"] == 80
assert health_data["specialistConfirmedReconciliations"] == 80
for taxon_id in FINAL_TEN:
    response = client.get(f"/api/taxa/{taxon_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["profileStatus"] == "Partially enriched"
    assert payload["media"][0]["storage_key"] == f"/media/thumbs/{taxon_id}.jpg"
    media_response = client.get(payload["media"][0]["storage_key"])
    assert media_response.status_code == 200 and len(media_response.content) > 1000
assert client.get("/api/packs/tree-id-80/manifest").json()["coverage"]["enrichedTaxa"] == 80
assert len(client.get("/api/packs/tree-id-80/download").content) == archive.stat().st_size

service_worker = (ROOT / "apps" / "web" / "sw.js").read_text(encoding="utf-8")
assert "arbotflash-v0-12-authority-slice-80" in service_worker
assert service_worker.count("./media/thumbs/") == 80
for phrase in ("grip formulation", "adhesion testing", "friction testing", "hand application", "wa grip"):
    assert phrase not in json.dumps(enrichment).casefold()

print("ArbotFlash v0.12 validation passed: 80 taxa, 80 sourced profiles, 80 reviewed local images, zero transparent shells, accepted-name separation, manifests and API routes verified.")
