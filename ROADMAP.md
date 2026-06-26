# Product roadmap

## Milestone 1 — Independent foundation

**Status: complete**

- [x] Preserve and audit the finished Tree ID Trainer.
- [x] Import all 80 trees into a separate structured seed.
- [x] Create normalised development and production database schemas.
- [x] Reproduce core flashcard, deck and local-progress behaviour.
- [x] Add API-backed stacked filters and linked profiles.
- [x] Add source, verification and taxonomy-review states.

## Milestone 1.1 — First authority vertical slice

**Status: complete in v0.4**

- [x] Enrich ten locally relevant Western Australian taxa.
- [x] Preserve source identifiers, botanical authorship and source warnings.
- [x] Attach one individually licensed image to each enriched taxon.
- [x] Add richer profile sections and searchable traits.
- [x] Add review decisions, immutable audit events and a protected review workspace.

## Milestone 1.2a — Versioned offline-pack foundation

**Status: complete in v0.5**

- [x] Produce a downloadable 80-tree offline data pack.
- [x] Include a machine-readable manifest and per-file checksums.
- [x] Include complete taxon and profile payloads for all 80 records.
- [x] Store the ten reviewed thumbnails locally with their attribution records.
- [x] Mark the remaining seventy records transparently as profile shells.
- [x] Add IndexedDB install, update, load and removal workflows.
- [x] Add pack discovery and download APIs.
- [x] Add conservative authority and media candidate collectors.
- [x] Add coverage and pack-status reporting to the review workspace.

## Milestone 1.2b — Complete the 80-tree evidence pass

**Status: complete — 80/80 in v0.12**

- Reconcile 80/80 study names against the pinned Catalogue of Life release.
- Cross-check Australian vascular-plant names against Australian Plant Census/APNI.
- Review synonyms, changed genera, authorship, hybrid notation and rank conflicts.
- [x] Expanded sourced profile coverage to 80/80.
- [x] Expanded reviewed licensed media coverage to 80/80.
- Add bark, leaves, flowers, fruit and comparison-image categories where legally available.
- Add explicit evidence-conflict and source-priority display.
- Add automated link, licence and stale-source checks.
- [x] Regenerate the offline pack after every approved evidence batch.

## Milestone 2 — Australian tree and plant catalogue

- Import pinned Australian plant names and identifiers into staging.
- Add states, botanical regions and IBRA bioregions.
- Add occurrence-derived range evidence without treating raw points as unquestioned native range.
- Add map and user-radius filtering.
- Generate downloadable regional packs from saved filter stacks.

## Milestone 3 — Cross-kingdom public beta

- Import a pinned Catalogue of Life release into staging.
- Publish reviewed animals, fungi, bacteria, archaea, algae and protists.
- Expose organism-specific filters only when relevant.
- Add global search, multilingual names and phylogenetic cross-references.

## Milestone 4 — Accounts and field collections

- Synced study history, mastery, notes and favourites.
- Personal specimen uploads and identification history.
- Private/shared decks and field collections.
- Organisation and school accounts.

## Milestone 5 — Global catalogue operations

- Repeatable release imports and taxonomy-difference review.
- Specialist-source priority rules by clade and region.
- Community contributions and expert moderation.
- Global occurrence maps and pack generation.
- Translation and accessible education workflows.
