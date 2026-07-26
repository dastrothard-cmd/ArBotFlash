#!/usr/bin/env python3
"""Stage a Darwin Core Archive taxon core in the Arbot Taxa Registry.

This importer deliberately writes source records only. Mapping records onto stable
Arbot concepts and publishing an accepted-name projection are separate reviewed
steps so an upstream release can never silently rewrite a professional catalogue.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sqlite3
import sys
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree


TAXON_ROW_TYPE = "http://rs.tdwg.org/dwc/terms/Taxon"


@dataclass(frozen=True)
class CoreDefinition:
    location: str
    encoding: str
    delimiter: str
    quotechar: str | None
    line_terminator: str
    ignore_header_lines: int
    id_index: int | None
    fields: dict[int, str]


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def decode_separator(value: str | None, fallback: str) -> str:
    if value is None or value == "":
        return fallback
    try:
        return bytes(value, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return value


def term_name(term: str) -> str:
    return term.rstrip("/").rsplit("/", 1)[-1]


def archive_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_core(meta_xml: bytes) -> CoreDefinition:
    root = ElementTree.fromstring(meta_xml)
    core = next((node for node in root.iter() if local_name(node.tag) == "core"), None)
    if core is None:
        raise ValueError("meta.xml does not define a Darwin Core core")
    row_type = core.attrib.get("rowType", "")
    if row_type and row_type != TAXON_ROW_TYPE and not row_type.endswith("/Taxon"):
        raise ValueError(f"Darwin Core core is not a Taxon core: {row_type}")

    location = ""
    id_index: int | None = None
    fields: dict[int, str] = {}
    for child in core:
        name = local_name(child.tag)
        if name == "files":
            location_node = next((node for node in child if local_name(node.tag) == "location"), None)
            if location_node is not None and location_node.text:
                location = location_node.text.strip()
        elif name == "id":
            id_index = int(child.attrib["index"])
        elif name == "field":
            index = int(child.attrib["index"])
            fields[index] = term_name(child.attrib.get("term", f"field_{index}"))

    if not location:
        raise ValueError("meta.xml taxon core does not include a file location")

    delimiter = decode_separator(core.attrib.get("fieldsTerminatedBy"), ",")
    quote_value = decode_separator(core.attrib.get("fieldsEnclosedBy"), '"')
    quotechar = quote_value[0] if quote_value else None
    line_terminator = decode_separator(core.attrib.get("linesTerminatedBy"), "\n")
    encoding = core.attrib.get("encoding", "UTF-8")
    ignore_header_lines = int(core.attrib.get("ignoreHeaderLines", "0"))

    if len(delimiter) != 1:
        raise ValueError(f"Only single-character Darwin Core delimiters are supported: {delimiter!r}")

    return CoreDefinition(
        location=location,
        encoding=encoding,
        delimiter=delimiter,
        quotechar=quotechar,
        line_terminator=line_terminator,
        ignore_header_lines=ignore_header_lines,
        id_index=id_index,
        fields=fields,
    )


def initialise_database(connection: sqlite3.Connection, schema_path: Path) -> None:
    connection.executescript(schema_path.read_text(encoding="utf-8"))


def text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def select_field(record: dict[str, str], *names: str) -> str:
    for name in names:
        value = record.get(name, "").strip()
        if value:
            return value
    return ""


def iter_taxa(archive: zipfile.ZipFile, definition: CoreDefinition) -> Iterable[dict[str, str]]:
    try:
        raw = archive.open(definition.location, "r")
    except KeyError as error:
        candidates = [name for name in archive.namelist() if name.endswith(definition.location)]
        if len(candidates) != 1:
            raise ValueError(f"Taxon core file not found in archive: {definition.location}") from error
        raw = archive.open(candidates[0], "r")

    with raw, io.TextIOWrapper(raw, encoding=definition.encoding, errors="replace", newline="") as handle:
        reader = csv.reader(
            handle,
            delimiter=definition.delimiter,
            quotechar=definition.quotechar,
            quoting=csv.QUOTE_MINIMAL if definition.quotechar else csv.QUOTE_NONE,
        )
        for _ in range(definition.ignore_header_lines):
            next(reader, None)
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            record = {
                field_name: row[index].strip() if index < len(row) else ""
                for index, field_name in definition.fields.items()
            }
            if definition.id_index is not None and definition.id_index < len(row):
                record["__core_id"] = row[definition.id_index].strip()
            yield record


def release_identifier(source: str, version: str, sha256: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"arbot-taxa:{source}:{version}:{sha256}"))


def stage_archive(args: argparse.Namespace) -> int:
    archive_path = Path(args.archive).resolve()
    database_path = Path(args.db).resolve()
    schema_path = Path(args.schema).resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    digest = archive_sha256(archive_path)
    release_id = release_identifier(args.source, args.release, digest)
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    with zipfile.ZipFile(archive_path) as archive:
        definition = parse_core(archive.read("meta.xml"))
        connection = sqlite3.connect(database_path)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            initialise_database(connection, schema_path)
            existing = connection.execute(
                "SELECT record_count, status FROM registry_releases WHERE id = ?",
                (release_id,),
            ).fetchone()
            if existing and not args.replace:
                print(json.dumps({
                    "releaseId": release_id,
                    "status": "already-staged",
                    "recordCount": existing[0],
                    "releaseStatus": existing[1],
                }, indent=2))
                return 0

            with connection:
                if existing:
                    connection.execute("DELETE FROM registry_releases WHERE id = ?", (release_id,))
                connection.execute(
                    """
                    INSERT INTO registry_releases (
                      id, source_id, source_version, source_dataset_id, source_url,
                      published_at, retrieved_at, archive_sha256, licence, citation,
                      record_count, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'staged')
                    """,
                    (
                        release_id,
                        args.source,
                        args.release,
                        args.dataset_id or "",
                        args.source_url or archive_path.as_uri(),
                        args.published_at or None,
                        retrieved_at,
                        digest,
                        args.licence or "",
                        args.citation or "",
                    ),
                )

                insert_sql = """
                    INSERT INTO source_taxa (
                      release_id, source_taxon_id, scientific_name, authorship, rank,
                      taxonomic_status, nomenclatural_status, accepted_source_taxon_id,
                      parent_source_taxon_id, kingdom, family, genus, name_according_to,
                      dataset_name, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                batch: list[tuple[str, ...]] = []
                count = 0
                skipped = 0
                for record in iter_taxa(archive, definition):
                    source_taxon_id = select_field(record, "taxonID", "__core_id")
                    scientific_name = select_field(record, "scientificName", "canonicalName")
                    if not source_taxon_id or not scientific_name:
                        skipped += 1
                        continue
                    batch.append((
                        release_id,
                        source_taxon_id,
                        scientific_name,
                        select_field(record, "scientificNameAuthorship", "namePublishedInYear"),
                        select_field(record, "taxonRank"),
                        select_field(record, "taxonomicStatus"),
                        select_field(record, "nomenclaturalStatus"),
                        select_field(record, "acceptedNameUsageID", "acceptedTaxonID"),
                        select_field(record, "parentNameUsageID", "parentTaxonID"),
                        select_field(record, "kingdom"),
                        select_field(record, "family"),
                        select_field(record, "genus"),
                        select_field(record, "nameAccordingTo", "nameAccordingToID"),
                        select_field(record, "datasetName"),
                        json.dumps(record, ensure_ascii=False, separators=(",", ":")),
                    ))
                    if len(batch) >= args.batch_size:
                        connection.executemany(insert_sql, batch)
                        count += len(batch)
                        batch.clear()
                if batch:
                    connection.executemany(insert_sql, batch)
                    count += len(batch)
                connection.execute(
                    "UPDATE registry_releases SET record_count = ? WHERE id = ?",
                    (count, release_id),
                )

            print(json.dumps({
                "releaseId": release_id,
                "source": args.source,
                "version": args.release,
                "archiveSha256": digest,
                "recordCount": count,
                "skippedRecords": skipped,
                "status": "staged",
                "database": str(database_path),
            }, indent=2))
            return 0
        finally:
            connection.close()


def parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--db", required=True, help="SQLite registry database")
    result.add_argument("--archive", required=True, help="Local Darwin Core Archive ZIP")
    result.add_argument("--source", required=True, help="Stable source identifier, e.g. wcvp")
    result.add_argument("--release", required=True, help="Pinned source release version")
    result.add_argument("--schema", default=str(root / "schema.sql"))
    result.add_argument("--dataset-id", default="")
    result.add_argument("--source-url", default="")
    result.add_argument("--published-at", default="")
    result.add_argument("--licence", default="")
    result.add_argument("--citation", default="")
    result.add_argument("--batch-size", type=int, default=5000)
    result.add_argument("--replace", action="store_true")
    return result


def main() -> int:
    try:
        return stage_archive(parser().parse_args())
    except (OSError, ValueError, sqlite3.Error, zipfile.BadZipFile) as error:
        print(f"taxa-registry ingest failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
