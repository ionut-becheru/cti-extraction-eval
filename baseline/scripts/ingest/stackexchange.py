"""Stack Exchange Information Security (security.stackexchange.com) → ingest.

Downloads the public .7z dump from archive.org, decompresses Posts.xml,
streams via iterparse, buffers questions and pairs them with their accepted
answer. Filters by cyber-relevant tag whitelist.

Dump license: CC BY-SA 4.0 (declared in script docstring; per-record `source`
field carries provenance).
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Iterator, Optional
from xml.etree.ElementTree import iterparse

from .common import cache_path, download, normalize_record, _session

logger = logging.getLogger("ingest.stackexchange")

DUMP_URL = "https://archive.org/download/stackexchange/security.stackexchange.com.7z"
DUMP_NAME = "security.stackexchange.com.7z"

# Cyber-relevant tag whitelist (any one is sufficient)
TAG_WHITELIST = {
    "malware", "exploit", "vulnerability", "apt", "ransomware",
    "forensics", "incident-response", "reverse-engineering",
    "network", "tls", "ssl", "authentication", "attack-prevention",
    "buffer-overflow", "sql-injection", "xss", "csrf", "cve",
    "penetration-test", "pentest", "passwords", "crypto", "cryptography",
    "firewall", "intrusion-detection", "ids", "ips", "siem",
    "phishing", "social-engineering", "botnet", "ddos", "denial-of-service",
    "ssh", "tor", "vpn", "active-directory", "kerberos", "ntlm",
    "iot-security", "ics", "scada", "cloud-security",
    "exploit-development", "shellcode",
}

# Stack Exchange uses pipe-separated tags in the dump: "|tag1|tag2|tag3|".
# (The angle-bracket format only appears on the live site HTML, not the XML.)
# `findall` on the pipe form has an overlap problem (every-other tag); split instead.
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ENTITIES = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
    "&#39;": "'", "&nbsp;": " ", "&apos;": "'",
}


def _strip_html(s: str) -> str:
    if not s:
        return ""
    out = _HTML_TAG_RE.sub(" ", s)
    for ent, ch in _HTML_ENTITIES.items():
        out = out.replace(ent, ch)
    return out


def _parse_tags(tags_field: str) -> list[str]:
    if not tags_field:
        return []
    # SE dump: "|appsec|attack-prevention|source-code|"; split on '|' and drop empties.
    return [t.lower() for t in tags_field.split("|") if t.strip()]


def _ensure_dump(cache_dir: Path) -> Optional[Path]:
    """Download + extract Posts.xml. Returns path or None on failure."""
    src = "stackexchange"
    archive = cache_path(cache_dir, src, DUMP_NAME)
    extracted = archive.parent / "Posts.xml"
    if extracted.exists():
        logger.info("stackexchange: Posts.xml already extracted (%d MB)",
                    extracted.stat().st_size // (1 << 20))
        return extracted
    try:
        download(DUMP_URL, archive, session=_session())
    except Exception as e:
        logger.warning("stackexchange: download failed: %s", e)
        return None
    logger.info("stackexchange: extracting Posts.xml from %s ...", archive.name)
    try:
        import py7zr
        with py7zr.SevenZipFile(archive, mode="r") as zf:
            names = zf.getnames()
            target = next((n for n in names if n.endswith("Posts.xml")), None)
            if not target:
                logger.warning("stackexchange: Posts.xml not in archive contents")
                return None
            zf.extract(path=archive.parent, targets=[target])
        # py7zr extracts preserving paths
        candidate = archive.parent / target
        if candidate.exists() and candidate != extracted:
            candidate.rename(extracted)
        if not extracted.exists():
            logger.warning("stackexchange: Posts.xml not present post-extract")
            return None
    except Exception as e:
        logger.warning("stackexchange: 7z extract failed: %s", e)
        return None
    return extracted


def fetch_and_yield_records(cache_dir: Path, max_records: int | None = None,
                            **_kwargs) -> Iterator[dict]:
    src = "stackexchange_security"
    posts_xml = _ensure_dump(cache_dir)
    if posts_xml is None or not posts_xml.exists():
        logger.warning("stackexchange: skipping (no Posts.xml)")
        return

    questions: dict[int, dict] = {}     # Id → {title, body, tags, accepted_id, date, score}
    n = 0
    logger.info("stackexchange: streaming Posts.xml ...")
    for evt, elem in iterparse(str(posts_xml), events=("end",)):
        if elem.tag != "row":
            continue
        a = elem.attrib
        ptype = a.get("PostTypeId")
        try:
            pid = int(a.get("Id", "0"))
        except ValueError:
            elem.clear()
            continue

        if ptype == "1":  # question
            tags = _parse_tags(a.get("Tags", ""))
            if not (set(tags) & TAG_WHITELIST):
                elem.clear()
                continue
            try:
                accepted = int(a.get("AcceptedAnswerId", "0") or 0)
            except ValueError:
                accepted = 0
            if not accepted:
                elem.clear()
                continue   # require an accepted answer
            questions[pid] = {
                "title": (a.get("Title") or "").strip(),
                "body":  _strip_html(a.get("Body") or ""),
                "tags":  tags,
                "accepted": accepted,
                "date": a.get("CreationDate", ""),
                "score": int(a.get("Score", "0") or 0),
            }
        elif ptype == "2":  # answer
            try:
                parent = int(a.get("ParentId", "0") or 0)
            except ValueError:
                parent = 0
            q = questions.get(parent)
            if q is None or q["accepted"] != pid:
                elem.clear()
                continue
            ans_body = _strip_html(a.get("Body") or "")
            parts = [
                f"Question: {q['title']}",
                f"Body: {q['body']}",
                f"Tags: {', '.join(q['tags'])}",
                f"Accepted Answer: {ans_body}",
            ]
            raw_text = " ".join(p for p in parts if p)
            rec = normalize_record(
                raw_text, source_forum=src,
                timestamp=q["date"] or None,
                url=f"https://security.stackexchange.com/q/{parent}",
                file_type="xml",
                file_info=f"security.stackexchange.com Posts.xml q={parent} a={pid}",
            )
            del questions[parent]
            elem.clear()
            if rec is None:
                continue
            yield rec
            n += 1
            if max_records and n >= max_records:
                logger.info("stackexchange: yielded %d (cap)", n)
                return
        else:
            elem.clear()

    logger.info("stackexchange: yielded %d records (questions in buffer: %d)",
                n, len(questions))
