# Data sources and authority rules

## Source hierarchy

ArbotFlash does not expect one dataset to provide every name, trait, image and distribution record correctly.

### 1. Catalogue of Life / ChecklistBank

Role: global taxonomic backbone.

The configured foundation release is:

- Release: `2026-05-15 XR`
- Issued: 15 May 2026
- DOI: `10.48580/dgxsq`
- ChecklistBank dataset key: `315192`

This release is registered as **configured but not imported**. The seed records remain pending reconciliation until candidates are reviewed.

Catalogue of Life itself warns that the catalogue is incomplete and can contain errors. ArbotFlash therefore stores the release and source record rather than presenting any classification as timeless truth.

### 2. Specialist authorities

Role: higher-priority review for particular regions or clades.

Examples include national plant name indexes, marine registers, fungal indexes and microbial nomenclature services. A specialist source can override the generic backbone only through a reviewed mapping. It must never destructively erase the previous name or classification.

### 3. GBIF

Role:

- Name matching and cross-checks
- Occurrence evidence
- Distribution maps
- Dataset discovery
- Media discovery

Raw occurrence points do not automatically become an authoritative native range. Every occurrence and media record must retain its publishing dataset and licence.

### 4. Wikidata

Role:

- Cross-identifiers
- Multilingual labels
- Links to related sources

Wikidata is a useful linked-data layer, not ArbotFlash's final taxonomic authority.

### 5. Wikipedia

Role: optional readable summary source.

Wikipedia text may be used only with page title, language, permanent revision, retrieval date and compatible attribution/share-alike handling. ArbotFlash should prefer concise attributed summaries or links rather than copying entire articles.

### 6. Wikimedia Commons

Role: licensed media candidates.

Every file has its own licence. Store creator, source page, file revision, licence, licence URL, modifications and retrieval date.

### 7. Open Tree of Life

Role: phylogenetic and tree-of-life cross-reference.

ArbotFlash may use Open Tree IDs and synthetic-tree relationships to support future phylogenetic browsing. Imported taxonomy and synthetic-tree releases must be pinned.

## Data states

- `authoritative_import`
- `specialist_import`
- `expert_verified`
- `community_submitted`
- `ai_assisted_draft`
- `unverified`
- `disputed`
- `superseded`
- `verified_seed_import` for preserved Tree ID Trainer values

## AI rule

AI may:

- Draft text from supplied sources
- Propose name mappings
- Flag inconsistencies
- Structure imported data

AI may not:

- Invent missing biological facts
- Promote its own draft to verified
- Invent licences or citations
- Silently overwrite accepted taxonomy
- Convert raw observations into unquestioned range claims

## Western Australian Herbarium / Florabase

Role in v0.4:

- Western Australian taxon profile identifier
- Regional accepted-name evidence
- Descriptive morphology and habitat fields
- Flowering period
- Western Australian conservation/status evidence

The first curated import contains ten profiles retrieved on 17 June 2026. Florabase's service notice says WAHerb and WACensus have been read-only since 1 October 2025 during data migration testing. ArbotFlash therefore stores the warning, marks the records `specialist_import`, and requires later APC and Catalogue of Life cross-checks.

Florabase prose is paraphrased into discrete profile sections rather than copied as anonymous text. Every section retains the profile ID, source URL, retrieval/review date and source state.

## Australian Plant Census / APNI

Role: national accepted-name, synonym and nomenclatural cross-check for Australian vascular plants.

The source is registered in v0.4, but no APC or APNI taxon record is claimed imported yet. Registration is intentionally separate from import status so configuration cannot be mistaken for completed authority work.
