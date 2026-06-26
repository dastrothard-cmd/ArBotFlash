#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.importers.collect_commons_candidates import parse_candidates

payload = json.loads((ROOT / "tests" / "fixtures" / "commons" / "sample.json").read_text(encoding="utf-8"))
items = parse_candidates("Eucalyptus marginata", payload)
assert len(items) == 1
assert items[0]["creator"] == "Example photographer"
assert items[0]["licenceCode"] == "CC BY-SA 4.0"
assert items[0]["reviewStatus"] == "candidate_only"
assert "Human review required" in items[0]["reviewRule"]
print("Commons media candidate parser passed: reusable licences retained, non-free candidate rejected.")
