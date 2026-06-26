#!/usr/bin/env python3
"""Build the disposable SQLite development database from versioned seed files.

The production design remains PostgreSQL/PostGIS. SQLite makes this milestone
runnable locally without cloud credentials while preserving the same model
boundaries: sources, releases, taxa, names, classifications, traits, profiles,
and a read-optimised search projection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "database" / "dev" / "arbotflash-dev.sqlite3"
SCHEMA = ROOT / "database" / "dev" / "001_sqlite_schema.sql"
SEED = ROOT / "apps" / "web" / "data" / "treeid-seed-80.json"
FILTERS = ROOT / "apps" / "web" / "data" / "filter-definitions.json"
SOURCES = ROOT / "data" / "source_registry.json"
SEED_METADATA = ROOT / "data" / "seed" / "treeid-seed-metadata.json"
SOURCE_RELEASES_PATH = ROOT / "data" / "source_releases.json"
ENRICHMENT_PATH = ROOT / "data" / "enrichment" / "authority-slice-80.json"

NAMESPACE = uuid.UUID("6a69f51a-59db-4f20-98e7-57d3fd12545b")
NOW = datetime.now(timezone.utc).isoformat()

SOURCE_DETAILS: dict[str, dict[str, str | None]] = {
    "tree_id_trainer_v15_23": {
        "title": "Tree ID Trainer v15.23 verified 80-tree seed",
        "publisher": "User-supplied ArbotFlash reference dataset",
        "homepage_url": "https://www.treeidflashcards.com",
        "licence_code": "private_seed_reference",
        "licence_url": None,
    },
    "catalogue_of_life": {
        "title": "Catalogue of Life / ChecklistBank",
        "publisher": "Catalogue of Life",
        "homepage_url": "https://www.catalogueoflife.org/",
        "licence_code": "CC-BY-4.0-metadata-see-source-datasets",
        "licence_url": "https://creativecommons.org/licenses/by/4.0/",
    },
    "florabase": {
        "title": "Florabase — the Western Australian flora",
        "publisher": "Western Australian Herbarium, Department of Biodiversity, Conservation and Attractions",
        "homepage_url": "https://florabase.dbca.wa.gov.au/",
        "licence_code": "source_terms_apply",
        "licence_url": "https://florabase.dbca.wa.gov.au/",
    },
    "plants_of_the_world_online": {
        "title": "Plants of the World Online / World Checklist of Vascular Plants",
        "publisher": "Royal Botanic Gardens, Kew",
        "homepage_url": "https://powo.science.kew.org/",
        "licence_code": "source_terms_apply",
        "licence_url": "https://www.kew.org/about-us/terms-and-conditions",
    },
    "australian_plant_census": {
        "title": "Australian Plant Census",
        "publisher": "Council of Heads of Australasian Herbaria",
        "homepage_url": "https://biodiversity.org.au/nsl/services/apc",
        "licence_code": "source_terms_apply",
        "licence_url": "https://biodiversity.org.au/nsl/services/apc",
    },
    "gbif": {
        "title": "Global Biodiversity Information Facility",
        "publisher": "GBIF Secretariat",
        "homepage_url": "https://www.gbif.org/",
        "licence_code": "record_specific",
        "licence_url": None,
    },
    "wikidata": {
        "title": "Wikidata",
        "publisher": "Wikimedia Foundation and contributors",
        "homepage_url": "https://www.wikidata.org/",
        "licence_code": "CC0-1.0",
        "licence_url": "https://creativecommons.org/publicdomain/zero/1.0/",
    },
    "wikipedia": {
        "title": "Wikipedia",
        "publisher": "Wikimedia Foundation and contributors",
        "homepage_url": "https://www.wikipedia.org/",
        "licence_code": "CC-BY-SA-4.0",
        "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    },
    "wikimedia_commons": {
        "title": "Wikimedia Commons",
        "publisher": "Wikimedia Foundation and contributors",
        "homepage_url": "https://commons.wikimedia.org/",
        "licence_code": "file_specific",
        "licence_url": None,
    },
    "open_tree_of_life": {
        "title": "Open Tree of Life",
        "publisher": "Open Tree of Life project",
        "homepage_url": "https://tree.opentreeoflife.org/",
        "licence_code": "source_specific",
        "licence_url": None,
    },
}


def stable_id(*parts: object) -> str:
    return str(uuid.uuid5(NAMESPACE, "|".join(str(part) for part in parts)))


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    records = json.loads(SEED.read_text(encoding="utf-8"))
    definitions = json.loads(FILTERS.read_text(encoding="utf-8"))
    source_registry = json.loads(SOURCES.read_text(encoding="utf-8"))
    metadata = json.loads(SEED_METADATA.read_text(encoding="utf-8"))
    configured_releases = json.loads(SOURCE_RELEASES_PATH.read_text(encoding="utf-8"))
    enrichment = json.loads(ENRICHMENT_PATH.read_text(encoding="utf-8"))

    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
        connection.execute("PRAGMA foreign_keys = ON")

        source_ids: dict[str, str] = {}
        release_ids: dict[str, str] = {}
        registry_by_key = {row["key"]: row for row in source_registry}
        registry_by_key.setdefault(
            "open_tree_of_life",
            {
                "key": "open_tree_of_life",
                "role": "phylogenetic_tree_and_taxonomy_cross_reference",
                "authority": "supplemental_phylogenetic",
                "enabled": True,
            },
        )

        for key, registry in registry_by_key.items():
            details = SOURCE_DETAILS.get(key, {})
            source_id = stable_id("source", key)
            source_ids[key] = source_id
            connection.execute(
                """INSERT INTO source_dataset
                   (id, key, title, publisher, homepage_url, licence_code,
                    licence_url, authority_role, enabled, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    source_id,
                    key,
                    details.get("title") or key.replace("_", " ").title(),
                    details.get("publisher"),
                    details.get("homepage_url"),
                    details.get("licence_code"),
                    details.get("licence_url"),
                    registry.get("authority", registry.get("role", "supplemental")),
                    1 if registry.get("enabled", True) else 0,
                    registry.get("role"),
                ),
            )

        seed_release_id = stable_id("release", "tree_id_trainer_v15_23", metadata["source_sha256"])
        release_ids["tree_id_trainer_v15_23"] = seed_release_id
        connection.execute(
            """INSERT INTO source_release
               (id, source_dataset_id, release_key, issued_on, imported_at, immutable_manifest_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                seed_release_id,
                source_ids["tree_id_trainer_v15_23"],
                "uploaded-v15.23-" + metadata["source_sha256"][:12],
                None,
                NOW,
                compact_json({
                    "source_sha256": metadata["source_sha256"],
                    "record_count": metadata["record_count"],
                    "seed_json_sha256": sha256(SEED),
                    "status": "imported",
                }),
            ),
        )

        # Register pinned external releases even before their taxa are imported.
        # `imported_at` remains null, so configured and imported data cannot be confused.
        for source_key, release in configured_releases.items():
            if source_key not in source_ids or not release.get("release_key"):
                continue
            release_id = stable_id("release", source_key, release["release_key"])
            release_ids[source_key] = release_id
            connection.execute(
                """INSERT INTO source_release
                   (id, source_dataset_id, release_key, issued_on, doi, download_url,
                    imported_at, immutable_manifest_json)
                   VALUES (?, ?, ?, ?, ?, ?, NULL, ?)""",
                (
                    release_id,
                    source_ids[source_key],
                    release["release_key"],
                    release.get("issued_on"),
                    release.get("doi"),
                    release.get("download_url"),
                    compact_json({**release, "status": "configured_not_imported"}),
                ),
            )

        definition_keys = {definition["key"] for definition in definitions}
        for order, definition in enumerate(definitions):
            values = definition.get("values", [])
            connection.execute(
                """INSERT INTO trait_definition
                   (key, label, group_name, data_type, filterable, multi_valued,
                    applicable_lineages_json, allowed_values_json, sort_order)
                   VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                (
                    definition["key"],
                    definition["label"],
                    definition["group"],
                    definition.get("dataType", "option"),
                    1 if definition.get("multiValued", False) else 0,
                    compact_json(definition.get("appliesTo", [])),
                    compact_json(values),
                    order,
                ),
            )

        classification_fields = {
            "domain": "domain",
            "kingdom": "kingdom",
            "phylum": "phylum",
            "class": "class",
            "order": "order",
            "family": "family",
            "genus": "genus",
        }
        reserved_fields = {
            "id", "sourceRecordIndex", "commonName", "scientificName", "profile",
            *classification_fields.keys(),
        }

        for record in records:
            taxon_id = record["id"]
            verification = "verified_seed_import"
            connection.execute(
                """INSERT INTO taxon
                   (id, canonical_scientific_name, canonical_rank, life_status,
                    canonical_source_release_id, verification_status,
                    source_record_index, created_at, updated_at)
                   VALUES (?, ?, 'species', ?, ?, ?, ?, ?, ?)""",
                (
                    taxon_id,
                    record["scientificName"],
                    str(record.get("lifeStatus", "Extant")).lower().replace(" ", "_"),
                    seed_release_id,
                    verification,
                    record["sourceRecordIndex"],
                    NOW,
                    NOW,
                ),
            )
            for status, name, language in (
                ("accepted_study_name", record["scientificName"], None),
                ("common", record["commonName"], "en"),
            ):
                connection.execute(
                    """INSERT INTO taxon_name
                       (id, taxon_id, name, status, language_code, source_release_id,
                        external_record_id, verification_status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        stable_id("name", taxon_id, status, name, language),
                        taxon_id,
                        name,
                        status,
                        language,
                        seed_release_id,
                        str(record["sourceRecordIndex"]),
                        verification,
                    ),
                )

            for source_key, rank in classification_fields.items():
                value = record.get(source_key)
                if value:
                    connection.execute(
                        """INSERT INTO taxon_classification
                           (taxon_id, rank, name, source_release_id, verification_status)
                           VALUES (?, ?, ?, ?, ?)""",
                        (taxon_id, rank, value, seed_release_id, verification),
                    )

            profile = record.get("profile", {})
            for section_key, body in (
                ("summary", profile.get("summary")),
                ("identifying_features", profile.get("features")),
                ("distribution", profile.get("distribution")),
            ):
                if body:
                    section_id = stable_id("profile", taxon_id, section_key, "en")
                    connection.execute(
                        """INSERT INTO profile_section
                           (id, taxon_id, section_key, language_code, body_markdown,
                            source_release_id, verification_status, assertion_status)
                           VALUES (?, ?, ?, 'en', ?, ?, 'verified_seed_import', 'published')""",
                        (section_id, taxon_id, section_key, body, seed_release_id),
                    )

            # Values explicitly present in the seed become sourced trait assertions.
            # The collection itself is an 80-tree course, so growth form=Tree is a
            # dataset-level fact rather than a biological guess about unknown taxa.
            seed_traits = {key: value for key, value in record.items() if key not in reserved_fields}
            seed_traits["plantForm"] = sorted(set([*seed_traits.get("plantForm", []), "Tree"]))
            seed_traits["taxonRank"] = "Species"
            seed_traits["profileStatus"] = "Seed shell only"
            seed_traits["taxonomyReconciliation"] = "Pending authoritative match"
            seed_traits["mediaStatus"] = "No licensed species media attached"
            seed_traits["hasCommonName"] = "Common name available"

            for key, value in seed_traits.items():
                if key not in definition_keys:
                    continue
                if value in (None, "", [], {}):
                    continue
                connection.execute(
                    """INSERT INTO taxon_trait_assertion
                       (id, taxon_id, trait_key, value_json, source_release_id,
                        citation_text, verification_status, assertion_status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, 'verified_seed_import', 'published', ?)""",
                    (
                        stable_id("trait", taxon_id, key, compact_json(value)),
                        taxon_id,
                        key,
                        compact_json(value),
                        seed_release_id,
                        f"Tree ID Trainer v15.23 seed record {record['sourceRecordIndex']}",
                        NOW,
                    ),
                )

            for source_key in ("catalogue_of_life", "gbif"):
                connection.execute(
                    """INSERT INTO reconciliation_queue
                       (taxon_id, source_dataset_id, searched_name, status, notes)
                       VALUES (?, ?, ?, 'pending', ?)""",
                    (
                        taxon_id,
                        source_ids[source_key],
                        record["scientificName"],
                        "Requires live source lookup and human review before authoritative publication.",
                    ),
                )

            citation_id = stable_id("citation", taxon_id, "seed")
            connection.execute(
                """INSERT INTO source_citation
                   (id, taxon_id, record_type, record_id, source_release_id,
                    citation_text, source_url, retrieved_at, licence_code)
                   VALUES (?, ?, 'taxon', ?, ?, ?, ?, ?, ?)""",
                (
                    citation_id,
                    taxon_id,
                    taxon_id,
                    seed_release_id,
                    f"Tree ID Trainer v15.23 verified seed, source record {record['sourceRecordIndex']}",
                    "https://www.treeidflashcards.com",
                    NOW,
                    "private_seed_reference",
                ),
            )

        apply_wa_authority_slice(
            connection=connection,
            enrichment=enrichment,
            source_ids=source_ids,
            release_ids=release_ids,
            seed_release_id=seed_release_id,
            definition_keys=definition_keys,
        )

        rebuild_projection(connection)
        connection.executemany(
            "INSERT INTO app_metadata(key, value_json) VALUES (?, ?)",
            [
                ("schema_version", compact_json("0.12.0")),
                ("built_at", compact_json(NOW)),
                ("seed_record_count", compact_json(len(records))),
                ("seed_sha256", compact_json(metadata["source_sha256"])),
                ("authority_slice_key", compact_json(enrichment["sliceKey"])),
                ("authority_slice_record_count", compact_json(len(enrichment["records"]))),
                ("authority_slice_reviewed_at", compact_json(enrichment["reviewedAt"])),
                ("authority_slice_source_warning", compact_json(enrichment["sourceWarning"])),
                ("production_database", compact_json("PostgreSQL 16 + PostGIS + ltree")),
                ("development_database", compact_json("SQLite 3 disposable local build")),
            ],
        )
        connection.commit()


def rebuild_projection(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM taxon_search_projection")
    taxa = connection.execute(
        "SELECT id, canonical_scientific_name, life_status, verification_status FROM taxon ORDER BY source_record_index"
    ).fetchall()
    for taxon_id, scientific, life_status, verification in taxa:
        names = connection.execute(
            "SELECT name, status FROM taxon_name WHERE taxon_id = ?",
            (taxon_id,),
        ).fetchall()
        common_name = next((name for name, status in names if status == "common"), scientific)
        classifications = dict(connection.execute(
            "SELECT rank, name FROM taxon_classification WHERE taxon_id = ?",
            (taxon_id,),
        ).fetchall())
        traits: dict[str, list[Any]] = {}
        for key, value_json in connection.execute(
            "SELECT trait_key, value_json FROM taxon_trait_assertion WHERE taxon_id = ? AND assertion_status = 'published'",
            (taxon_id,),
        ):
            value = json.loads(value_json)
            if isinstance(value, list):
                traits.setdefault(key, []).extend(value)
            else:
                traits.setdefault(key, []).append(value)
        traits = {key: sorted(set(values), key=lambda item: str(item)) for key, values in traits.items()}
        reconciliation = connection.execute(
            """SELECT CASE
                 WHEN SUM(CASE WHEN status IN ('matched', 'approved', 'specialist_confirmed') THEN 1 ELSE 0 END) >= 3 THEN 'Authoritatively matched'
                 WHEN SUM(CASE WHEN status IN ('matched', 'approved', 'specialist_confirmed') THEN 1 ELSE 0 END) > 0 THEN 'Partially matched'
                 WHEN SUM(CASE WHEN status = 'review_required' THEN 1 ELSE 0 END) > 0 THEN 'Review required'
                 ELSE 'Pending authoritative match' END
               FROM reconciliation_queue WHERE taxon_id = ?""",
            (taxon_id,),
        ).fetchone()[0]
        search_text = " ".join(filter(None, [
            scientific, common_name,
            classifications.get("family"), classifications.get("genus"),
            classifications.get("order"), classifications.get("class"),
            classifications.get("phylum"), classifications.get("kingdom"),
        ])).casefold()
        source_pack = (traits.get("sourcePack") or ["Tree ID Trainer 80"])[0]
        profile_status = (traits.get("profileStatus") or ["Seed shell only"])[0]
        image_status = (traits.get("verifiedImages") or ["Not available"])[0]
        connection.execute(
            """INSERT INTO taxon_search_projection
               (taxon_id, scientific_name, common_name, domain_name, kingdom_name,
                phylum_name, class_name, order_name, family_name, genus_name,
                life_status, verification_status, source_pack,
                reconciliation_status, profile_status, image_status,
                traits_json, searchable_text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                taxon_id, scientific, common_name,
                classifications.get("domain"), classifications.get("kingdom"),
                classifications.get("phylum"), classifications.get("class"),
                classifications.get("order"), classifications.get("family"),
                classifications.get("genus"), life_status, verification,
                source_pack, reconciliation, profile_status, image_status,
                compact_json(traits), search_text,
            ),
        )


def apply_wa_authority_slice(
    connection: sqlite3.Connection,
    enrichment: dict[str, Any],
    source_ids: dict[str, str],
    release_ids: dict[str, str],
    seed_release_id: str,
    definition_keys: set[str],
) -> None:
    """Apply the manually curated, source-aware sixty-taxon evidence slice.

    The source taxon remains the stable internal concept. Florabase material is
    attached as specialist regional evidence, not allowed to silently replace
    the canonical global taxonomy. Commons media are stored as individually
    licensed records with source pages and creators retained.
    """
    florabase_release_id = release_ids["florabase"]
    connection.execute(
        """UPDATE source_release SET imported_at = ?, immutable_manifest_json = ?
           WHERE id = ?""",
        (
            NOW,
            compact_json({
                "status": "curated_profile_slice_imported",
                "slice_key": enrichment["sliceKey"],
                "record_count": len(enrichment["records"]),
                "retrieved_on": enrichment["version"],
                "source_warning": enrichment["sourceWarning"],
            }),
            florabase_release_id,
        ),
    )
    commons_release_id = stable_id("release", "wikimedia_commons", f"retrieved-{enrichment['version']}")
    release_ids["wikimedia_commons"] = commons_release_id
    connection.execute(
        """INSERT OR IGNORE INTO source_release
           (id, source_dataset_id, release_key, issued_on, imported_at, immutable_manifest_json)
           VALUES (?, ?, ?, NULL, ?, ?)""",
        (
            commons_release_id,
            source_ids["wikimedia_commons"],
            f"retrieved-{enrichment['version']}",
            NOW,
            compact_json({
                "status": "file_level_metadata_curated",
                "retrieved_on": enrichment["version"],
                "licensing": "Each media asset retains its own licence and source page.",
            }),
        ),
    )

    wikipedia_release_id = stable_id("release", "wikipedia", f"retrieved-{enrichment['version']}")
    release_ids["wikipedia"] = wikipedia_release_id
    connection.execute(
        """INSERT OR IGNORE INTO source_release
           (id, source_dataset_id, release_key, issued_on, imported_at, immutable_manifest_json)
           VALUES (?, ?, ?, NULL, ?, ?)""",
        (
            wikipedia_release_id,
            source_ids["wikipedia"],
            f"retrieved-{enrichment['version']}",
            NOW,
            compact_json({
                "status": "revision_pinned_supplemental_profiles",
                "retrieved_on": enrichment["version"],
                "licensing": "Wikipedia profile text is paraphrased and revision-pinned; CC BY-SA attribution retained.",
            }),
        ),
    )

    powo_release_id = release_ids.get("plants_of_the_world_online")
    if powo_release_id:
        connection.execute(
            """UPDATE source_release SET imported_at = ?, immutable_manifest_json = ?
               WHERE id = ?""",
            (
                NOW,
                compact_json({
                    "status": "record_level_name_status_cross_checks_imported",
                    "retrieved_on": enrichment["version"],
                    "record_count": sum(1 for row in enrichment["records"] if row.get("secondarySources")),
                    "scope": "Record-level accepted-name, synonym, authorship and native-range cross-checks; not a bulk POWO import.",
                }),
                powo_release_id,
            ),
        )

    for record in enrichment["records"]:
        taxon_id = record["taxonId"]
        record_source_key = record.get("source", {}).get("key", "florabase")
        record_release_id = release_ids.get(record_source_key, florabase_release_id)
        record_source_id = source_ids.get(record_source_key, source_ids["florabase"])
        exists = connection.execute("SELECT 1 FROM taxon WHERE id = ?", (taxon_id,)).fetchone()
        if not exists:
            raise ValueError(f"Authority slice references unknown taxon: {taxon_id}")

        # Preserve the trainer's canonical binomial while enriching the accepted
        # name record with botanical authorship and specialist source evidence.
        connection.execute(
            """UPDATE taxon_name SET authorship = ?, verification_status = 'specialist_import'
               WHERE taxon_id = ? AND status = 'accepted_study_name' AND name = ?""",
            (record.get("authorship"), taxon_id, record["scientificName"]),
        )
        regional_name = record.get("regionalScientificName", record["scientificName"])
        regional_authorship = record.get("regionalAuthorship", record.get("authorship"))
        connection.execute(
            """INSERT OR IGNORE INTO taxon_name
               (id, taxon_id, name, authorship, status, language_code,
                source_release_id, external_record_id, verification_status)
               VALUES (?, ?, ?, ?, 'accepted_regional_name', NULL, ?, ?, 'specialist_import')""",
            (
                stable_id("name", taxon_id, "accepted_regional_name", regional_name, "florabase"),
                taxon_id,
                regional_name,
                regional_authorship,
                record_release_id,
                record.get("externalIdentifiers", {}).get(record_source_key) or record.get("externalIdentifiers", {}).get("wikipediaPageId") or record.get("externalIdentifiers", {}).get("florabase"),
            ),
        )
        connection.execute(
            """UPDATE taxon SET verification_status = 'specialist_import',
                   last_reviewed_at = ?, updated_at = ? WHERE id = ?""",
            (enrichment["reviewedAt"], NOW, taxon_id),
        )

        profile_id = record.get("externalIdentifiers", {}).get(record_source_key) or record.get("externalIdentifiers", {}).get("wikipediaPageId") or record.get("externalIdentifiers", {}).get("florabase")
        connection.execute(
            """INSERT OR REPLACE INTO taxon_external_identifier
               (taxon_id, source_dataset_id, external_id, external_url, source_release_id)
               VALUES (?, ?, ?, ?, ?)""",
            (
                taxon_id,
                record_source_id,
                profile_id,
                record["source"]["url"],
                record_release_id,
            ),
        )

        for secondary in record.get("secondarySources", []):
            secondary_key = secondary.get("key")
            if not secondary_key or secondary_key not in source_ids or secondary_key not in release_ids:
                continue
            secondary_source_id = source_ids[secondary_key]
            secondary_release_id = release_ids[secondary_key]
            secondary_external_id = secondary.get("externalId") or secondary.get("acceptedName") or record["scientificName"]
            connection.execute(
                """INSERT OR REPLACE INTO taxon_external_identifier
                   (taxon_id, source_dataset_id, external_id, external_url, source_release_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (taxon_id, secondary_source_id, secondary_external_id, secondary.get("url"), secondary_release_id),
            )
            connection.execute(
                """INSERT OR REPLACE INTO source_citation
                   (id, taxon_id, record_type, record_id, source_release_id,
                    citation_text, source_url, retrieved_at, licence_code)
                   VALUES (?, ?, 'taxon_external_identifier', ?, ?, ?, ?, ?, 'source_terms_apply')""",
                (
                    stable_id("citation", taxon_id, secondary_key, secondary_external_id),
                    taxon_id,
                    secondary_external_id,
                    secondary_release_id,
                    secondary.get("citation") or f"{secondary_key} record for {record['scientificName']}",
                    secondary.get("url"),
                    enrichment["reviewedAt"],
                ),
            )

        for rank, name in record.get("classification", {}).items():
            connection.execute(
                """INSERT INTO taxon_classification
                   (taxon_id, rank, name, source_release_id, verification_status)
                   VALUES (?, ?, ?, ?, 'specialist_import')
                   ON CONFLICT(taxon_id, rank) DO UPDATE SET
                     name = excluded.name,
                     source_release_id = excluded.source_release_id,
                     verification_status = excluded.verification_status""",
                (taxon_id, rank, name, record_release_id),
            )

        enriched_keys = [key for key in record.get("traits", {}) if key in definition_keys]
        if enriched_keys:
            placeholders = ",".join("?" for _ in enriched_keys)
            connection.execute(
                f"DELETE FROM taxon_trait_assertion WHERE taxon_id = ? AND trait_key IN ({placeholders})",
                [taxon_id, *enriched_keys],
            )
        for key, value in record.get("traits", {}).items():
            if key not in definition_keys or value in (None, "", [], {}):
                continue
            connection.execute(
                """INSERT INTO taxon_trait_assertion
                   (id, taxon_id, trait_key, value_json, source_release_id,
                    citation_text, verification_status, assertion_status,
                    reviewed_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'specialist_import', 'published', ?, ?)""",
                (
                    stable_id("trait", taxon_id, key, compact_json(value), f"florabase-{enrichment['version']}"),
                    taxon_id,
                    key,
                    compact_json(value),
                    record_release_id,
                    record["source"]["citation"],
                    enrichment["reviewedAt"],
                    NOW,
                ),
            )

        for section_key, body in record.get("profileSections", {}).items():
            section_id = stable_id("profile", taxon_id, section_key, "en")
            connection.execute(
                """INSERT INTO profile_section
                   (id, taxon_id, section_key, language_code, body_markdown,
                    source_release_id, source_revision, licence_code,
                    verification_status, assertion_status, last_reviewed_at)
                   VALUES (?, ?, ?, 'en', ?, ?, ?, 'source_terms_apply',
                           'specialist_import', 'published', ?)
                   ON CONFLICT(taxon_id, section_key, language_code) DO UPDATE SET
                     body_markdown = excluded.body_markdown,
                     source_release_id = excluded.source_release_id,
                     source_revision = excluded.source_revision,
                     licence_code = excluded.licence_code,
                     verification_status = excluded.verification_status,
                     assertion_status = excluded.assertion_status,
                     last_reviewed_at = excluded.last_reviewed_at""",
                (
                    section_id,
                    taxon_id,
                    section_key,
                    body,
                    record_release_id,
                    f"{record_source_key} profile {profile_id}; curated {enrichment['version']}",
                    enrichment["reviewedAt"],
                ),
            )
            connection.execute(
                """INSERT OR REPLACE INTO source_citation
                   (id, taxon_id, record_type, record_id, source_release_id,
                    citation_text, source_url, retrieved_at, licence_code)
                   VALUES (?, ?, 'profile_section', ?, ?, ?, ?, ?, 'source_terms_apply')""",
                (
                    stable_id("citation", taxon_id, "profile", section_key, "florabase"),
                    taxon_id,
                    section_id,
                    record_release_id,
                    record["source"]["citation"],
                    record["source"]["url"],
                    enrichment["reviewedAt"],
                ),
            )

        connection.execute(
            """INSERT INTO reconciliation_queue
               (taxon_id, source_dataset_id, searched_name, status,
                proposed_external_id, proposed_scientific_name, proposed_rank,
                confidence, notes, checked_at)
               VALUES (?, ?, ?, 'specialist_confirmed', ?, ?, 'species', 1.0, ?, ?)
               ON CONFLICT(taxon_id, source_dataset_id) DO UPDATE SET
                 searched_name = excluded.searched_name,
                 status = excluded.status,
                 proposed_external_id = excluded.proposed_external_id,
                 proposed_scientific_name = excluded.proposed_scientific_name,
                 proposed_rank = excluded.proposed_rank,
                 confidence = excluded.confidence,
                 notes = excluded.notes,
                 checked_at = excluded.checked_at""",
            (
                taxon_id,
                record_source_id,
                record["scientificName"],
                profile_id,
                regional_name,
                f"{record['acceptedNameStatus']}. {enrichment['sourceWarning']}",
                enrichment["reviewedAt"],
            ),
        )

        for index, media in enumerate(record.get("media", [])):
            file_name = media["fileName"]
            media_id = stable_id("media", "wikimedia_commons", file_name)
            original_url = (
                "https://commons.wikimedia.org/wiki/Special:Redirect/file/"
                + quote(file_name, safe="")
                + "?width=1600"
            )
            local_media_path = ROOT / "apps" / "web" / "media" / "thumbs" / f"{taxon_id}.jpg"
            storage_key = f"/media/thumbs/{taxon_id}.jpg" if local_media_path.exists() else None
            local_sha256 = sha256(local_media_path) if local_media_path.exists() else None
            connection.execute(
                """INSERT OR REPLACE INTO media_asset
                   (id, storage_key, original_url, media_type, title, creator,
                    source_page_url, licence_code, licence_url, captured_at,
                    verification_status, metadata_json, created_at)
                   VALUES (?, ?, ?, 'image', ?, ?, ?, ?, ?, ?,
                           'specialist_import', ?, ?)""",
                (
                    media_id,
                    storage_key,
                    original_url,
                    media.get("title"),
                    media.get("creator"),
                    media.get("sourcePageUrl"),
                    media.get("licenceCode"),
                    media.get("licenceUrl"),
                    media.get("capturedAt"),
                    compact_json({
                        "file_name": file_name,
                        "retrieved_on": enrichment["version"],
                        "source": "Wikimedia Commons",
                        "licence_verified": True,
                        "locally_stored": bool(storage_key),
                        "local_sha256": local_sha256,
                    }),
                    NOW,
                ),
            )
            connection.execute(
                """INSERT OR REPLACE INTO media_taxon
                   (media_asset_id, taxon_id, category, caption, diagnostic_notes, is_primary)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    media_id,
                    taxon_id,
                    media["category"],
                    media.get("caption"),
                    "Licence and creator metadata checked against the individual Commons file page.",
                    1 if index == 0 else 0,
                ),
            )
            connection.execute(
                """INSERT OR REPLACE INTO source_citation
                   (id, taxon_id, record_type, record_id, source_release_id,
                    citation_text, source_url, retrieved_at, licence_code)
                   VALUES (?, ?, 'media_asset', ?, ?, ?, ?, ?, ?)""",
                (
                    stable_id("citation", taxon_id, "media", file_name),
                    taxon_id,
                    media_id,
                    commons_release_id,
                    f"{media.get('title') or file_name}, {media.get('creator') or 'creator not recorded'}, {media.get('licenceCode')}",
                    media.get("sourcePageUrl"),
                    enrichment["reviewedAt"],
                    media.get("licenceCode"),
                ),
            )

        connection.execute(
            """INSERT OR REPLACE INTO review_decision
               (id, taxon_id, source_dataset_id, decision, reviewer,
                rationale, previous_status, new_status, decided_at)
               VALUES (?, ?, ?, 'approve_specialist_evidence', 'ArbotFlash curated source pass',
                       ?, 'pending', 'specialist_confirmed', ?)""",
            (
                stable_id("review", taxon_id, record_source_key, enrichment["version"]),
                taxon_id,
                record_source_id,
                f"Curated {record_source_key} profile {profile_id}; global backbone confirmation remains pending.",
                enrichment["reviewedAt"],
            ),
        )
        connection.execute(
            """INSERT OR REPLACE INTO audit_event
               (id, actor, action, entity_type, entity_id, before_json, after_json, created_at)
               VALUES (?, 'ArbotFlash curated source pass', 'import_specialist_evidence',
                       'taxon', ?, ?, ?, ?)""",
            (
                stable_id("audit", taxon_id, record_source_key, enrichment["version"]),
                taxon_id,
                compact_json({"verification_status": "verified_seed_import"}),
                compact_json({
                    "verification_status": "specialist_import",
                    "source": record_source_key,
                    "profile_id": profile_id,
                    "licensed_media": len(record.get("media", [])),
                }),
                enrichment["reviewedAt"],
            ),
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    build(args.db.resolve())
    print(f"Built {args.db.resolve()}")


if __name__ == "__main__":
    main()
