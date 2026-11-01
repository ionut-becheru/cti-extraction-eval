#!/usr/bin/env python3
"""
Large-scale evaluation of the relevance filter.

Replaces the 15-record toy validation set with a 6,000-record evaluation:

  Positives (label = cyber)
    Random sample from the hybrid public CTI corpus
    (MITRE ATT&CK, NVD HIGH+CRITICAL CVEs, CISA KEV, APTNER, DNRTI, CyNER,
    Stack Exchange Information Security). Every record was hand-curated
    by upstream sources to be cybersecurity-related → high-confidence
    positive ground truth.

  Negatives (label = non-cyber)
    Random English Wikipedia article extracts pulled via the REST API.
    Independent of any signal our filter has seen, broadly non-cyber on
    average. Articles whose summary unambiguously hits cybersec vocabulary
    are kept (they are real-world ambiguity); the goal is realistic non-
    cyber text, not adversarially-curated examples.

Outputs:
  results/relevance_eval.json   — full numbers (per-class confusion +
                                  error samples)
  results/relevance_eval.tex    — paper-ready LaTeX table fragment

Usage:
  python scripts/evaluate_relevance_filter.py --n 3000
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import random
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ijson
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("eval_filter")

CORPUS = PROJECT_ROOT / "data" / "input" / "public_cyber_corpus.json"
NEG_CACHE = PROJECT_ROOT / "data" / "input" / ".cache" / "wikipedia_negatives.jsonl"
OUT_JSON = PROJECT_ROOT / "results" / "relevance_eval.json"
OUT_TEX  = PROJECT_ROOT / "results" / "relevance_eval.tex"

WIKI_QUERY_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "DarkWebProject/0.9 evaluation (research bot)"}


# ----- Negative pool: random Wikipedia article extracts ----------------------
#
# Uses the MediaWiki query API in batch mode (generator=random + prop=extracts)
# instead of the per-page REST endpoint. One HTTP call returns up to 20
# article extracts → 50× fewer requests, well under rate limits.

def _fetch_wiki_batch(session: requests.Session, n: int = 20) -> List[Dict]:
    try:
        params = {
            "format": "json",
            "action": "query",
            "generator": "random",
            "grnnamespace": 0,         # main articles only
            "grnlimit": min(n, 20),
            "prop": "extracts|info",
            "exintro": 1,              # lead section only
            "explaintext": 1,          # plain text, no markup
            "inprop": "url",
        }
        r = session.get(WIKI_QUERY_API, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            log.debug("wiki batch HTTP %d", r.status_code)
            return []
        data = r.json()
        pages = (data.get("query") or {}).get("pages") or {}
        out = []
        for _, p in pages.items():
            extract = (p.get("extract") or "").strip()
            if len(extract) < 200:
                continue
            out.append({"title": p.get("title", ""), "extract": extract,
                        "url": p.get("fullurl", "")})
        return out
    except Exception as e:
        log.debug("wiki batch failed: %s", e)
        return []


def gather_wiki_negatives(n: int) -> List[Dict]:
    cached: List[Dict] = []
    if NEG_CACHE.exists():
        with open(NEG_CACHE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    cached.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        log.info("loaded %d Wikipedia negatives from cache", len(cached))
    if len(cached) >= n:
        return cached[:n]

    log.info("fetching %d more Wikipedia article extracts (batch=20)...",
             n - len(cached))
    NEG_CACHE.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    session = requests.Session()
    consecutive_empty = 0
    throttle = 2.5                       # base inter-batch sleep
    with open(NEG_CACHE, "a", encoding="utf-8") as fout:
        while len(cached) < n:
            batch = _fetch_wiki_batch(session, n=20)
            if not batch:
                consecutive_empty += 1
                # Exponential backoff up to 60s; never give up
                backoff = min(60, 5 * (2 ** (consecutive_empty - 1)))
                log.warning("empty batch %d — sleeping %ds", consecutive_empty, backoff)
                time.sleep(backoff)
                continue
            consecutive_empty = 0
            for d in batch:
                fout.write(json.dumps(d, ensure_ascii=False) + "\n")
                cached.append(d)
                if len(cached) >= n:
                    break
            fout.flush()
            if len(cached) % 200 < 20:
                log.info("  %d/%d cached (%.1fs elapsed)", len(cached), n,
                         time.time() - t0)
            time.sleep(throttle)
    log.info("Wikipedia negatives ready: %d total in %.1fs",
             len(cached), time.time() - t0)
    return cached[:n]


# ----- Positive pool: random sample from public_cyber_corpus.json -----------

def gather_corpus_positives(n: int, seed: int = 42) -> List[Dict]:
    """Reservoir-sample `n` records from the public CTI corpus."""
    if not CORPUS.exists():
        sys.exit(f"missing {CORPUS}; build with `python -m scripts.ingest --all`")
    rng = random.Random(seed)
    out: List[Dict] = []
    i = 0
    with open(CORPUS, "rb") as f:
        for rec in ijson.items(f, "item"):
            i += 1
            text = rec.get("raw_text") or ""
            if not text:
                continue
            if len(out) < n:
                out.append({"text": text,
                            "source_forum": rec.get("source_forum", "?")})
            else:
                j = rng.randrange(i)
                if j < n:
                    out[j] = {"text": text,
                              "source_forum": rec.get("source_forum", "?")}
    log.info("corpus positives: %d (sampled from %d total)", len(out), i)
    return out


# ----- Run filter + score ---------------------------------------------------

def evaluate(n: int) -> Dict:
    from src.relevance_filter import RelevanceFilter

    log.info("instantiating relevance filter (default keyword-only mode)...")
    rf = RelevanceFilter(
        min_length=50, max_length=50000,
        enable_spam_filter=True,
        enable_cybersecurity_filter=True,
        min_cybersecurity_keywords=1,
        zero_shot_enabled=False,
    )

    pos = gather_corpus_positives(n)
    neg = gather_wiki_negatives(n)
    log.info("evaluation pool: %d positives + %d negatives", len(pos), len(neg))

    tp = fp = tn = fn = 0
    pos_pred_reasons = Counter()
    neg_pred_reasons = Counter()
    fp_examples: List[Dict] = []
    fn_examples: List[Dict] = []
    per_source: Dict[str, Dict[str, int]] = {}

    log.info("scoring positives...")
    t0 = time.time()
    for i, rec in enumerate(pos):
        is_rel, reason = rf.is_relevant(rec["text"])
        src = rec["source_forum"]
        per_source.setdefault(src, {"tp": 0, "fn": 0})
        if is_rel:
            tp += 1
            per_source[src]["tp"] += 1
            pos_pred_reasons["passed"] += 1
        else:
            fn += 1
            per_source[src]["fn"] += 1
            pos_pred_reasons[str(reason)[:60]] += 1
            if len(fn_examples) < 20:
                fn_examples.append({
                    "source_forum": src,
                    "reason": reason,
                    "text_head": rec["text"][:240],
                })

    log.info("scoring negatives...")
    for i, rec in enumerate(neg):
        is_rel, reason = rf.is_relevant(rec["extract"])
        if is_rel:
            fp += 1
            neg_pred_reasons["wrongly_kept_as_cyber"] += 1
            if len(fp_examples) < 20:
                fp_examples.append({
                    "title": rec["title"],
                    "url": rec.get("url", ""),
                    "text_head": rec["extract"][:240],
                })
        else:
            tn += 1
            neg_pred_reasons[str(reason)[:60]] += 1

    elapsed = time.time() - t0
    log.info("scored in %.1fs", elapsed)

    total = tp + fp + tn + fn
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    accuracy = (tp + tn) / max(total, 1)
    specificity = tn / max(tn + fp, 1)

    out = {
        "n_positives": len(pos),
        "n_negatives": len(neg),
        "confusion_matrix": {
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        },
        "metrics": {
            "precision":   round(precision, 4),
            "recall":      round(recall, 4),
            "f1":          round(f1, 4),
            "accuracy":    round(accuracy, 4),
            "specificity": round(specificity, 4),
        },
        "per_source": {src: {
            "tp": d["tp"], "fn": d["fn"],
            "recall": round(d["tp"] / max(d["tp"] + d["fn"], 1), 4),
        } for src, d in sorted(per_source.items(), key=lambda kv: -sum(kv[1].values()))},
        "pos_reasons_when_rejected": dict(pos_pred_reasons.most_common(20)),
        "neg_reasons_when_rejected": dict(neg_pred_reasons.most_common(20)),
        "fp_examples": fp_examples,
        "fn_examples": fn_examples,
        "scored_seconds": round(elapsed, 2),
        "positive_source": "public_cyber_corpus.json (hybrid CTI: MITRE / NVD / CISA / APTNER / DNRTI / CyNER / Stack Exchange Security)",
        "negative_source": "English Wikipedia random article summaries (REST API)",
    }
    return out


# ----- LaTeX renderer -------------------------------------------------------

def render_latex(res: Dict, out_path: Path) -> None:
    cm = res["confusion_matrix"]; m = res["metrics"]
    rows = "\n".join(
        rf"{src.replace('_', ' ')} & {d['tp']:,} & {d['fn']:,} & {d['recall']:.3f} \\ \hline"
        for src, d in res["per_source"].items()
    )
    tex = rf"""% relevance_eval.tex — generated by scripts/evaluate_relevance_filter.py

\begin{{table}}[H]
\centering
\caption{{Relevance-filter evaluation on a {res['n_positives']+res['n_negatives']:,}-record balanced
set ({res['n_positives']:,} hand-curated cybersecurity positives from the hybrid CTI corpus
of MITRE ATT\&CK, NVD HIGH+CRITICAL CVEs, CISA KEV, APTNER, DNRTI, CyNER, and Stack
Exchange Information Security; {res['n_negatives']:,} negatives sampled uniformly from random
English Wikipedia article summaries via the public REST API).}}
\label{{tab:filter-results}}
\begin{{tabular}}{{|l|r|}}
\hline
\textbf{{Metric}} & \textbf{{Value}} \\ \hline
Precision & {m['precision']:.3f} \\ \hline
Recall & {m['recall']:.3f} \\ \hline
F1 score & {m['f1']:.3f} \\ \hline
Accuracy & {m['accuracy']:.3f} \\ \hline
Specificity & {m['specificity']:.3f} \\ \hline
True positives & {cm['tp']:,} \\ \hline
False negatives & {cm['fn']:,} \\ \hline
True negatives & {cm['tn']:,} \\ \hline
False positives & {cm['fp']:,} \\ \hline
\end{{tabular}}
\end{{table}}

% Per-source recall breakdown
\begin{{table}}[H]
\centering
\caption{{Per-source recall on the positive split. Each source contributes hand-curated
cybersecurity-relevant records; the recall column measures how often the keyword-based
relevance filter correctly retains them.}}
\label{{tab:filter-recall-per-source}}
\begin{{tabular}}{{|l|r|r|r|}}
\hline
\textbf{{Source}} & \textbf{{TP}} & \textbf{{FN}} & \textbf{{Recall}} \\ \hline
{rows}
\hline
\end{{tabular}}
\end{{table}}
"""
    out_path.write_text(tex)
    log.info("wrote %s", out_path)


# ----- Main -----------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=3000,
                   help="positives = negatives = N (default 3000)")
    args = p.parse_args()

    res = evaluate(args.n)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, indent=2, ensure_ascii=False))
    log.info("wrote %s", OUT_JSON)

    render_latex(res, OUT_TEX)

    # Headline print
    m = res["metrics"]; cm = res["confusion_matrix"]
    print(f"\n=== Relevance filter on N={res['n_positives']+res['n_negatives']:,} ===")
    print(f"  Precision: {m['precision']:.4f}")
    print(f"  Recall:    {m['recall']:.4f}")
    print(f"  F1:        {m['f1']:.4f}")
    print(f"  Accuracy:  {m['accuracy']:.4f}")
    print(f"  TP={cm['tp']:,} FP={cm['fp']:,} TN={cm['tn']:,} FN={cm['fn']:,}")


if __name__ == "__main__":
    main()
