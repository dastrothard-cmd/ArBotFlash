# Arbot Taxa Registry

Arbot Taxa Registry is the long-lived taxonomy service shared by ArbotFlash, ARBOT Quote and future ARBOT products.

It exists because a global professional tree catalogue cannot be maintained safely as one hand-edited browser JSON file. The registry keeps stable internal taxon concepts while tracking accepted names, synonyms, alternative classifications, regional usage and source-release history.

## Product responsibilities

- ingest versioned global and regional taxonomy releases
- preserve every source identifier and release rather than overwriting history
- map source records onto stable Arbot taxon concepts
- retain competing classifications when recognised authorities disagree
- record accepted, synonym, historic and vernacular names with provenance
- flag likely tree and tree-like taxa for arboricultural search
- generate compact regional and product-specific search projections
- detect upstream release changes and create a human-review report
- publish reviewed snapshots for ARBOT Quote without shipping the global catalogue to every browser

## Initial authority stack

1. Catalogue of Life / ChecklistBank — broad global backbone and release history
2. World Checklist of Vascular Plants / Plants of the World Online — actively curated vascular-plant taxonomy
3. International Plant Names Index — nomenclatural publications and author citations
4. Australian Plant Name Index and Australian Plant Census — Australian names and accepted regional concepts
5. specialist and regional sources — added as reviewed overlays, never silent replacements

The source configuration lives in `config/sources.json`.

## Important taxonomy rule

The registry separates **name**, **source taxon record** and **Arbot taxon concept**.

For example, a newly published combination in *Blakella* can be stored as a valid source name even when another authority treats it as a synonym under *Corymbia*. ARBOT can then show the current name used by the selected regional or authority profile without deleting either classification.

## Directory

```text
services/taxa_registry/
├── README.md
├── config/sources.json
├── schema.sql
├── ingest_dwca.py
├── taxonomy_watch.py
├── export_quote_catalog.py
├── state/source-state.json
└── tests/
```

## Local use

Create a registry database:

```bash
sqlite3 data/taxa-registry.sqlite < services/taxa_registry/schema.sql
```

Ingest a Darwin Core Archive already downloaded from an authority:

```bash
python services/taxa_registry/ingest_dwca.py \
  --db data/taxa-registry.sqlite \
  --archive /path/to/wcvp_dwca.zip \
  --source wcvp \
  --release 2026-06-04
```

Export a compact ARBOT Quote search snapshot:

```bash
python services/taxa_registry/export_quote_catalog.py \
  --db data/taxa-registry.sqlite \
  --output dist/arbot-quote-taxa.json \
  --region AU \
  --limit 50000
```

Run the release watcher:

```bash
python services/taxa_registry/taxonomy_watch.py \
  --sources services/taxa_registry/config/sources.json \
  --state services/taxa_registry/state/source-state.json \
  --report taxonomy-watch-report.json
```

## Publication boundary

Automated jobs may download, parse, compare and propose changes. They must not silently publish a changed accepted name or merge concepts. A reviewed release produces:

- a stable registry release ID
- a source and licence manifest
- a change report
- a rebuilt search projection
- compact regional/product snapshots

## Scale target

The schema and importer are intended for millions of source name records and hundreds of thousands of accepted plant concepts. ARBOT Quote should query a server-side projection and receive only the small result set needed for the current search.
