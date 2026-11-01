"""DNRTI (Dataset for Named-Entity Recognition in Threat Intelligence).

DNRTI ships as a single `DNRTI.rar` archive in the master branch. We
download it, extract via `unrar` (apt: `unrar`), and parse the resulting
CoNLL-style train/valid/test text files. Same join logic as APTNER.

GitHub: https://github.com/SCreaMxp/DNRTI-A-Large-scale-Dataset-for-Named-Entity-Recognition-in-Threat-Intelligence
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Iterator, List

from .common import (
    cache_path, download, join_conll_tokens, normalize_record, _session,
)
from .aptner import _read_conll  # exact same CoNLL reader

logger = logging.getLogger("ingest.dnrti")

RAR_URL = (
    "https://raw.githubusercontent.com/SCreaMxp/DNRTI-A-Large-scale-Dataset-"
    "for-Named-Entity-Recognition-in-Threat-Intelligence/master/DNRTI.rar"
)

SENT_PER_RECORD = 8


def _ensure_extracted(cache_dir: Path) -> List[Path]:
    """Download DNRTI.rar and extract. Returns list of CoNLL .txt paths."""
    src = "dnrti"
    rar = cache_path(cache_dir, src, "DNRTI.rar")
    extracted_dir = rar.parent / "DNRTI"
    if extracted_dir.exists() and any(extracted_dir.rglob("*.txt")):
        return sorted(extracted_dir.rglob("*.txt"))

    try:
        download(RAR_URL, rar, session=_session())
    except Exception as e:
        logger.warning("dnrti: download failed: %s", e)
        return []

    if not shutil.which("unrar"):
        logger.warning("dnrti: unrar not installed; cannot extract %s", rar)
        return []
    extracted_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["unrar", "x", "-o+", str(rar), str(extracted_dir) + "/"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        logger.warning("dnrti: unrar failed: %s", e.stderr.decode()[:200])
        return []

    txts = sorted(extracted_dir.rglob("*.txt"))
    logger.info("dnrti: extracted %d .txt files", len(txts))
    return txts

SENT_PER_RECORD = 8


def fetch_and_yield_records(cache_dir: Path, max_records: int | None = None,
                            **_kwargs) -> Iterator[dict]:
    src = "dnrti"
    paths = _ensure_extracted(cache_dir)
    if not paths:
        logger.warning("dnrti: no CoNLL files available — adapter yielded nothing")
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
                        url="https://github.com/SCreaMxp/DNRTI-A-Large-scale-Dataset-for-Named-Entity-Recognition-in-Threat-Intelligence",
                        file_type="conll",
                        file_info=f"DNRTI {p.name}",
                    )
                    if rec is not None:
                        yield rec
                        n += 1
                        if max_records and n >= max_records:
                            logger.info("dnrti: yielded %d (cap)", n)
                            return
                buf_text = []
                buf_has_entity = False
    if buf_text and buf_has_entity:
        rec = normalize_record(
            " ".join(buf_text), source_forum=src,
            url="https://github.com/SCreaMxp/DNRTI-A-Large-scale-Dataset-for-Named-Entity-Recognition-in-Threat-Intelligence",
            file_type="conll",
            file_info="DNRTI tail",
        )
        if rec is not None:
            yield rec
            n += 1
    logger.info("dnrti: yielded %d records", n)
