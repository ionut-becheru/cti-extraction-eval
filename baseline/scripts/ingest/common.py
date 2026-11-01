"""Shared helpers for the ingest adapters."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import time
from pathlib import Path
from typing import Iterator, Optional

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

logger = logging.getLogger("ingest")

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE_RE = re.compile(r"\s+")
_MITRE_CITATION_RE = re.compile(r"\(Citation:\s*[^)]+\)")
_MITRE_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(https?://[^)]+\)")

# Cybersec context terms — sanity gate that each adapter's records contain
# at least one real-world cybersec word. Mirrors the spirit of
# CybersecNER._CYBER_CONTEXT_TERMS but kept independent so the ingest can
# run without importing the full src/ tree.
_CYBER_TERMS = (
    "malware", "ransomware", "trojan", "exploit", "vulnerability", "vuln",
    "cve", "cwe", "rce", "lpe", "xss", "sqli", "csrf", "rootkit", "backdoor",
    "phishing", "credential", "leak", "breach", "c2", "command and control",
    "apt", "threat actor", "ttp", "mitre", "att&ck", "encrypt", "decrypt",
    "payload", "shellcode", "ddos", "pentest", "red team", "blue team",
    "forensic", "ioc", "indicator", "darkweb", "dark web", "onion", "tor",
    "lockbit", "conti", "ryuk", "wannacry", "emotet", "trickbot",
    "bypass", "elevation of privilege", "remote code execution",
    "buffer overflow", "ssrf", "xxe", "rdp", "smb", "tls", "ssh",
    "active directory", "kerberos", "ntlm", "password", "hash", "decrypt",
)
_CYBER_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in _CYBER_TERMS) + r")\b", re.I)


# ---------------------------------------------------------------- networking

def _session(retries: int = 5, backoff: float = 2.0) -> requests.Session:
    """A requests.Session with sane retry behavior for flaky public APIs."""
    s = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "DarkWebProject-ingest/0.9 (+research)"})
    return s


def download(url: str, dest: Path, session: Optional[requests.Session] = None,
             stream: bool = True, force: bool = False) -> Path:
    """Download `url` to `dest` atomically (.partial → rename) unless cached."""
    dest = Path(dest)
    if dest.exists() and not force:
        logger.debug("cache hit: %s", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    s = session or _session()
    logger.info("download %s → %s", url, dest)
    with s.get(url, stream=stream, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
    tmp.replace(dest)
    return dest


def cache_path(cache_dir: Path, source: str, *parts: str) -> Path:
    return Path(cache_dir) / source / Path(*parts)


# ---------------------------------------------------------------- normalize

def _clean_mitre_markdown(text: str) -> str:
    """Strip `(Citation: Foo 2020)` and `[Foo](https://...)` from MITRE prose."""
    text = _MITRE_CITATION_RE.sub("", text)
    text = _MITRE_MD_LINK_RE.sub(r"\1", text)
    return text


def normalize_text(text: str) -> str:
    """Whitespace + control-char normalization (shared across all sources)."""
    if not text:
        return ""
    text = _CONTROL_CHARS_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _truncate_at_sentence(text: str, limit: int = 5000) -> str:
    """If text > limit, truncate at the last sentence boundary <= limit; else hard cap."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    # Find the last sentence-ending punctuation in the head
    cut = max(head.rfind(". "), head.rfind("! "), head.rfind("? "))
    if cut < int(limit * 0.6):
        cut = limit  # no good break — hard cut
    return text[:cut].rstrip() + "..."


def has_cyber_context(text: str) -> bool:
    """Sanity gate: does the record contain at least one cybersec context word?"""
    return bool(_CYBER_RE.search(text or ""))


def normalize_record(raw_text: str, source_forum: str, **fields) -> Optional[dict]:
    """Apply length + whitespace + cyber-context gates; return record or None."""
    text = normalize_text(raw_text)
    if len(text) < 200:
        return None
    text = _truncate_at_sentence(text, limit=5000)
    if not has_cyber_context(text):
        logger.debug("dropped (no cyber context): %s", source_forum)
        return None
    rec = {
        "raw_text":     text,
        "source_forum": source_forum,
        "source":       "public_cyber_corpus",
    }
    # Add optional pipeline-aware fields
    for k in ("timestamp", "url", "file_name", "file_type", "file_info"):
        v = fields.get(k)
        if v:
            rec[k] = v
    return rec


# ---------------------------------------------------------------- CoNLL rejoin

# Tokens that hug the PREVIOUS token (no leading space): . , ; : ! ? ) ] }
_HUG_LEFT = {".", ",", ";", ":", "!", "?", ")", "]", "}", "'s", "n't", "'re",
             "'ve", "'ll", "'d", "'m"}
# Tokens that hug the NEXT token (no trailing space): ( [ {
_HUG_RIGHT = {"(", "[", "{"}


def join_conll_tokens(tokens: list[str]) -> str:
    """Rebuild a readable sentence from CoNLL-style space-separated tokens.

    Punctuation hugs the appropriate side; quotes get best-effort even/odd
    pairing (works for most APTNER/DNRTI text).
    """
    out: list[str] = []
    quote_open = True
    for tok in tokens:
        if not tok:
            continue
        if tok == '"':
            if out and quote_open:
                out.append('"')          # closing — hug left
                quote_open = False
                continue
            else:
                if out and out[-1] != " ":
                    out.append(" ")
                out.append('"')          # opening
                quote_open = True
                continue
        if tok in _HUG_LEFT:
            out.append(tok)
            continue
        if out and out[-1] in _HUG_RIGHT:
            out.append(tok)
            continue
        if out:
            out.append(" ")
        out.append(tok)
    return "".join(out).strip()


# ---------------------------------------------------------------- I/O writer

class JsonArrayWriter:
    """Stream-write a JSON array atomically (writes to .tmp + os.replace())."""

    def __init__(self, out_path: Path):
        self.path = Path(out_path)
        self.tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = None
        self._first = True
        self.count = 0

    def __enter__(self):
        self._fh = open(self.tmp, "w", encoding="utf-8")
        self._fh.write("[\n")
        return self

    def write(self, record: dict) -> None:
        if not self._first:
            self._fh.write(",\n")
        json.dump(record, self._fh, ensure_ascii=False)
        self._first = False
        self.count += 1

    def __exit__(self, exc_type, exc, tb):
        if self._fh is None:
            return
        self._fh.write("\n]\n")
        self._fh.close()
        if exc_type is None:
            self.tmp.replace(self.path)
            logger.info("wrote %d records → %s", self.count, self.path)
        else:
            logger.error("aborting; leaving partial at %s", self.tmp)


# ---------------------------------------------------------------- dedup

class Dedup:
    """Cheap in-memory dedup by SHA1 of normalized text."""

    def __init__(self):
        self._seen: set[str] = set()
        self.dropped = 0

    def is_new(self, text: str) -> bool:
        h = hashlib.sha1((text or "").lower().strip().encode("utf-8")).hexdigest()
        if h in self._seen:
            self.dropped += 1
            return False
        self._seen.add(h)
        return True


# ---------------------------------------------------------------- misc

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
