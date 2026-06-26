# Taxonomy reconciliation

## Why reconciliation is required

The Tree ID Trainer contains the study names used by the completed course app. Those names are valuable and must be preserved, but they should not automatically be treated as the latest accepted global taxonomy.

Taxonomy changes can include:

- Accepted names becoming synonyms
- Species moving to another genus
- Rank changes
- Different authorities disagreeing
- Different common names sharing one scientific name
- One common name referring to several taxa

## Safe workflow

1. Preserve the original study name.
2. Query a pinned external release.
3. Store the proposed match in `reconciliation_queue`.
4. Compare name, rank, authorship and lineage.
5. Review conflicts.
6. Approve or reject the mapping.
7. Publish the external ID and accepted name without deleting history.

## Command

```bash
python packages/importers/reconcile_taxonomy.py \
  --source catalogue_of_life \
  --name "Eucalyptus marginata" \
  --limit 1
```

This prints the candidate but makes no database change.

To save it for review:

```bash
python packages/importers/reconcile_taxonomy.py \
  --source catalogue_of_life \
  --name "Eucalyptus marginata" \
  --limit 1 \
  --apply
```

`--apply` means “apply to the review queue,” not “accept the taxonomy.”

## Supported candidate sources

- `catalogue_of_life` — pinned ChecklistBank release
- `gbif` — GBIF species matcher and cross-check

Australian plant names will later receive additional specialist review rather than relying only on a generic global backbone.

## Network and fixture behaviour

The execution environment used to build v0.3 could not make direct outbound API calls from the code container. Parser behaviour is tested with synthetic fixtures. The live clients and release endpoints are included, but real results must be retrieved in a connected development or deployment environment.

Fixtures are clearly synthetic and are never inserted into the shipped database.

## v0.4 specialist-source state

The first Florabase records use `specialist_confirmed`. This means a regional specialist profile was manually curated and linked. It does not close the Catalogue of Life, APC/APNI or GBIF queues.

The review workspace records `approved`, `rejected` or `deferred` decisions. Approval may add an external identifier, but it does not delete the seed study name or automatically replace the canonical concept.
