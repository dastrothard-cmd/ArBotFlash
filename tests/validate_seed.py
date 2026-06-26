#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
seed_path = ROOT / 'apps/web/data/treeid-seed-80.json'
records = json.loads(seed_path.read_text(encoding='utf-8'))

assert len(records) == 80, f'Expected 80 records, found {len(records)}'
assert len({row['scientificName'].casefold() for row in records}) == 80, 'Scientific names are not unique'
assert all(row['commonName'] and row['scientificName'] and row['family'] for row in records), 'Required seed fields are missing'
assert all(row['id'].startswith('treeid-') for row in records), 'Unexpected seed IDs'
assert all(row['verification'] == 'Verified seed import' for row in records), 'Verification state mismatch'

common_counts = Counter(row['commonName'].casefold() for row in records)
assert common_counts['flooded gum'] == 2, 'Known repeated common name was not preserved'

active_files = [
    ROOT / 'apps/web/app.js',
    ROOT / 'apps/web/sw.js',
    ROOT / 'apps/web/manifest.webmanifest',
]
for path in active_files:
    lowered = path.read_text(encoding='utf-8').lower()
    assert 'tree-id-trainer-data-v1' not in lowered, f'Legacy storage collision in {path}'
    assert 'tree-id-trainer-hosted-v23' not in lowered, f'Legacy cache collision in {path}'


definitions = json.loads((ROOT / 'apps/web/data/filter-definitions.json').read_text(encoding='utf-8'))
keys = [row['key'] for row in definitions]
assert len(keys) == len(set(keys)), 'Filter-definition keys are not unique'
assert len(definitions) >= 130, f'Expected broad filter schema, found {len(definitions)} definitions'

metadata = json.loads((ROOT / 'data/seed/treeid-seed-metadata.json').read_text(encoding='utf-8'))
assert metadata['record_count'] == 80
assert metadata['source_sha256'] == 'b94715dd289d17ecf6415121565148cbd671f608a04b531606adf72be55f0b55'

print(f'Seed validation passed: 80/80 unique scientific names; {len(definitions)} filter definitions; namespaces separated.')
