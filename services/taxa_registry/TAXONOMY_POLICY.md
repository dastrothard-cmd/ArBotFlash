# Taxonomy and name-change policy

## Stable concepts, changing names

An Arbot taxon concept is a stable internal record. Scientific names are sourced assertions attached to that concept; they are not the primary key.

This prevents a newly published combination, synonymisation or genus split from breaking quotes, specimen records, study history or media attribution.

## Authority profiles

The registry can expose different reviewed treatments for different contexts:

- `global` — selected global backbone
- `wcvp` — World Checklist of Vascular Plants treatment
- `col` — Catalogue of Life treatment
- `apc` — Australian Plant Census treatment
- future country, state, municipal or course profiles

A profile selects the name shown as preferred. It does not delete alternative names or classifications.

## Example: Blakella and Corymbia

The 2024 elevation of *Blakella* creates combinations such as *Blakella eximia*. Other active authorities may continue to treat those names as synonyms under *Corymbia*, such as *Corymbia eximia*.

The registry must therefore store:

1. the stable tree concept
2. both source name records and their authorship
3. each authority's accepted/synonym relationship
4. the release in which each treatment occurred
5. the preferred display name for the selected authority/region profile
6. an event requiring review before a product changes its preferred display name

## Review classes

### Automatic staging allowed

- new source release metadata
- raw source record ingestion
- exact source-ID updates within the same pinned release
- proposed name matches with confidence and evidence
- rebuilt disposable search projections from already reviewed records

### Human review required

- accepted-name changes
- genus transfers or splits
- synonymy changes
- merges or splits of stable Arbot concepts
- arboreal-status changes
- regional preferred-name changes
- licence or attribution changes
- media replacement

## Arboricultural scope

Global plant backbones contain herbs, grasses, vines and many non-arboreal taxa. Inclusion in ARBOT Quote requires a reviewed `tree` or `tree-like` assertion. The registry may store every plant name while exporting only relevant taxa to arboricultural products.

Cultivars, hybrids and trade names can be attached to a concept, but must remain distinguishable from taxonomic ranks and scientific names.

## Publication

Every published registry snapshot must include:

- source release IDs and checksums
- retrieval dates
- citations and licences
- record and change counts
- unresolved conflict count
- reviewer identity and date
- snapshot checksum

No automated watcher or importer is authorised to publish directly.
