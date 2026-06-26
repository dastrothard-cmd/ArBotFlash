# Universal data model

## Taxon concept

A taxon is a stable ArbotFlash record, not merely a scientific-name string. Names and classifications can change while decks, notes and study history continue pointing to the same internal ID.

Important fields include:

- Internal ID
- Canonical scientific name
- Rank
- Life status
- Source release used for canonical placement
- Verification status
- Last-reviewed date

## Names

Each taxon can have many name records:

- Accepted scientific names
- Original study names
- Synonyms
- Historic names
- Misapplied names
- Common names by language and region
- Cultivar and hybrid names

The current seed stores its scientific names as `accepted_study_name`, not as unquestioned authoritative names. This distinction remains until reconciliation is approved.

## Classifications

Classifications are stored separately by rank. This allows ArbotFlash to preserve one source's placement while reviewing another source's alternative hierarchy.

Supported ranks include domain, kingdom, phylum or division, class, order, family, genus, species and lower ranks.

## Traits

Traits consist of:

1. A definition describing the field.
2. One or more sourced assertions connecting that field to a taxon.

Each assertion can carry:

- Value
- Source release
- Citation
- Verification status
- Draft, published, disputed or superseded state
- Review date

This permits plant-only traits such as bark type and animal-only traits such as thermoregulation without adding hundreds of empty columns to every taxon.

## Profiles

Long text is divided into profile sections such as overview, identification, habitat, distribution, uses and chemistry. Every section carries its own source and verification status.

A future profile can therefore contain both reviewed and draft sections without mislabelling the whole page.

## Geography

Regions use parent-child relationships:

```text
World
→ Australia
→ Western Australia
→ South-west Western Australia
→ Swan Coastal Plain
```

The production database adds PostGIS geometry for boundaries and map-radius filters. Taxon-region assertions store presence, establishment, seasonality, confidence and source.

## Media

Media is separate from taxon records. One taxon can have many labelled images, and one comparison image can relate to several taxa.

Required image metadata includes:

- Original URL or storage key
- Creator
- Source page
- Licence and licence URL
- Category
- Location and date where available
- Caption and diagnostic notes
- Verification status

## Reconciliation queue

External matching results enter a queue containing:

- Source searched
- Original study name
- Proposed external ID
- Proposed accepted name
- Proposed rank
- Confidence
- Source classification
- Review status

A match does not change the canonical taxon. Publication requires a later approval step.

## Search projection

`taxon_search_projection` combines the small set of values needed by the public search interface. It is rebuilt from normalised tables and may be discarded safely.

## Learning

Decks and answers reference internal taxon IDs. Individual answers are retained so mastery can be recalculated when the learning algorithm changes.

## Review governance added in v0.4

### `review_decision`

Stores a human or curated-process decision separately from the imported candidate:

- taxon
- source dataset
- decision
- reviewer
- rationale
- previous and new queue status
- decision timestamp

### `audit_event`

Stores the actor, action, entity, before state, after state and timestamp. The development implementation demonstrates the contract; production should make this append-only and permission-protected.

### Why decisions are separate

An imported candidate is evidence. A review decision is governance. Keeping them separate means ArbotFlash can show what the source proposed, what a reviewer decided and when that decision changed without rewriting history.
