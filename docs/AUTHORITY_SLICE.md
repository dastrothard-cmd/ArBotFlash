# Authority and evidence slice

## Current coverage

The active deterministic evidence file is:

```text
data/enrichment/authority-slice-80.json
```

It contains seventy reviewed seed-taxon records. Each enriched record preserves:

- the stable Tree ID Trainer study name;
- botanical authorship where available;
- source-specific external identifiers;
- independently cited profile sections;
- searchable trait assertions;
- reviewed, individually licensed media metadata;
- the exact accepted-name alternative when a specialist authority differs from the course name;
- review and audit records.

The original ten-, twenty-, thirty-, forty-, fifty- and sixty-record files remain in the repository as historical evidence snapshots. They are not imported by the active v0.11 database builder.

## v0.11 source layers

The ten records added in v0.11 use three separate evidence layers:

1. revision-pinned Wikipedia/Wikidata material for readable supplemental summaries and identifiers;
2. Plants of the World Online/WCVP for accepted-name, synonym and authorship cross-checks;
3. individually licensed Wikimedia Commons files for locally stored study media.

These layers remain distinct in the database. A readable summary cannot silently become the taxonomic authority, and a POWO accepted-name mapping cannot overwrite the stable study card.

## Current boundary

- 80/80 taxa are source-enriched.
- 80/80 have reviewed local media.
- 10/80 remain explicit seed shells.
- Catalogue of Life, GBIF and Australian Plant Census/APNI review remains queued.
