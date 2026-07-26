# ARBOT Quote integration

## Current limitation

ARBOT Quote currently bundles a compact ArbotFlash snapshot into the application. That is acceptable for the initial staging catalogue but does not scale to thousands or hundreds of thousands of names.

## Required production path

```text
ARBOT Quote tree-name field
        │
        ├── debounced search after 2 characters
        ▼
GET /v1/taxa/search?q=...&region=AU&authority=apc&arboreal=true
        │
        ├── accepted names
        ├── synonyms and historic combinations
        ├── regional common names
        └── stable Arbot concept ID
```

Selecting a result stores:

- stable Arbot concept ID
- issued scientific name
- issued common name
- authority profile
- registry release ID

The quote must retain the exact issued names even if the registry changes later. Opening the profile can show the newer reviewed treatment and name-change history, but an old issued proposal must remain reproducible.

## Offline behaviour

ARBOT Quote may cache:

- recently selected taxa
- a regional high-frequency pack
- the exact taxon records referenced by saved quotes

It must not download the full global registry into every browser.

## Manual expert entry

High-knowledge arborists must always be able to type an unlisted scientific name. Manual entries are stored as unresolved observations and can be submitted to the registry review queue. They are never silently mapped to a concept by fuzzy matching.

## Search ranking

Recommended order:

1. exact accepted scientific name
2. exact regional common name
3. exact synonym or former combination
4. scientific prefix match
5. common-name prefix match
6. contains match
7. fuzzy match, clearly labelled and never auto-selected

Regional and authority profiles affect display preference, not underlying source preservation.

## Migration steps

1. deploy the registry API separately from ARBOT Quote
2. add server-side proxy and cache in ARBOT Quote
3. replace bundled datalists with an accessible async combobox
4. persist registry release and authority profile with each selected tree
5. backfill existing local IDs into stable concepts
6. retain the bundled snapshot only as a temporary offline fallback
