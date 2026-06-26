# ArbotFlash architecture

## Product boundary

ArbotFlash is independent of Tree ID Trainer. The completed trainer is a functional reference and migration source only. It has not been renamed, overwritten or connected to the ArbotFlash database.

## Current v0.3 system

```text
Browser PWA
   │
   ├── GET /api/taxa             search, filters and facets
   ├── GET /api/taxa/{id}        linked profile and evidence
   ├── POST /api/decks/preview   server-built study selection
   └── local cache               progress and offline seed pack
            │
            ▼
FastAPI development API
            │
            ▼
SQLite development database
   ├── normalised evidence tables
   └── taxon_search_projection
```

SQLite is a disposable local development database. It is rebuilt from the seed and source configuration files. It is not the intended worldwide production database.

## Production direction

```text
Public PWA / future native clients
            │
            ▼
Versioned ArbotFlash API
            │
    ┌───────┼────────┐
    ▼       ▼        ▼
PostgreSQL  Search    Object storage
+ PostGIS   projection images/audio
    │
    ▼
Import staging and admin review
    │
    ▼
Catalogue of Life + specialist sources + evidence providers
```

## Why two database shapes are used

### Normalised evidence tables

These preserve the truth and its history:

- Stable ArbotFlash taxon concepts
- Scientific and common names
- Classifications from particular source releases
- Trait assertions
- Regions and occurrence assertions
- Profile sections
- Media and licences
- Citations
- Review status

### Search projection

Filtering millions of records should not reconstruct every profile on every click. The search projection stores only the fields needed for rapid names, facets and result cards. It can be rebuilt whenever authoritative data changes.

In local development it is a SQLite table. In production it can become:

- A PostgreSQL materialised view for early releases
- A dedicated search index when catalogue size and traffic require it

The search projection is never the source of truth.

## Filter logic

- Values inside one filter use **OR**.
- Different filters use **AND**.
- A facet ignores its own selected values while calculating available alternatives.

Example:

```text
Family = Myrtaceae OR Fabaceae
AND
Region = Western Australia
AND
Growth form = Tree
```

## Catalogue layers

1. **Internal taxon concept** — stable ArbotFlash ID.
2. **Source records** — external IDs and classifications tied to releases.
3. **Names** — accepted, synonym, historic and vernacular names.
4. **Evidence** — sourced assertions, dates and verification states.
5. **Search projection** — fast disposable representation.
6. **Learning records** — decks and answers linked to internal taxon IDs.

## Scaling rules

- Do not ship the global catalogue inside one browser file.
- Pin external releases.
- Import into staging before publication.
- Never let an importer silently overwrite a reviewed record.
- Keep media files outside the main database.
- Keep raw global occurrences external or partitioned rather than copying everything into each taxon profile.
- Generate small versioned offline packs for selected regions or courses.

## v0.4 review boundary

The public PWA and administration workspace share the same read API but are separate front ends:

```text
apps/web/    public study and identification interface
apps/admin/  protected evidence and taxonomy review interface
```

Administrative writes are disabled unless the server receives an `ARBOTFLASH_ADMIN_TOKEN` environment variable. This shared token is only a local-development control. Production must replace it with authenticated accounts, role checks, server sessions and row-level database policies.

Authority imports write into normalised evidence tables first. `taxon_search_projection` is rebuilt only after the evidence and review rows are committed. The projection is disposable and can always be regenerated.
