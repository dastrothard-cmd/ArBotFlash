# Changelog

## 0.12.0 — complete Tree ID 80 authority slice

- Completed the final ten transparent study shells: Acacia websteriana, Corymbia eximia, Eucalyptus norsemanica, Lophostemon confertus, Platanus × acerifolia, Populus alba, Syzygium australe, Tristaniopsis laurina, Ulmus procera and Washingtonia robusta.
- Reached 80/80 source-enriched profiles and 80/80 locally stored, individually licensed reviewed media assets.
- Preserved stable course names separately from authority-accepted names, including Acacia websteriana → Acacia websteri and Eucalyptus norsemanica → Eucalyptus websteriana evidence mappings.
- Regenerated the complete Tree ID 80 offline pack, manifests, attributions and per-file SHA-256 checksums.
- Added v0.12 regression, API, media-route and fresh-release validation.


## 0.11.0 — Authority slice 70

- Expanded sourced profile and reviewed local-media coverage from 60/80 to 70/80.
- Added Black Sheoak, Smooth-barked Apple, Crimson Bottlebrush, Camphor Laurel, Italian Cypress, Red Ironbark, Narrow-leaved Ash, European Ash, Silky Oak and American Sweetgum.
- Added ten revision-pinned Wikipedia/Wikidata supplemental profiles and ten individually licensed local Wikimedia Commons images.
- Added Plants of the World Online/WCVP as a separately registered source dataset with record-level citations and external identifiers.
- Preserved `Callistemon citrinus` and `Cinnamomum camphora` as stable course names while recording POWO accepted-name mappings to `Melaleuca citrina` and `Camphora officinarum`.
- Regenerated the Tree ID 80 offline pack with 70 enriched profiles, 70 local images and 10 transparent shells.
- Updated API, database, package, service-worker and pack metadata to 0.11.0 while preserving the stable PWA ID and IndexedDB schema.
- Added deterministic v0.11 validation for source separation, accepted-name mappings, media integrity and the regenerated pack.

### Data-quality boundary

- POWO checks are stored as explicit source evidence; they do not overwrite the canonical study name.
- Catalogue of Life, GBIF and Australian Plant Census/APNI reconciliation remains queued.
- No external taxonomic match or media candidate can bypass review.

## 0.10.0 — Authority slice 60

- Expanded sourced profile and reviewed local media coverage from 50/80 to 60/80.
- Added ten revision-pinned Wikipedia/Wikidata supplemental profiles while retaining Catalogue of Life and specialist-authority review as pending.
- Added individually licensed local Commons media for Japanese maple, bunya pine, Norfolk Island pine, lemon myrtle, Illawarra flame tree, kurrajong, deodar cedar, ginkgo, jacaranda and southern magnolia.
- Generalised the enrichment importer so a record can retain its own source dataset rather than being forced into Florabase.
- Regenerated the Tree ID 80 offline pack with 60 enriched profiles, 60 local images and 20 transparent shells.
- Updated API, database, package and service-worker version metadata to 0.10.0.

## 0.10.0-authority-slice-50 — 2026-06-17

### Added
- Added ten source-enriched taxa, expanding reviewed evidence and local media coverage from 40/80 to 50/80.
- Added White Cypress Pine, Spotted Gum, Sugar Gum, Flooded Gum, Broad-leaved Paperbark, Lemon-scented Gum, River Sheoak, Weeping Bottlebrush, Monterey Pine and Stone Pine.
- Added ten individually licensed Wikimedia Commons images stored locally with creator, exact file page, licence, capture metadata and SHA-256 checksums.
- Added explicit dual-name handling for the course name *Callistemon viminalis* and Florabase regional name *Melaleuca viminalis* without overwriting study history.
- Added deterministic v0.9 validation for the 50-record evidence slice, names, local media, API responses, pack inventory and offline namespaces.

### Changed
- Rebuilt the development database with 50 specialist-confirmed records and 30 transparent profile shells.
- Regenerated the Tree ID 80 offline pack as v0.10.0 with 60 enriched profiles and 50 local reviewed images.
- Advanced API, package, database and service-worker versions to v0.10.0 while retaining the stable PWA identity and IndexedDB schema.

### Data-quality boundary
- Florabase remains regional specialist evidence and retains its read-only migration warning.
- Catalogue of Life, Australian Plant Census/APNI and GBIF reconciliation remains queued.
- Course names remain stable even when a specialist regional source uses a different accepted genus.
- No external match or media candidate can bypass review.

## 0.8.0-authority-slice-40 — 2026-06-17

### Added
- Added ten source-enriched Western Australian taxa, expanding reviewed evidence coverage from 30/80 to 40/80.
- Added ten individually licensed Wikimedia Commons images stored locally with file-level attribution and checksums.
- Added Florabase identifiers, botanical authorship, classifications, searchable traits and profile sections for the fourth evidence slice.
- Added v0.8 validation for database coverage, media integrity, service-worker assets, API responses and the regenerated pack.

### Changed
- Rebuilt the development database with forty specialist-confirmed records.
- Regenerated the Tree ID 80 offline pack as v0.8.0 with 40 enriched profiles, 40 local images and 40 transparent shells.
- Advanced API, package and service-worker versions to v0.8.0 while preserving the stable PWA ID and IndexedDB schema.

### Data-quality boundary
- Florabase remains regional specialist evidence and retains its read-only migration warning.
- Catalogue of Life, Australian Plant Census/APNI and GBIF reconciliation remains queued.
- No authority match or media asset can silently replace canonical data without review.

## 0.7.0-authority-slice-30 — 2026-06-17

### Added
- Extended the curated Western Australian authority slice from 20 to 30 taxa.
- Added Florabase identifiers, botanical authorship, sourced profile sections and searchable traits for Mountain Marri/Bloodwood, River Red Gum, Yellow Tingle, Red Tingle, Bullich, Tallerack, Flooded Gum, Pincushion Hakea, Harsh Hakea and Rottnest Island Tea Tree.
- Added ten individually licensed or public-domain Wikimedia Commons images with local files, creator attribution, source pages, capture dates and SHA-256 metadata.
- Added explicit notes where the finished course common name differs from the current Florabase common name.
- Added deterministic v0.7 validation for 30 authority records, 30 local media files, 30 review decisions and the regenerated pack.

### Changed
- Regenerated the Tree ID 80 offline pack with 30 enriched profiles, 30 local reviewed images and 50 transparent profile shells.
- Advanced API, database, package, pack and service-worker versions to v0.7.
- Preserved the stable `/arbotflash/` PWA identity and existing IndexedDB pack schema.

### Coverage boundary
- 30/80 taxa are source-enriched and have reviewed local media.
- 50/80 remain clearly labelled seed profile shells.
- Catalogue of Life, Australian Plant Census/APNI and GBIF reconciliation remains queued unless explicitly reviewed.

### Protected
- The hosted Tree ID Trainer remains untouched.
- No candidate source can silently rename a taxon or publish media.
- Grip-product, formulation, hand-application, adhesion and friction-development content remains excluded.

## 0.6.0-authority-slice-20 — 2026-06-17

### Added
- Extended the curated Western Australian authority slice from 10 to 20 taxa.
- Added Florabase identifiers, authorship, classifications, traits and sourced profile sections for three wattles, five banksias and two eucalypts.
- Added ten individually licensed Wikimedia Commons images with creator, source-page, licence, date and local SHA-256 metadata.
- Added current evidence records for Acacia acuminata, Acacia cyclops, Acacia saligna, Banksia grandis, Banksia ilicifolia, Banksia littoralis, Banksia menziesii, Banksia prionotes, Eucalyptus accedens and Eucalyptus patens.
- Added deterministic v0.6 validation covering 20 authority records, 20 local media files, 20 review decisions and the regenerated pack.

### Changed
- Regenerated the Tree ID 80 offline pack with 20 enriched profiles, 20 local licensed images and 60 transparent profile shells.
- Advanced API, database, package, pack and service-worker versions to v0.6.
- Stabilised the PWA application ID at `/arbotflash/` so future releases can update one installed application.
- Preserved the existing IndexedDB pack database because its schema did not change.

### Coverage boundary
- 20/80 taxa are source-enriched and have reviewed local media.
- 60/80 remain explicit seed profile shells.
- Catalogue of Life, GBIF and Australian Plant Census/APNI reconciliation remains queued.

### Protected
- The hosted Tree ID Trainer and its deployment remain unchanged.
- No grip-product, formulation, adhesion, friction or hand-application content was introduced.

## 0.5.0-offline-pack-foundation — 2026-06-17

### Added
- Added the first downloadable, versioned Tree ID 80 offline pack.
- Added manifest, file-size and SHA-256 records for pack data and media.
- Added complete offline taxon summaries and linked profile payloads for all 80 taxa.
- Added ten locally stored Wikimedia Commons thumbnails already reviewed in v0.4.
- Added IndexedDB stores for packs, taxa and profiles, plus Cache API media storage.
- Added install, update and remove controls in the public application.
- Added pack list, manifest, taxa, profile and archive API endpoints.
- Added a safe batch runner for Catalogue of Life and GBIF review candidates.
- Added a Commons media candidate collector with reusable-licence filtering.
- Added pack, local-media and profile-shell counts to the administration dashboard.
- Added deterministic pack, checksum, archive, API and offline-storage validation.

### Changed
- Public media displays use local reviewed thumbnails when available while retaining original Commons URLs and attribution.
- Offline fallback order is now API, installed IndexedDB pack, then lightweight static seed.
- Regional data packs no longer depend on one large localStorage object.
- App, manifest, storage and service-worker identities advanced to v0.5.

### Coverage boundary
- 10/80 taxa are source-enriched; 70/80 remain explicit seed profile shells.
- 10/80 taxa have locally stored reviewed images.
- Catalogue of Life and GBIF candidates remain review-required.
- Australian Plant Census/APNI cross-checking remains pending.

### Protected
- The hosted Tree ID Trainer and its deployment remain unchanged.
- No grip-product, formulation, adhesion, friction or hand-application content was introduced.

## 0.4.0-authority-slice — 2026-06-17

### Added
- Added the first curated authority vertical slice for ten Western Australian taxa.
- Added ten Florabase profile identifiers and source-linked specialist confirmations.
- Added ten individually licensed Wikimedia Commons image records with creator, source page and licence metadata.
- Added botanical authorship, class/order evidence and 230+ enriched trait values across the slice.
- Added 74 specialist-sourced profile sections covering identification, habitat, phenology, distribution, conservation, ecology, fire response, exudates and data-quality notes where applicable.
- Added `review_decision` and `audit_event` tables to development and production schemas.
- Added a separate `/admin/` reconciliation review workspace.
- Added token-protected approve, reject and defer actions; write mode is disabled unless `ARBOTFLASH_ADMIN_TOKEN` is configured.
- Added admin overview and queue API endpoints.
- Added a source-warning display retaining Florabase's current read-only migration caveat.
- Added v0.4 validation for authority records, licensing, admin safeguards and audit history.

### Changed
- Public profiles now display every available sourced section, authorship, verification state, source links and image licence links.
- Ten taxa now report `specialist_import`, `Partially enriched`, licensed media and partially matched taxonomy states.
- Cold-start offline fallback can load the static 80-tree pack even before an API response has been cached.
- App, manifest, storage and service-worker identities advanced to v0.4.

### Still pending
- Catalogue of Life and GBIF review remains pending for all 80 taxa unless explicitly changed in a local review workspace.
- Australian Plant Census is registered but no APC records are claimed imported yet.
- Seventy seed taxa remain profile shells without licensed species media.

### Protected
- The hosted Tree ID Trainer and its deployment remain unchanged.
- Grip-product, formulation, hand-application, adhesion and friction-development content remains excluded.

## 0.3.0-database-foundation — 2026-06-17

### Added
- Added a runnable SQLite development database built from versioned seed files.
- Added a FastAPI development API serving the web application and taxon queries.
- Added normalised source, release, taxon, name, classification, trait, profile, citation, region, media and reconciliation tables.
- Added a read-optimised `taxon_search_projection` for fast filters and search.
- Migrated all 80 seed taxa into the database.
- Added 160 queued Catalogue of Life and GBIF reconciliation jobs.
- Registered the Catalogue of Life 2026-05-15 XR release as configured but not yet imported.
- Added source-release configuration for Catalogue of Life, GBIF, Wikimedia and Open Tree of Life.
- Added safe Catalogue of Life and GBIF reconciliation clients that create review candidates without changing canonical data.
- Expanded the filter catalogue to 154 definitions.
- Added populated filters for taxon rank, profile completeness, media status, common-name availability and reconciliation status.
- Added multi-value OR filtering within a facet and AND filtering across facets.
- Added disjunctive facet counts so alternative values remain selectable.
- Added detailed database profile responses containing names, classifications, citations, media and reconciliation states.
- Added API-backed deck previews and offline seed-pack fallback.
- Added database, API and reconciliation validation tests.

### Changed
- The active ArbotFlash browser application now queries the API instead of loading the 80 taxa directly as its primary data source.
- Service-worker, browser-storage and manifest identities were advanced to v0.3.
- Source claims are now visibly separated from authoritative taxonomy matches.

### Protected
- The hosted Tree ID Trainer and its deployment remain unchanged.
- The original uploaded Tree ID Trainer is still preserved only under the read-only `reference/` directory.
- No grip-product, hand-application, adhesion or friction-development data was introduced.

## 0.2.0-seed-migration — 2026-06-16

### Added
- Audited the complete uploaded Tree ID Trainer website.
- Imported 80/80 unique scientific names, 35 genera and 21 families into a separate seed dataset.
- Reproduced the four original name/taxonomy flashcard directions.
- Added local learning progress, stacked filters, deck selection and linked profile shells.
- Preserved the complete original project as a read-only reference.

## 0.1.0-foundation — 2026-06-16

### Added
- Created the independent ArbotFlash starter codebase.
- Expanded scope from botanical species to all catalogued extant life.
- Added a universal taxon model with extant, extinct and uncertain status support.
- Added source-release provenance and record-level verification states.
- Added initial stacked-filter, deck-builder and linked card/profile previews.
- Added PostgreSQL/PostGIS schema and importer foundations.
