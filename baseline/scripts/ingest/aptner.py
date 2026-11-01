"""APTNER CoNLL-style NER corpus → ingest records.

Reconstructs running text from `<token> <BIO_tag>` lines, groups ~8 sentences
per record, and drops groups whose sentences carry zero entity tags.

GitHub: https://github.com/wangxuren/APTNER
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, List

from .common import (
    cache_path, download, join_conll_tokens, normalize_record, _session,
)

logger = logging.getLogger("ingest.aptner")

RAW_BASE = "https://raw.githubusercontent.com/wangxuren/APTNER/main/"
FILES = ("APTNERtrain.txt", "APTNERdev.txt", "APTNERtest.txt")

SENT_PER_RECORD = 8


def _read_conll(path: Path) -> Iterator[tuple[List[str], List[str]]]:
    """Yield (tokens, tags) per sentence (blank-line separated)."""
    toks: List[str] = []
    tags: List[str] = []
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip():
                if toks:
                    yield toks, tags
                    toks, tags = [], []
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            toks.append(parts[0])
            tags.append(parts[-1])
        if toks:
            yield toks, tags


def fetch_and_yield_records(cache_dir: Path, max_records: int | None = None,
                            **_kwargs) -> Iterator[dict]:
    src = "aptner"
    session = _session()
    paths: List[Path] = []
    for fname in FILES:
        p = cache_path(cache_dir, src, fname)
        try:
            download(RAW_BASE + fname, p, session=session)
            paths.append(p)
        except Exception as e:
            logger.warning("aptner: failed to download %s (%s); skipping", fname, e)
    if not paths:
        return

    n = 0
    buf_text: List[str] = []
    buf_has_entity = False

    def flush():
        nonlocal n, buf_text, buf_has_entity
        if buf_text and buf_has_entity:
            raw_text = " ".join(buf_text)
            rec = normalize_record(
                raw_text, source_forum=src,
                url="https://github.com/wangxuren/APTNER",
                file_type="conll",
                file_info="APTNER (CSCWD 2022)",
            )
            if rec is not None:
                n_out_local[0] = n_out_local[0] + 1
                return rec
        buf_text = []
        buf_has_entity = False
        return None

    # Use a small mutable holder so the nested flush() can update the count.
    # (Avoids 'nonlocal' across function boundary for the orchestrator's tally.)
    n_out_local = [0]

    for p in paths:
        for tokens, tags in _read_conll(p):
            if not tokens:
                continue
            sentence = join_conll_tokens(tokens)
            buf_text.append(sentence)
            if any(t != "O" for t in tags):
                buf_has_entity = True
            if len(buf_text) >= SENT_PER_RECORD:
                if buf_has_entity:
                    raw_text = " ".join(buf_text)
                    rec = normalize_record(
                        raw_text, source_forum=src,
                        url="https://github.com/wangxuren/APTNER",
                        file_type="conll",
                        file_info=f"APTNER {p.name}",
                    )
                    if rec is not None:
                        yield rec
                        n += 1
                        if max_records and n >= max_records:
                            logger.info("aptner: yielded %d records (cap)", n)
                            return
                buf_text = []
                buf_has_entity = False
    # Flush trailing partial group
    if buf_text and buf_has_entity:
        raw_text = " ".join(buf_text)
        rec = normalize_record(
            raw_text, source_forum=src,
            url="https://github.com/wangxuren/APTNER",
            file_type="conll",
            file_info="APTNER tail",
        )
        if rec is not None:
            yield rec
            n += 1
    logger.info("aptner: yielded %d records", n)
