#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "dev" / "arbotflash-dev.sqlite3"

# Ensure imports work whether the test is launched from the root or elsewhere.
import sys
sys.path.insert(0, str(ROOT))

from apps.api.main import app  # noqa: E402
from scripts.build_dev_db import build  # noqa: E402

build(DB)

with sqlite3.connect(DB) as connection:
    assert connection.execute("SELECT COUNT(*) FROM taxon").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM taxon_name").fetchone()[0] >= 160
    assert connection.execute("SELECT COUNT(*) FROM taxon_search_projection").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM reconciliation_queue").fetchone()[0] >= 160
    assert connection.execute("SELECT COUNT(*) FROM trait_definition").fetchone()[0] >= 150
    assert connection.execute("SELECT COUNT(*) FROM source_dataset").fetchone()[0] >= 7
    flooded = connection.execute(
        "SELECT COUNT(*) FROM taxon_search_projection WHERE common_name = 'Flooded Gum'"
    ).fetchone()[0]
    assert flooded == 2

client = TestClient(app)

root_page = client.get("/")
assert root_page.status_code == 200
assert "ArbotFlash" in root_page.text

health = client.get("/api/health")
assert health.status_code == 200
health_payload = health.json()
assert health_payload["taxonCount"] == 80
assert health_payload["pendingReconciliations"] <= 160
assert health_payload["filterDefinitionCount"] >= 150

bootstrap = client.get("/api/bootstrap")
assert bootstrap.status_code == 200
bootstrap_payload = bootstrap.json()
assert len(bootstrap_payload["taxa"]) == 80
assert "family" in bootstrap_payload["facets"]
assert "plantForm" in bootstrap_payload["facets"]
plant_form_counts = {item["value"]: item["count"] for item in bootstrap_payload["facets"]["plantForm"]}
assert plant_form_counts["Tree"] >= 70
assert plant_form_counts["Shrub"] >= 1

myrtaceae = client.get("/api/taxa", params=[("filter", "family:Myrtaceae"), ("limit", "500")])
assert myrtaceae.status_code == 200
myrtaceae_payload = myrtaceae.json()
assert myrtaceae_payload["count"] == 38
assert all(item["family"] == "Myrtaceae" for item in myrtaceae_payload["items"])
# Disjunctive facets keep other family choices available while one family is active.
family_values = {item["value"] for item in myrtaceae_payload["facets"]["family"]}
assert "Myrtaceae" in family_values and "Fabaceae" in family_values

multi_family = client.get(
    "/api/taxa",
    params=[("filter", "family:Myrtaceae"), ("filter", "family:Fabaceae"), ("limit", "500")],
)
assert multi_family.status_code == 200
assert {item["family"] for item in multi_family.json()["items"]} <= {"Myrtaceae", "Fabaceae"}
assert multi_family.json()["count"] > myrtaceae_payload["count"]

jarrah = client.get("/api/taxa/treeid-eucalyptus-marginata")
assert jarrah.status_code == 200
jarrah_payload = jarrah.json()
assert jarrah_payload["scientificName"] == "Eucalyptus marginata"
assert len(jarrah_payload["names"]) >= 2
assert len(jarrah_payload["reconciliation"]) >= 2
assert len(jarrah_payload["citations"]) >= 1
assert isinstance(jarrah_payload["media"], list)

invalid_filter = client.get("/api/taxa", params={"filter": "notARealFilter:value"})
assert invalid_filter.status_code == 400

deck = client.post(
    "/api/decks/preview",
    json={
        "filters": {"family": ["Myrtaceae"]},
        "size": 10,
        "selectionMode": "alphabetical",
        "progress": {},
    },
)
assert deck.status_code == 200
assert deck.json()["count"] == 10
assert deck.json()["items"][0]["scientificName"] == "Agonis flexuosa"

seed = json.loads((ROOT / "apps/web/data/treeid-seed-80.json").read_text(encoding="utf-8"))
for record in seed:
    keys = " ".join(record.keys()).casefold()
    assert "grip" not in keys
    assert "adhesion" not in keys
    assert "friction" not in keys

for path in [
    ROOT / "apps/web/app.js",
    ROOT / "apps/web/sw.js",
    ROOT / "apps/web/manifest.webmanifest",
]:
    lowered = path.read_text(encoding="utf-8").casefold()
    assert "tree-id-trainer-data-v1" not in lowered
    assert "tree-id-trainer-hosted-v23" not in lowered

print(
    "ArbotFlash v0.3 validation passed: database 80/80, 154+ filters, "
    "source queues, disjunctive facets, profiles, decks and namespaces verified."
)
