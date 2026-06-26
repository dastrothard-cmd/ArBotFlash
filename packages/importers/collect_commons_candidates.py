#!/usr/bin/env python3
"""Collect Wikimedia Commons image candidates without publishing them.

Only files carrying a clearly reusable licence in their own extmetadata are
retained. The output is a review-candidate JSON document; it does not create a
published media_asset or download a file into the public application.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "ArbotFlash/0.5 media-candidate-collector (development; contact configured by deployer)"
ALLOWED_PREFIXES = ("cc by", "cc-by", "cc by-sa", "cc-by-sa", "public domain", "pd", "cc0")


def clean(value: Any) -> str:
    text = value.get("value", "") if isinstance(value, dict) else str(value or "")
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return " ".join(text.split())


def reusable_licence(metadata: dict[str, Any]) -> bool:
    licence = " ".join(filter(None, [
        clean(metadata.get("LicenseShortName")),
        clean(metadata.get("License")),
        clean(metadata.get("UsageTerms")),
    ])).casefold()
    return any(token in licence for token in ALLOWED_PREFIXES)


def parse_candidates(scientific_name: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    pages = (payload.get("query") or {}).get("pages") or []
    if isinstance(pages, dict):
        pages = pages.values()
    for page in pages:
        imageinfo = (page.get("imageinfo") or [{}])[0]
        metadata = imageinfo.get("extmetadata") or {}
        if not reusable_licence(metadata):
            continue
        source_page = page.get("canonicalurl") or page.get("fullurl")
        output.append({
            "scientificName": scientific_name,
            "fileTitle": page.get("title"),
            "sourcePageUrl": source_page,
            "originalUrl": imageinfo.get("url"),
            "thumbnailUrl": imageinfo.get("thumburl"),
            "creator": clean(metadata.get("Artist")) or clean(metadata.get("Credit")),
            "licenceCode": clean(metadata.get("LicenseShortName")) or clean(metadata.get("License")),
            "licenceUrl": clean(metadata.get("LicenseUrl")),
            "description": clean(metadata.get("ImageDescription")),
            "dateTimeOriginal": clean(metadata.get("DateTimeOriginal")),
            "reviewStatus": "candidate_only",
            "reviewRule": "Human review required for identity, diagnostic value, creator attribution and file-level licence before publication.",
        })
    return output


def request_candidates(scientific_name: str, limit: int = 8) -> dict[str, Any]:
    query = urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrsearch": f'file:"{scientific_name}"',
        "gsrnamespace": 6, "gsrlimit": limit, "prop": "imageinfo|info", "inprop": "url",
        "iiprop": "url|extmetadata", "iiurlwidth": 1200, "format": "json", "formatversion": 2,
    })
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scientific_name")
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()
    payload = json.loads(args.fixture.read_text(encoding="utf-8")) if args.fixture else request_candidates(args.scientific_name, args.limit)
    result = {
        "scientificName": args.scientific_name,
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Wikimedia Commons Action API",
        "status": "review_candidates_only",
        "candidates": parse_candidates(args.scientific_name, payload),
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
