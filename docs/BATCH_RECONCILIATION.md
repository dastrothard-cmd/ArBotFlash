# Batch reconciliation and media candidates

## Taxonomy candidates

`scripts/run_authority_batch.py` processes pending Catalogue of Life and GBIF queue records. It can use live APIs or deterministic fixtures.

Without `--apply`, it creates a report only. With `--apply`, it can set queue records to `review_required`, `no_match` or `error`. It does not mutate canonical taxon concepts, accepted study names or classifications.

A human decision remains required through the review workspace. Every decision is recorded separately and audited.

Australian Plant Census/APNI is registered as a required national authority. Its accepted-name and concept cross-check remains a later reviewed import, not an assumed result.

## Media candidates

`packages/importers/collect_commons_candidates.py` queries Wikimedia Commons file metadata. It rejects results whose file metadata does not describe a reusable Public Domain, CC0, CC BY or CC BY-SA licence.

Passing the licence filter is not publication approval. A reviewer must still confirm:

- the organism identification
- that the image is genuinely useful for the selected category
- creator and source-page attribution
- the exact file-level licence and link
- whether location or cultural sensitivity requires restriction

Only approved candidates become `media_asset` records and locally stored files.
