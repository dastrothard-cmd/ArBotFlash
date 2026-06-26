# Offline regional packs

## Tree ID 80 v0.11 pack

The generated pack is stored under:

```text
packs/tree-id-80/
```

Coverage:

- 80 taxon summaries
- 80 linked profile payloads
- 80 source-enriched profiles
- 80 locally stored, individually licensed media files
- 0 transparent seed profile shells
- source and attribution records
- machine-readable manifest
- per-file SHA-256 checksums
- standalone ZIP archive

Build it with:

```bash
python scripts/build_offline_pack.py
```

The archive is:

```text
packs/tree-id-80/arbotflash-tree-id-80-v0.12.0.zip
```

## Browser installation

The PWA installs packs into IndexedDB database `arbotflash-offline-v0-5`. The unchanged database name is intentional: pack versions update independently without discarding user-installed packs or study progress.

Pack data and media are separated:

- IndexedDB stores pack metadata, taxon summaries and full profiles.
- Cache API stores reviewed media.
- user progress remains outside the downloadable pack.

Loading order is:

1. live API;
2. installed offline pack;
3. static 80-taxon fallback seed.

## Integrity and licensing

The manifest records every included file’s byte size and SHA-256 checksum. `attributions.json` retains creator, source page and licence for every included image. A media candidate is not packaged until its identity and file-level licence have been reviewed.
