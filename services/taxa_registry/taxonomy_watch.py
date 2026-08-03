#!/usr/bin/env python3
"""Check configured taxonomy authorities for upstream release changes.

The watcher records only release signals such as ETag, Last-Modified, content
length and final URL. It never publishes taxonomy automatically. A changed
signal creates a review report that can trigger a pull request and a pinned
source ingestion run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


USER_AGENT = "ArbotTaxaRegistry/0.1 (+https://github.com/dastrothard-cmd/ArBotFlash)"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def request_headers(url: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        if error.code not in {400, 403, 405, 501}:
            raise
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"},
        )
        response = urllib.request.urlopen(request, timeout=timeout)

    with response:
        headers = response.headers
        signature_fields = {
            "finalUrl": response.geturl(),
            "etag": headers.get("ETag", ""),
            "lastModified": headers.get("Last-Modified", ""),
            "contentLength": headers.get("Content-Length", ""),
            "contentType": headers.get("Content-Type", ""),
        }
        signature = hashlib.sha256(
            json.dumps(signature_fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return {**signature_fields, "signature": signature}


def source_watch_target(source: dict[str, Any]) -> str:
    watch_mode = source.get("watchMode", "manual")
    if watch_mode == "archive-headers":
        return source.get("archiveUrl", "")
    if watch_mode == "landing-page":
        return source.get("releasePage", "")
    if watch_mode == "manual":
        return ""
    raise ValueError(f"unsupported watchMode for {source.get('id', '<unknown>')}: {watch_mode}")


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def check_sources(args: argparse.Namespace) -> int:
    source_path = Path(args.sources)
    state_path = Path(args.state)
    report_path = Path(args.report)
    config = load_json(source_path, {})
    prior_state = load_json(state_path, {"schemaVersion": 1, "sources": {}})
    prior_sources = prior_state.get("sources", {}) if isinstance(prior_state, dict) else {}

    checked_at = utc_now()
    current_sources: dict[str, Any] = {}
    changes: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for source in config.get("sources", []):
        source_id = source.get("id", "")
        if not source_id:
            continue
        watch_mode = source.get("watchMode", "manual")
        target = source_watch_target(source)
        if not target:
            current_sources[source_id] = {
                "checkedAt": checked_at,
                "watchMode": watch_mode,
                "status": "manual",
            }
            continue
        try:
            signal = request_headers(target, args.timeout)
            previous = prior_sources.get(source_id, {})
            changed = bool(previous.get("signature") and previous.get("signature") != signal["signature"])
            first_seen = not bool(previous.get("signature"))
            current_sources[source_id] = {
                **signal,
                "checkedAt": checked_at,
                "watchMode": watch_mode,
                "status": "changed" if changed else "current",
            }
            if changed or (first_seen and args.report_first_seen):
                changes.append({
                    "sourceId": source_id,
                    "name": source.get("name", source_id),
                    "target": target,
                    "changeType": "source-release-signal",
                    "previous": {key: previous.get(key, "") for key in ("signature", "etag", "lastModified", "contentLength", "finalUrl")},
                    "current": signal,
                    "reviewRequired": True,
                    "recommendedAction": "Pin the new release, download it to staging, verify licence/citation, ingest it, compare taxonomy events, then request human review.",
                })
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            errors.append({"sourceId": source_id, "target": target, "error": str(error)})
            current_sources[source_id] = {
                **prior_sources.get(source_id, {}),
                "checkedAt": checked_at,
                "watchMode": watch_mode,
                "status": "error",
                "error": str(error),
            }

    next_state = {
        "schemaVersion": 1,
        "checkedAt": checked_at,
        "sources": current_sources,
    }
    report = {
        "schemaVersion": 1,
        "generatedAt": checked_at,
        "sourceConfig": str(source_path),
        "changed": bool(changes),
        "changeCount": len(changes),
        "errorCount": len(errors),
        "changes": changes,
        "errors": errors,
        "publicationBlocked": True,
        "publicationRule": "Taxonomy changes require a reviewed pinned release and must never publish from this watcher alone.",
    }
    write_json(state_path, next_state)
    write_json(report_path, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if errors and args.fail_on_error:
        return 2
    return 0


def parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--sources", default=str(root / "config" / "sources.json"))
    result.add_argument("--state", default=str(root / "state" / "source-state.json"))
    result.add_argument("--report", default="taxonomy-watch-report.json")
    result.add_argument("--timeout", type=int, default=30)
    result.add_argument("--report-first-seen", action="store_true")
    result.add_argument("--fail-on-error", action="store_true")
    return result


def main() -> int:
    try:
        return check_sources(parser().parse_args())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"taxonomy watch failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
