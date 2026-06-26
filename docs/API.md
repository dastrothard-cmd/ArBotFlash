# Development API

The v0.3 API is implemented in `apps/api/main.py` using FastAPI.

## Start

```bash
python -m apps.api.main
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8080/docs
```

## Endpoints

### `GET /api/health`

Returns database version, counts and reconciliation status.

### `GET /api/bootstrap`

Returns the 80-taxon offline seed pack, filter definitions, initial facet counts and database metadata.

### `GET /api/taxa`

Searches and filters taxa.

Parameters:

- `search` — free-text name/family/genus search
- `filter` — repeatable `key:value` token
- `offset`
- `limit`

Example:

```text
/api/taxa?filter=family:Myrtaceae&filter=family:Fabaceae&filter=plantForm:Tree
```

Values within `family` use OR. `plantForm` then stacks with AND.

### `GET /api/taxa/{taxon_id}`

Returns the detailed linked taxon profile:

- Names
- Classification path
- Profile sections
- Citations
- Reconciliation records
- Media records

### `POST /api/decks/preview`

Builds a deck from the current database query.

Example request:

```json
{
  "search": "",
  "filters": {
    "family": ["Myrtaceae"],
    "plantForm": ["Tree"]
  },
  "size": 20,
  "selectionMode": "alphabetical",
  "progress": {}
}
```

### `GET /api/sources`

Lists configured data sources, roles, licences and release counts.

### `GET /api/reconciliation/summary`

Returns taxonomy-review queue counts by status and source.

## Production changes later

Before public global deployment, the API will add:

- Authentication and permissions
- Pagination cursors
- Rate limiting
- Cached facet queries
- Region geometry endpoints
- Offline-pack manifests
- Admin review endpoints
- Versioned public API paths

## v0.4 administration endpoints

### `GET /api/admin/overview`

Returns source-enrichment totals, queue status, write-mode configuration and the current authority-source warning.

### `GET /api/admin/reconciliation`

Returns the joined queue, taxon and source records. Optional query parameters:

- `status`
- `source`
- `limit`

### `POST /api/admin/reconciliation/{taxon_id}/{source_key}/decision`

Development-only guarded write endpoint. The server must have `ARBOTFLASH_ADMIN_TOKEN` configured and the request must send the matching `X-ArbotFlash-Admin-Token` header.

Accepted body decisions are `approve`, `reject` and `defer`. Every accepted decision creates both a review row and an audit event.

## Offline-pack endpoints added in v0.5

- `GET /api/packs` — list available versioned packs and coverage counts
- `GET /api/packs/{pack_key}/manifest` — retrieve the pack manifest
- `GET /api/packs/{pack_key}/taxa` — retrieve searchable taxon summaries
- `GET /api/packs/{pack_key}/profiles` — retrieve full linked profile payloads
- `GET /api/packs/{pack_key}/download` — download the pack ZIP archive

Pack keys are validated before filesystem access. Pack APIs expose only directories containing a valid manifest.
