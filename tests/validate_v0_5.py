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

with sqlite3.connect(DB) as connection:
    connection.row_factory = sqlite3.Row
    assert connection.execute("SELECT COUNT(*) FROM taxon").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM media_asset").fetchone()[0] >= 10
    assert connection.execute("SELECT COUNT(*) FROM media_asset WHERE storage_key IS NOT NULL").fetchone()[0] >= 10
    for row in connection.execute("SELECT storage_key, metadata_json FROM media_asset"):
        media_file = ROOT / "apps" / "web" / row["storage_key"].lstrip("/")
        assert media_file.exists() and media_file.stat().st_size > 1000
        metadata = json.loads(row["metadata_json"])
        assert metadata["locally_stored"] is True
        assert metadata["local_sha256"] == sha256(media_file)
    assert connection.execute("SELECT COUNT(*) FROM taxon_search_projection WHERE profile_status = 'Seed shell only'").fetchone()[0] <= 70

manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
assert manifest["version"] in {"0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.10.0", "0.11.0", "0.12.0"}
assert manifest["coverage"]["taxonCount"] == 80
assert manifest["coverage"]["enrichedTaxa"] >= 10
assert manifest["coverage"]["profileShells"] <= 70
assert manifest["coverage"]["localMediaCount"] >= 10
assert "global and national reconciliation remains queued" in manifest["coverage"]["taxonomyStatus"]
taxa = json.loads((PACK / "taxa.json").read_text(encoding="utf-8"))
profiles = json.loads((PACK / "profiles.json").read_text(encoding="utf-8"))
assert len(taxa) == 80 and len(profiles) == 80
assert sum(item["profileStatus"] == "Seed shell only" for item in taxa) <= 70
assert sum(bool(profile["media"]) for profile in profiles.values()) >= 10
for record in manifest["files"]:
    path = PACK / record["path"]
    assert path.exists()
    assert path.stat().st_size == record["bytes"]
    assert sha256(path) == record["sha256"]

archive = PACK / manifest["archiveFile"]
assert archive.exists()
with zipfile.ZipFile(archive) as zipped:
    names = set(zipped.namelist())
    assert "tree-id-80/taxa.json" in names
    assert "tree-id-80/profiles.json" in names
    assert "tree-id-80/manifest.json" in names
    assert len([name for name in names if name.startswith("tree-id-80/media/") and name.endswith(".jpg")]) >= 10

client = TestClient(app)
health = client.get("/api/health")
assert health.status_code == 200
health_data = health.json()
assert health_data["version"] in {"0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.10.0", "0.11.0", "0.12.0"}
assert health_data["locallyStoredMediaCount"] >= 10
assert health_data["profileShellCount"] <= 70
assert health_data["packCount"] == 1

jarrah = client.get("/api/taxa/treeid-eucalyptus-marginata").json()
assert jarrah["media"][0]["display_url"] == "/media/thumbs/treeid-eucalyptus-marginata.jpg"
assert jarrah["media"][0]["storage_key"] == "/media/thumbs/treeid-eucalyptus-marginata.jpg"
assert jarrah["media"][0]["original_url"].startswith("https://commons.wikimedia.org/")

packs = client.get("/api/packs").json()
assert packs["count"] == 1 and packs["items"][0]["taxonCount"] == 80
assert client.get("/api/packs/tree-id-80/manifest").json()["coverage"]["profileShells"] <= 70
assert len(client.get("/api/packs/tree-id-80/taxa").json()) == 80
assert len(client.get("/api/packs/tree-id-80/profiles").json()) == 80
download = client.get("/api/packs/tree-id-80/download")
assert download.status_code == 200 and len(download.content) == archive.stat().st_size
assert client.get("/api/packs/../../etc/passwd/manifest").status_code in {404, 422}

web_js = (ROOT / "apps" / "web" / "offline-db.js").read_text(encoding="utf-8")
assert "arbotflash-offline-v0-5" in web_js
assert "indexedDB.open" in web_js
assert "profiles" in web_js and "taxa" in web_js and "packs" in web_js
service_worker = (ROOT / "apps" / "web" / "sw.js").read_text(encoding="utf-8")
assert "arbotflash-v0-" in service_worker
assert service_worker.count("./media/thumbs/") >= 10
for path in [ROOT / "apps" / "web" / "app.js", ROOT / "apps" / "web" / "offline-db.js", ROOT / "apps" / "web" / "sw.js"]:
    lowered = path.read_text(encoding="utf-8").casefold()
    assert "tree-id-trainer-data-v1" not in lowered
    assert "tree-id-trainer-hosted-v23" not in lowered

print("ArbotFlash v0.5 foundation validation passed against the current compatible pack: 80 taxa, at least 10 local licensed images, transparent shells, IndexedDB installation, pack API and checksums verified.")
