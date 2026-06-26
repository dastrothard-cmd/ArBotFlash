#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "dev" / "arbotflash-dev.sqlite3"
sys.path.insert(0, str(ROOT))

from apps.api.main import app  # noqa: E402
from scripts.build_dev_db import build  # noqa: E402

build(DB)

with sqlite3.connect(DB) as connection:
    connection.row_factory = sqlite3.Row
    assert connection.execute("SELECT COUNT(*) FROM taxon").fetchone()[0] == 80
    assert connection.execute("SELECT COUNT(*) FROM taxon_name").fetchone()[0] >= 170
    assert connection.execute("SELECT COUNT(*) FROM taxon WHERE verification_status = 'specialist_import'").fetchone()[0] >= 10
    assert connection.execute("SELECT COUNT(*) FROM media_asset").fetchone()[0] >= 10
    assert connection.execute("SELECT COUNT(*) FROM media_asset WHERE licence_code IS NULL OR creator IS NULL OR source_page_url IS NULL").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM review_decision").fetchone()[0] >= 10
    assert connection.execute("SELECT COUNT(*) FROM audit_event").fetchone()[0] >= 10
    assert connection.execute("SELECT COUNT(DISTINCT taxon_id) FROM profile_section WHERE verification_status = 'specialist_import'").fetchone()[0] >= 10
    assert connection.execute(
        """SELECT COUNT(*) FROM taxon_external_identifier e
           JOIN source_dataset d ON d.id = e.source_dataset_id
           WHERE d.key = 'florabase'"""
    ).fetchone()[0] >= 10
    assert connection.execute(
        """SELECT COUNT(*) FROM reconciliation_queue q
           JOIN source_dataset d ON d.id = q.source_dataset_id
           WHERE d.key = 'florabase' AND q.status = 'specialist_confirmed'"""
    ).fetchone()[0] >= 10
    florabase_release = connection.execute(
        """SELECT r.release_key, r.imported_at FROM source_release r
           JOIN source_dataset d ON d.id = r.source_dataset_id
           WHERE d.key = 'florabase'"""
    ).fetchone()
    assert florabase_release["release_key"] == "retrieved-2026-06-17-read-only-migration-window"
    assert florabase_release["imported_at"]

client = TestClient(app)

health = client.get("/api/health")
assert health.status_code == 200
health_data = health.json()
assert health_data["version"] in {"0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.10.0", "0.11.0", "0.12.0"}
assert health_data["enrichedTaxa"] >= 10
assert health_data["licensedMediaCount"] >= 10
assert health_data["specialistConfirmedReconciliations"] >= 10
assert health_data["reviewDecisionCount"] >= 10

jarrah = client.get("/api/taxa/treeid-eucalyptus-marginata")
assert jarrah.status_code == 200
jarrah_data = jarrah.json()
assert jarrah_data["verification"] == "Specialist import"
assert jarrah_data["profileStatus"] == "Partially enriched"
assert jarrah_data["verifiedImages"] == "Available"
assert any(item["source_key"] == "florabase" and item["status"] == "specialist_confirmed" for item in jarrah_data["reconciliation"])
assert any(item["authorship"] == "Sm." for item in jarrah_data["names"])
assert len(jarrah_data["profileSections"]) >= 7
assert len(jarrah_data["media"]) == 1
assert jarrah_data["media"][0]["licence_code"] == "CC-BY-2.5-AU"
assert jarrah_data["media"][0]["creator"] == "JarrahTree"
assert jarrah_data["media"][0]["source_page_url"].startswith("https://commons.wikimedia.org/")
assert any("Florabase" in item["citation_text"] for item in jarrah_data["citations"])

wa = client.get("/api/taxa", params=[("filter", "country:Australia"), ("limit", "500")])
assert wa.status_code == 200
assert wa.json()["count"] >= 10
assert "bioregion" in wa.json()["facets"]

swan = client.get("/api/taxa", params=[("filter", "bioregion:Swan Coastal Plain"), ("limit", "500")])
assert swan.status_code == 200
assert swan.json()["count"] >= 4

admin_page = client.get("/admin/")
assert admin_page.status_code == 200
assert "ArbotFlash review" in admin_page.text

overview = client.get("/api/admin/overview")
assert overview.status_code == 200
overview_data = overview.json()
assert overview_data["meta"]["enrichedTaxa"] >= 10
assert overview_data["writeModeConfigured"] is False
assert any(term in overview_data["sourceWarning"].lower() for term in ("read-only", "review-required", "review required"))

florabase_queue = client.get("/api/admin/reconciliation", params={"source": "florabase"})
assert florabase_queue.status_code == 200
assert florabase_queue.json()["count"] >= 10
assert all(item["status"] == "specialist_confirmed" for item in florabase_queue.json()["items"])

with sqlite3.connect(DB) as connection:
    baseline_review_count = connection.execute("SELECT COUNT(*) FROM review_decision").fetchone()[0]
    baseline_audit_count = connection.execute("SELECT COUNT(*) FROM audit_event").fetchone()[0]

write_disabled = client.post(
    "/api/admin/reconciliation/treeid-eucalyptus-marginata/catalogue_of_life/decision",
    json={"decision": "defer", "rationale": "Test decision", "reviewer": "Automated validator"},
)
assert write_disabled.status_code == 503

os.environ["ARBOTFLASH_ADMIN_TOKEN"] = "validation-only-token"
write_enabled = client.post(
    "/api/admin/reconciliation/treeid-eucalyptus-marginata/catalogue_of_life/decision",
    headers={"X-ArbotFlash-Admin-Token": "validation-only-token"},
    json={
        "decision": "defer",
        "rationale": "Automated validator confirms review decisions are audited.",
        "reviewer": "Automated validator",
    },
)
assert write_enabled.status_code == 200
assert write_enabled.json()["status"] == "deferred"
with sqlite3.connect(DB) as connection:
    assert connection.execute("SELECT COUNT(*) FROM review_decision").fetchone()[0] == baseline_review_count + 1
    assert connection.execute("SELECT COUNT(*) FROM audit_event").fetchone()[0] == baseline_audit_count + 1
os.environ.pop("ARBOTFLASH_ADMIN_TOKEN", None)

# Restore the versioned, deterministic build after testing the write workflow.
build(DB)

enrichment = json.loads((ROOT / "data" / "enrichment" / "wa-authority-slice-10.json").read_text(encoding="utf-8"))
assert len(enrichment["records"]) >= 10
for record in enrichment["records"]:
    assert record["source"]["url"].startswith("https://florabase.dbca.wa.gov.au/")
    assert record["media"]
    for media in record["media"]:
        assert media["creator"] and media["licenceCode"] and media["sourcePageUrl"]
    forbidden = json.dumps(record).casefold()
    assert "grip formulation" not in forbidden
    assert "adhesion testing" not in forbidden
    assert "hand application" not in forbidden

print(
    "ArbotFlash v0.4 validation passed: 80/80 seed retained, 10 authority profiles, "
    "10 licensed images, source warnings, admin review and audit trail verified."
)
