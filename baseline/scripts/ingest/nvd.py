"""NVD CVE 2.0 REST API → ingest records.

Pulls HIGH and CRITICAL CVEs across a window (default: trailing 12 months).
Page size 2000 (NVD's max). Rate-limited Retry. Cache per (start, end, severity).
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, List, Optional

from .common import cache_path, normalize_record, _session

logger = logging.getLogger("ingest.nvd")

API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
PAGE = 2000


def _fmt_dt(d: datetime) -> str:
    """NVD wants 'YYYY-MM-DDTHH:MM:SS.fff' (no zone suffix, milliseconds optional)."""
    return d.strftime("%Y-%m-%dT%H:%M:%S.000")


def _split_window(start: datetime, end: datetime, days: int = 120) -> List[tuple]:
    """NVD only allows 120-day windows per request; split as needed."""
    out = []
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=days - 1), end)
        out.append((cur, nxt))
        cur = nxt + timedelta(seconds=1)
    return out


def _pull_window(session, start: datetime, end: datetime, severity: str,
                 api_key: Optional[str], cache_file: Path,
                 throttle_seconds: float) -> dict:
    """Fetch one window of (severity, start..end). Returns the merged JSON."""
    if cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                obj = json.load(f)
            if obj.get("__complete"):
                logger.info("nvd cache hit: %s", cache_file.name)
                return obj
        except Exception:
            pass

    headers = {}
    if api_key:
        headers["apiKey"] = api_key
    params_base = {
        "pubStartDate":     _fmt_dt(start),
        "pubEndDate":       _fmt_dt(end),
        "cvssV3Severity":   severity,
        "resultsPerPage":   PAGE,
    }
    all_vulns: list = []
    start_index = 0
    total = None
    while True:
        params = dict(params_base, startIndex=start_index)
        logger.info("nvd: GET %s..%s [%s] startIndex=%d",
                    start.date(), end.date(), severity, start_index)
        r = session.get(API_URL, params=params, headers=headers, timeout=120)
        if r.status_code == 403 and not api_key:
            logger.warning("nvd: 403 unauthenticated — sleeping 30s and retrying")
            time.sleep(30)
            continue
        r.raise_for_status()
        data = r.json()
        if total is None:
            total = int(data.get("totalResults", 0))
            logger.info("nvd: %d results in window", total)
        all_vulns.extend(data.get("vulnerabilities", []))
        start_index += PAGE
        if start_index >= total or not data.get("vulnerabilities"):
            break
        time.sleep(throttle_seconds)

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "__complete": True,
        "window":     [start.isoformat(), end.isoformat(), severity],
        "vulnerabilities": all_vulns,
    }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return payload


def _build_record_text(cve: dict) -> tuple[str, str, str]:
    """Return (raw_text, cve_id, published_iso) for one CVE entry."""
    cve_id = cve.get("id", "").strip()
    descs = cve.get("descriptions", []) or []
    en = next((d.get("value", "") for d in descs if d.get("lang") == "en"), "")
    en = (en or "").strip()
    metrics = cve.get("metrics", {}) or {}
    cvss_v31 = metrics.get("cvssMetricV31", []) or []
    cvss_v30 = metrics.get("cvssMetricV30", []) or []
    cvss_v2  = metrics.get("cvssMetricV2", []) or []
    score = severity = vec = "N/A"
    if cvss_v31:
        m = cvss_v31[0].get("cvssData", {})
        score = str(m.get("baseScore", "N/A"))
        severity = m.get("baseSeverity", "N/A")
        vec = "v3.1"
    elif cvss_v30:
        m = cvss_v30[0].get("cvssData", {})
        score = str(m.get("baseScore", "N/A"))
        severity = m.get("baseSeverity", "N/A")
        vec = "v3.0"
    elif cvss_v2:
        m = cvss_v2[0].get("cvssData", {})
        score = str(m.get("baseScore", "N/A"))
        severity = "HIGH" if float(m.get("baseScore", 0) or 0) >= 7 else "MEDIUM"
        vec = "v2.0"

    # CWE
    cwes: list[str] = []
    for w in (cve.get("weaknesses") or []):
        for desc in (w.get("description") or []):
            v = desc.get("value")
            if v and v.startswith("CWE-"):
                cwes.append(v)
    cwes = sorted(set(cwes))

    # Affected products (capped)
    affected: list[str] = []
    for cfg in (cve.get("configurations") or []):
        for node in (cfg.get("nodes") or []):
            for m in (node.get("cpeMatch") or []):
                crit = m.get("criteria") or ""
                if crit:
                    # criteria looks like "cpe:2.3:a:microsoft:exchange_server:..."
                    parts = crit.split(":")
                    if len(parts) >= 6:
                        vendor = parts[3].replace("_", " ")
                        product = parts[4].replace("_", " ")
                        version = parts[5] if parts[5] not in ("-", "*") else ""
                        s = f"{vendor} {product} {version}".strip()
                        if s and s not in affected:
                            affected.append(s)
                if len(affected) >= 20:
                    break
            if len(affected) >= 20:
                break
        if len(affected) >= 20:
            break

    pub = cve.get("published", "")
    parts = [f"{cve_id}: {en}" if en else f"{cve_id}"]
    if affected:
        parts.append("Affected: " + "; ".join(affected) + ".")
    parts.append(f"CVSS {vec} base score: {score} ({severity}).")
    if cwes:
        parts.append("Weakness: " + ", ".join(cwes) + ".")
    parts.append(f"References: https://nvd.nist.gov/vuln/detail/{cve_id}")
    return " ".join(parts), cve_id, pub


def fetch_and_yield_records(cache_dir: Path,
                            max_records: int | None = None,
                            nvd_start: Optional[str] = None,
                            nvd_end: Optional[str] = None,
                            api_key_env: str = "NVD_API_KEY",
                            **_kwargs) -> Iterator[dict]:
    src = "nvd"
    end_dt = datetime.fromisoformat(nvd_end) if nvd_end else datetime.now(timezone.utc).replace(tzinfo=None)
    start_dt = datetime.fromisoformat(nvd_start) if nvd_start else (end_dt - timedelta(days=365))
    api_key = os.environ.get(api_key_env) or None
    throttle = 0.6 if api_key else 6.5    # NVD: 50/30s with key, 5/30s without
    if not api_key:
        logger.warning("nvd: NVD_API_KEY not set — running unauthenticated (5 req/30s)")
    session = _session()
    windows = _split_window(start_dt, end_dt)
    n = 0
    for severity in ("CRITICAL", "HIGH"):
        for (ws, we) in windows:
            cf = cache_path(cache_dir, src,
                            f"cves_{ws.date()}_{we.date()}_{severity}.json")
            try:
                payload = _pull_window(session, ws, we, severity, api_key, cf, throttle)
            except Exception as e:
                logger.warning("nvd: window %s..%s %s failed: %s", ws.date(), we.date(), severity, e)
                continue
            for v in payload.get("vulnerabilities", []):
                cve = v.get("cve") or {}
                if not cve:
                    continue
                raw_text, cve_id, pub = _build_record_text(cve)
                rec = normalize_record(
                    raw_text, source_forum=src,
                    timestamp=pub,
                    url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                    file_type="json",
                    file_info=f"nvd cves 2.0 {severity}",
                )
                if rec is None:
                    continue
                yield rec
                n += 1
                if max_records and n >= max_records:
                    logger.info("nvd: yielded %d (cap)", n)
                    return
    logger.info("nvd: yielded %d records", n)
