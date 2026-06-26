#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.importers.reconcile_taxonomy import parse_col_response, parse_gbif_response

fixture = json.loads((ROOT / "tests/fixtures/reconciliation/Eucalyptus_marginata.json").read_text())
col = parse_col_response("Eucalyptus marginata", fixture)
assert col is not None
assert col.external_id == "synthetic-col-id"
assert col.scientific_name == "Eucalyptus marginata"
assert col.rank == "species"
assert col.confidence == 1.0

fixture_gbif = {
    "usageKey": 123,
    "scientificName": "Eucalyptus marginata Donn ex Sm.",
    "canonicalName": "Eucalyptus marginata",
    "rank": "SPECIES",
    "status": "ACCEPTED",
    "confidence": 99,
    "matchType": "EXACT",
    "kingdom": "Plantae",
    "phylum": "Tracheophyta",
    "family": "Myrtaceae",
    "genus": "Eucalyptus",
    "species": "Eucalyptus marginata"
}
gbif = parse_gbif_response("Eucalyptus marginata", fixture_gbif)
assert gbif is not None
assert gbif.external_id == "123"
assert gbif.confidence == 0.99
assert gbif.raw_summary["matchType"] == "EXACT"

print("Taxonomy reconciliation parsers passed synthetic fixtures; no canonical data was changed.")
