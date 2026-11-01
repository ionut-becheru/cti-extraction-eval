"""CISA Known Exploited Vulnerabilities catalog → ingest records.

Every entry is a CVE confirmed exploited in the wild — the strongest
per-record signal in the corpus.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterator

from .common import cache_path, download, normalize_record, _session

logger = logging.getLogger("ingest.cisa")

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def fetch_and_yield_records(cache_dir: Path, max_records: int | None = None,
                            **_kwargs) -> Iterator[dict]:
    src = "cisa_kev"
    p = cache_path(cache_dir, src, "known_exploited_vulnerabilities.json")
    download(KEV_URL, p, session=_session())
    with open(p, encoding="utf-8") as f:
        catalog = json.load(f)
    entries = catalog.get("vulnerabilities", []) or []
    logger.info("cisa_kev: %d entries", len(entries))

    n = 0
    for e in entries:
        cve = (e.get("cveID") or "").strip()
        if not cve:
            continue
        vendor = (e.get("vendorProject") or "").strip()
        product = (e.get("product") or "").strip()
        name = (e.get("vulnerabilityName") or "").strip()
        desc = (e.get("shortDescription") or "").strip()
        added = (e.get("dateAdded") or "").strip()
        due = (e.get("dueDate") or "").strip()
        action = (e.get("requiredAction") or "").strip()
        ransomware = (e.get("knownRansomwareCampaignUse") or "Unknown").strip()
        notes = (e.get("notes") or "").strip()

        if not desc:
            logger.debug("cisa_kev: skipped %s (no description)", cve)
            continue

        # Build the narrative
        parts: list[str] = []
        parts.append(f"{cve}: {name}." if name else f"{cve}.")
        parts.append(f"Vendor/Project: {vendor}.")
        parts.append(f"Product: {product}.")
        parts.append(desc)
        if added:
            parts.append(
                f"CISA added this vulnerability to the Known Exploited Vulnerabilities "
                f"(KEV) catalog on {added} because it is being actively exploited in the wild."
            )
        if action:
            parts.append(f"Required Action: {action}")
        if due:
            parts.append(f"Due date: {due}.")
        parts.append(f"Known to be used in ransomware campaigns: {ransomware}.")
        if notes:
            parts.append(f"Notes: {notes}")

        raw_text = " ".join(parts)
        rec = normalize_record(
            raw_text,
            source_forum=src,
            timestamp=added + "T00:00:00Z" if added else None,
            url=f"https://nvd.nist.gov/vuln/detail/{cve}",
            file_type="json",
            file_info="cisa kev catalog",
        )
        if rec is None:
            continue
        yield rec
        n += 1
        if max_records and n >= max_records:
            break
    logger.info("cisa_kev: yielded %d records", n)
