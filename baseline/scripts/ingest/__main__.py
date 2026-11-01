"""Hybrid public CTI corpus orchestrator.

Pulls from MITRE ATT&CK, NVD, CISA KEV, APTNER, DNRTI, CyNER, and Stack
Exchange Information Security. Dedupes by SHA1 of normalized text. Writes
a single JSON array file that the DarkWeb pipeline ingests via ijson.

Stack Exchange dump is CC BY-SA 4.0 — see scripts/ingest/stackexchange.py.

Usage (typical):
    python -m scripts.ingest --all \
        --out data/input/public_cyber_corpus.json \
        --max-per-source 4000

To run a single source for debugging:
    python -m scripts.ingest --mitre --shards --out data/input/public_cyber_corpus.json
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import SOURCES
from .common import Dedup, JsonArrayWriter

DEFAULT_OUT = Path("data/input/public_cyber_corpus.json")
DEFAULT_CACHE = Path("data/input/.cache")


def _parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--all", action="store_true", help="enable every source")
    for src in SOURCES:
        p.add_argument(f"--{src}", action="store_true",
                       help=f"enable {src} source")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT,
                   help=f"output JSON array path (default: {DEFAULT_OUT})")
    p.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE,
                   help=f"cache directory (default: {DEFAULT_CACHE})")
    p.add_argument("--max-per-source", type=int, default=None,
                   help="cap each source independently")
    p.add_argument("--max-total", type=int, default=None,
                   help="hard cap on total records")
    p.add_argument("--shards", action="store_true",
                   help="also write per-source shard files alongside the merged corpus")
    p.add_argument("--nvd-start", default=None,
                   help="NVD start date (YYYY-MM-DD); default = trailing 365d")
    p.add_argument("--nvd-end",   default=None,
                   help="NVD end date (YYYY-MM-DD); default = now")
    p.add_argument("--nvd-api-key-env", default="NVD_API_KEY",
                   help="env var holding NVD API key (default NVD_API_KEY)")
    p.add_argument("--dry-run", action="store_true",
                   help="iterate sources but do not write the output file")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    enabled = set()
    if args.all:
        enabled = set(SOURCES.keys())
    for src in SOURCES:
        if getattr(args, src.replace("-", "_")):
            enabled.add(src)
    if not enabled:
        p.error("Pick at least one source (or --all).")
    args.enabled_sources = sorted(enabled)
    return args


def main(argv=None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("ingest")
    log.info("Enabled sources: %s", ", ".join(args.enabled_sources))
    log.info("Output: %s   Cache: %s", args.out, args.cache_dir)

    dedup = Dedup()
    counts: dict[str, int] = {}
    shard_writers: dict[str, JsonArrayWriter] = {}

    if args.dry_run:
        merged = None
    else:
        merged = JsonArrayWriter(args.out).__enter__()

    total = 0
    try:
        for src in args.enabled_sources:
            adapter = SOURCES[src]
            log.info("--- %s ---", src)
            kwargs = {}
            if src == "nvd":
                kwargs.update(
                    nvd_start=args.nvd_start,
                    nvd_end=args.nvd_end,
                    api_key_env=args.nvd_api_key_env,
                )
            src_count = 0
            shard_w = None
            if args.shards and not args.dry_run:
                shard_path = args.out.with_name(args.out.stem + f"_{src}.json")
                shard_w = JsonArrayWriter(shard_path).__enter__()
                shard_writers[src] = shard_w

            try:
                for rec in adapter.fetch_and_yield_records(
                    cache_dir=args.cache_dir,
                    max_records=args.max_per_source,
                    **kwargs,
                ):
                    if not dedup.is_new(rec["raw_text"]):
                        continue
                    if merged is not None:
                        merged.write(rec)
                    if shard_w is not None:
                        shard_w.write(rec)
                    src_count += 1
                    total += 1
                    if args.max_total and total >= args.max_total:
                        log.warning("hit --max-total=%d, stopping", args.max_total)
                        break
            except Exception as e:
                log.exception("source %s crashed: %s", src, e)

            if shard_w is not None:
                shard_w.__exit__(None, None, None)
            counts[src] = src_count
            log.info("source %s: %d records (running total %d, dedup-dropped %d)",
                     src, src_count, total, dedup.dropped)
            if args.max_total and total >= args.max_total:
                break

        if merged is not None:
            merged.__exit__(None, None, None)
    except BaseException:
        if merged is not None:
            merged.__exit__(*sys.exc_info())
        for w in shard_writers.values():
            try:
                w.__exit__(*sys.exc_info())
            except Exception:
                pass
        raise

    log.info("=== summary ===")
    for src in args.enabled_sources:
        log.info("  %-22s %6d", src, counts.get(src, 0))
    log.info("  TOTAL                  %6d (deduped: %d dropped)", total, dedup.dropped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
