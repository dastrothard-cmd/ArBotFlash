from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from argparse import Namespace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


INGEST = load_module("taxa_registry_ingest", ROOT / "ingest_dwca.py")
WATCH = load_module("taxa_registry_watch", ROOT / "taxonomy_watch.py")
EXPORT = load_module("taxa_registry_export", ROOT / "export_quote_catalog.py")


META_XML = """<?xml version="1.0" encoding="UTF-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/">
  <core encoding="UTF-8" fieldsTerminatedBy="," linesTerminatedBy="\n" fieldsEnclosedBy="&quot;" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Taxon">
    <files><location>taxon.csv</location></files>
    <id index="0" />
    <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName" />
    <field index="2" term="http://rs.tdwg.org/dwc/terms/taxonRank" />
    <field index="3" term="http://rs.tdwg.org/dwc/terms/taxonomicStatus" />
    <field index="4" term="http://rs.tdwg.org/dwc/terms/acceptedNameUsageID" />
    <field index="5" term="http://rs.tdwg.org/dwc/terms/family" />
    <field index="6" term="http://rs.tdwg.org/dwc/terms/genus" />
  </core>
</archive>
"""


class RegistryTests(unittest.TestCase):
    def test_dwca_import_stages_source_records_without_publishing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "fixture.zip"
            database = root / "registry.sqlite"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("meta.xml", META_XML)
                handle.writestr(
                    "taxon.csv",
                    "id,scientificName,rank,status,accepted,family,genus\n"
                    "corymbia,Corymbia eximia,species,accepted,,Myrtaceae,Corymbia\n"
                    "blakella,Blakella eximia,species,synonym,corymbia,Myrtaceae,Blakella\n",
                )
            args = Namespace(
                db=str(database),
                archive=str(archive),
                source="fixture",
                release="2026-01",
                schema=str(ROOT / "schema.sql"),
                dataset_id="fixture-1",
                source_url="https://example.test/fixture.zip",
                published_at="2026-01-01",
                licence="CC0",
                citation="Fixture",
                batch_size=10,
                replace=False,
            )
            self.assertEqual(INGEST.stage_archive(args), 0)
            connection = sqlite3.connect(database)
            try:
                release = connection.execute("SELECT record_count, status FROM registry_releases").fetchone()
                records = connection.execute(
                    "SELECT scientific_name, taxonomic_status, accepted_source_taxon_id FROM source_taxa ORDER BY scientific_name"
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual(release, (2, "staged"))
            self.assertEqual(records[0], ("Blakella eximia", "synonym", "corymbia"))
            self.assertEqual(records[1], ("Corymbia eximia", "accepted", ""))

    def test_quote_export_contains_only_reviewed_arboreal_projection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / "registry.sqlite"
            output = root / "quote.json"
            connection = sqlite3.connect(database)
            try:
                connection.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO taxon_concepts (id, canonical_name, rank, arboreal_status, created_at, updated_at) VALUES ('tree-1','Corymbia eximia','species','tree','now','now')"
                )
                connection.execute(
                    "INSERT INTO taxon_search_projection (concept_id, accepted_name, common_name, aliases, family, genus, rank, arboreal_status, region_codes, authority_profile, updated_at) VALUES ('tree-1','Corymbia eximia','Yellow Bloodwood','Blakella eximia','Myrtaceae','Corymbia','species','tree','AU','apc','now')"
                )
                connection.execute(
                    "INSERT INTO taxon_concepts (id, canonical_name, rank, arboreal_status, created_at, updated_at) VALUES ('herb-1','Example herb','species','not-tree','now','now')"
                )
                connection.execute(
                    "INSERT INTO taxon_search_projection (concept_id, accepted_name, rank, arboreal_status, region_codes, authority_profile, updated_at) VALUES ('herb-1','Example herb','species','not-tree','AU','apc','now')"
                )
                connection.commit()
            finally:
                connection.close()
            args = Namespace(db=str(database), output=str(output), region="AU", authority_profile="apc", limit=100)
            self.assertEqual(EXPORT.export_catalog(args), 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["taxa"][0]["binomial"], "Corymbia eximia")
            self.assertIn("Blakella eximia", payload["taxa"][0]["aliases"])

    def test_watch_report_never_authorises_automatic_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = root / "sources.json"
            state = root / "state.json"
            report = root / "report.json"
            local_release = root / "release.txt"
            local_release.write_text("release one", encoding="utf-8")
            sources.write_text(json.dumps({
                "sources": [{
                    "id": "fixture",
                    "name": "Fixture",
                    "watchMode": "landing-page",
                    "releasePage": local_release.as_uri(),
                }]
            }), encoding="utf-8")
            args = Namespace(
                sources=str(sources),
                state=str(state),
                report=str(report),
                timeout=5,
                report_first_seen=True,
                fail_on_error=True,
            )
            self.assertEqual(WATCH.check_sources(args), 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(payload["publicationBlocked"])
            self.assertEqual(payload["changeCount"], 1)

    def test_watch_skips_manual_sources_even_with_reference_urls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = root / "sources.json"
            state = root / "state.json"
            report = root / "report.json"
            sources.write_text(json.dumps({
                "sources": [{
                    "id": "manual-reference",
                    "name": "Manual Reference",
                    "watchMode": "manual",
                    "releasePage": "https://example.test/not-ci-watchable",
                }]
            }), encoding="utf-8")
            args = Namespace(
                sources=str(sources),
                state=str(state),
                report=str(report),
                timeout=5,
                report_first_seen=True,
                fail_on_error=True,
            )
            with mock.patch.object(WATCH, "request_headers", side_effect=AssertionError("manual sources must not be probed")):
                self.assertEqual(WATCH.check_sources(args), 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            state_payload = json.loads(state.read_text(encoding="utf-8"))
            self.assertFalse(payload["changed"])
            self.assertEqual(payload["errorCount"], 0)
            self.assertTrue(payload["publicationBlocked"])
            self.assertEqual(state_payload["sources"]["manual-reference"]["status"], "manual")


if __name__ == "__main__":
    unittest.main()
