# Development database

ArbotFlash uses a disposable SQLite database for local development while retaining PostgreSQL/PostGIS as the production architecture.

## Rebuild

```bash
python scripts/build_dev_db.py
```

The command recreates:

```text
database/dev/arbotflash-dev.sqlite3
```

The database is generated from versioned source files and should not be hand-edited. Approved source changes belong in the seed, enrichment, source-registry or migration files and are then rebuilt deterministically.

## v0.11 deterministic contents

- 80 original Tree ID Trainer taxa
- 80 source-enriched taxa
- 80 locally stored reviewed media records
- 0 transparent seed profile shells
- 154 filter definitions
- separate source datasets and releases
- profile sections and trait assertions with citations
- Catalogue of Life and GBIF review queues
- Plants of the World Online record-level cross-checks for the ten v0.11 additions
- protected review decisions and audit events
- read-optimised search projection

## Stable study names

The canonical study name remains the name used by the finished Tree ID Trainer. Alternative accepted names are stored as additional `taxon_name` records. This protects flashcards, saved decks and study history while still exposing current authority evidence.

Examples in v0.11:

- `Callistemon citrinus` remains the study name; `Melaleuca citrina` is recorded as the POWO accepted-name mapping.
- `Cinnamomum camphora` remains the study name; `Camphora officinarum` is recorded as the POWO accepted-name mapping.

## Production transition

The production target remains PostgreSQL 16 with PostGIS and hierarchical taxonomy support. SQLite is only the local deterministic build and test layer; application code reaches it through the API boundary so the public interface does not depend on SQLite-specific behaviour.
