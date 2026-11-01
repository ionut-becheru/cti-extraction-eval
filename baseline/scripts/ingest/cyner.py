"""CyNER (Cybersecurity NER) dataset → ingest records.

GitHub: https://github.com/aiforsec/CyNER

The repo ships annotated CoNLL files; we follow the same join logic as
APTNER. Each repo folder is downloaded best-effort; missing files are
skipped with a debug log.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, List

from .common import (
    cache_path, download, join_conll_tokens, normalize_record, _session,
)
from .aptner import _read_conll

logger = logging.getLogger("ingest.cyner")

CANDIDATES = [
    ("dataset/mitre/train.txt",
     "https://raw.githubusercontent.com/aiforsec/CyNER/main/dataset/mitre/train.txt"),
    ("dataset/mitre/valid.txt",
     "https://raw.githubusercontent.com/aiforsec/CyNER/main/dataset/mitre/valid.txt"),
    ("dataset/mitre/test.txt",
     "https://raw.githubusercontent.com/aiforsec/CyNER/main/dataset/mitre/test.txt"),
]

SENT_PER_RECORD = 8


def fetch_and_yield_records(cache_dir: Path, max_records: int | None = None,
                            **_kwargs) -> Iterator[dict]:
    src = "cyner"
    session = _session()
    paths: List[Path] = []
    for relname, url in CANDIDATES:
        p = cache_path(cache_dir, src, relname)
        try:
            download(url, p, session=session)
            paths.append(p)
        except Exception as e:
            logger.debug("cyner: %s → %s", url, e)
    if not paths:
        logger.warning("cyner: no files downloaded — adapter yielded nothing")
        return

    n = 0
    buf_text: List[str] = []
    buf_has_entity = False
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
                    rec = normalize_record(
                        " ".join(buf_text), source_forum=src,
                        url="https://github.com/aiforsec/CyNER",
                        file_type="conll",
                        file_info=f"CyNER {p.name}",
                    )
                    if rec is not None:
                        yield rec
                        n += 1
                        if max_records and n >= max_records:
                            logger.info("cyner: yielded %d (cap)", n)
                            return
                buf_text = []
                buf_has_entity = False
    if buf_text and buf_has_entity:
        rec = normalize_record(
            " ".join(buf_text), source_forum=src,
            url="https://github.com/aiforsec/CyNER",
            file_type="conll",
            file_info="CyNER tail",
        )
        if rec is not None:
            yield rec
            n += 1
    logger.info("cyner: yielded %d records", n)
