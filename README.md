# ArbotFlash

ArbotFlash is a separate next-generation learning and identification platform for the known tree of life. It begins with the completed 80-tree Tree ID Trainer as its seed pack, while the universal taxon model supports plants, animals, fungi, bacteria, archaea, algae, protists and optional extinct or uncertain taxa.

The hosted Tree ID Trainer remains untouched. ArbotFlash has its own code, database, deployment identity, service-worker cache and browser-storage namespaces.

## What v0.11 delivers

Version 0.11 expands the reviewed evidence pass from sixty to seventy of the original eighty study taxa.

- 80/80 original study taxa retained
- 80 source-enriched profiles
- 70 individually licensed Wikimedia Commons images stored locally with file hashes and attribution
- 10 records explicitly labelled `Seed shell only`
- Plants of the World Online/WCVP name-status cross-checks stored separately for the ten new records
- Stable course names preserved while changed accepted names are recorded as additional taxon names
- Downloadable `tree-id-80` offline pack with manifest, checksums and ZIP archive
- IndexedDB pack installation, update and removal
- Candidate-only Catalogue of Life, GBIF and Wikimedia import pipelines
- Protected evidence-review workspace and immutable audit records

This remains an evidence milestone rather than a claim that all eighty taxa are globally reconciled. Catalogue of Life, GBIF and Australian Plant Census/APNI review remains queued.

## Run locally

```bash
python -m pip install -r requirements.txt
python scripts/build_dev_db.py
python scripts/build_offline_pack.py
python -m apps.api.main
```

Public app: `http://127.0.0.1:8080`

Review workspace: `http://127.0.0.1:8080/admin/`

Administrative writes are disabled unless a token is supplied:

```bash
ARBOTFLASH_ADMIN_TOKEN="choose-a-long-local-token" python -m apps.api.main
```

## Build the offline pack

```bash
python scripts/build_offline_pack.py
```

Generated files are under `packs/tree-id-80/`. The archive is:

```text
packs/tree-id-80/arbotflash-tree-id-80-v0.12.0.zip
```

## Validate

```bash
npm run validate
```

The active regression suite checks the original seed, parser safety, API/filter compatibility, evidence coverage, accepted-name mappings, local media hashes, offline-pack checksums, JavaScript syntax and separation from the hosted Tree ID Trainer. Version-specific snapshot tests for earlier releases remain in `tests/` for checking those archived releases.

## Important files

- `apps/api/main.py` — database, search, filtering, profiles, packs and guarded review APIs
- `apps/web/` — public PWA and IndexedDB pack manager
- `apps/admin/` — evidence and taxonomy review workspace
- `data/enrichment/authority-slice-80.json` — current seventy-taxon evidence slice
- `database/dev/arbotflash-dev.sqlite3` — disposable development database
- `packs/tree-id-80/` — generated v0.11 offline pack
- `scripts/build_dev_db.py` — deterministic database builder
- `scripts/build_offline_pack.py` — versioned pack and checksum builder
- `ROADMAP.md`
- `CHANGELOG.md`

## Authority rule

Wikipedia may provide attributed readable summaries, but it is not the canonical taxonomic authority. Catalogue of Life is the global backbone. Specialist sources such as Plants of the World Online and Australian Plant Census provide reviewed plant-name evidence. GBIF supplies occurrence and supporting-name evidence. Wikidata supplies identifiers and multilingual labels. Wikimedia Commons supplies individually licensed media. Open Tree of Life supplies phylogenetic cross-references.
