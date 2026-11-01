#!/usr/bin/env python3
"""
Compute paper-quality pipeline statistics across the full corpus.

Single streaming pass over the JSONL (Stage-by-stage funnel + skip reasons +
entity tallies + risk/topic distributions + correlation hits) plus indexed
queries against SQLite (entity/IOC/alert/forum) and FalkorDB (graph counts).

Outputs:
  results/pipeline_stats_full.json   (machine-readable, dashboard reads this)
  results/pipeline_stats_tables.tex  (LaTeX fragments, paper-ready)
  results/pipeline_stats.md          (Markdown summary)

Usage:
  python scripts/pipeline_stats.py \
      --input  data/output/translated_dataset.jsonl \
      --db     data/threat_intel.db
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_INPUT = PROJECT_ROOT / "data" / "output" / "translated_dataset.jsonl"
DEFAULT_DB = PROJECT_ROOT / "data" / "threat_intel.db"
DEFAULT_OUT_JSON = PROJECT_ROOT / "results" / "pipeline_stats_full.json"
DEFAULT_OUT_TEX = PROJECT_ROOT / "results" / "pipeline_stats_tables.tex"
DEFAULT_OUT_MD = PROJECT_ROOT / "results" / "pipeline_stats.md"

# ---------------------------------------------------------------------------
# Stage classification
# ---------------------------------------------------------------------------

# Each record is assigned to exactly one funnel bucket. Buckets are
# mutually exclusive and sum to total_records.
FUNNEL_ORDER = [
    ("cleaner_html_noise",      "Cleaner: HTML/JS/short rejected"),
    ("cleaner_too_short",       "Cleaner: text too short"),
    ("spam_rejected",           "Spam filter rejected"),
    ("not_cyber_english",       "English non-cyber (filtered)"),
    ("lid_unknown",             "Language ID: unknown / low conf"),
    ("pre_translation_filter",  "Pre-translation filter (non-EN non-cyber)"),
    ("english_kept",            "English cyber (skip translation, analyze)"),
    ("translated_then_filtered","Translated then dropped (post-filter)"),
    ("translated_kept",         "Translated cyber (analyzed)"),
]


def classify(rec: dict) -> str:
    """Map a JSONL record to one funnel bucket."""
    skipped = rec.get("translation_skipped", False)
    if skipped is False or skipped is None:
        # Translation actually happened.
        if rec.get("post_translation_filtered"):
            return "translated_then_filtered"
        return "translated_kept"
    # Translation was skipped — categorize by reason string.
    reason = str(skipped)
    if reason == "html_noise":
        return "cleaner_html_noise"
    if reason == "too_short":
        return "cleaner_too_short"
    if reason.startswith("spam_keyword") or reason.startswith("spam_pattern"):
        return "spam_rejected"
    if reason.startswith("not_cybersecurity"):
        return "not_cyber_english"
    if reason == "unknown":
        return "lid_unknown"
    if reason.startswith("pre_translation_filter"):
        return "pre_translation_filter"
    if reason == "english":
        return "english_kept"
    # Backwards compat: treat True (legacy bool) and unknown reasons as
    # "lid_unknown" so the buckets still sum.
    return "lid_unknown"


# ---------------------------------------------------------------------------
# Dictionary filter (mirrors dashboard `_is_cyber_relevant`)
# ---------------------------------------------------------------------------

def load_cyber_dicts():
    from src.cybersec_ner import CybersecNER  # noqa: WPS433
    ner = CybersecNER.__new__(CybersecNER)  # avoid full init
    # Pull whatever malware aliases are loaded; fall back to inline list.
    try:
        ner._load_malware_dict()  # type: ignore[attr-defined]
        malware = set(ner._malware_aliases.keys())  # type: ignore[attr-defined]
    except Exception:
        malware = {m.lower() for m in CybersecNER.KNOWN_MALWARE}
    return {
        "TOOL":         {t.lower() for t in CybersecNER.KNOWN_TOOLS},
        "THREAT_ACTOR": {t.lower() for t in CybersecNER.KNOWN_THREAT_ACTORS},
        "MALWARE":      malware,
    }


def is_cyber_relevant(label: str, value: str, dicts: dict) -> bool:
    if not value:
        return False
    if label not in ("TOOL", "THREAT_ACTOR", "MALWARE"):
        return True
    v = value.strip().lower()
    d = dicts.get(label, set())
    return any(term in v or v in term for term in d)


# ---------------------------------------------------------------------------
# SQLite + FalkorDB aggregates
# ---------------------------------------------------------------------------

def sqlite_stats(db_path: Path) -> dict:
    out = {
        "available": False,
        "records": 0,
        "entities": 0,
        "iocs": 0,
        "alerts": 0,
        "feedback": 0,
        "by_severity": {},
        "by_alert_type": {},
        "by_forum": {},
        "by_language": {},
    }
    if not db_path.exists():
        return out
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        for table, key in [("records", "records"), ("entities", "entities"),
                           ("iocs", "iocs"), ("alerts", "alerts"),
                           ("feedback", "feedback")]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                out[key] = int(cur.fetchone()[0])
            except sqlite3.OperationalError:
                pass
        out["available"] = True
        try:
            cur.execute("SELECT severity, COUNT(*) FROM alerts GROUP BY severity")
            out["by_severity"] = {r[0] or "UNKNOWN": int(r[1]) for r in cur.fetchall()}
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("SELECT alert_type, COUNT(*) FROM alerts "
                        "GROUP BY alert_type ORDER BY 2 DESC LIMIT 10")
            out["by_alert_type"] = {r[0] or "unknown": int(r[1]) for r in cur.fetchall()}
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("SELECT source_forum, COUNT(*) FROM records "
                        "WHERE source_forum IS NOT NULL "
                        "GROUP BY source_forum ORDER BY 2 DESC LIMIT 20")
            out["by_forum"] = {r[0]: int(r[1]) for r in cur.fetchall()}
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("SELECT detected_language, COUNT(*) FROM records "
                        "GROUP BY detected_language ORDER BY 2 DESC")
            out["by_language"] = {r[0] or "unknown": int(r[1]) for r in cur.fetchall()}
        except sqlite3.OperationalError:
            pass
        conn.close()
    except Exception as e:
        out["error"] = str(e)
    return out


def graph_stats() -> dict:
    out = {"available": False, "node_counts": {}, "edge_total": 0}
    try:
        import yaml  # type: ignore
        cfg_path = PROJECT_ROOT / "config" / "config.yaml"
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f) or {}
        gcfg = cfg.get("graph_db", {}) or {}
        if not gcfg.get("enabled"):
            return out
        from src.graph_db import FalkorGraph  # noqa: WPS433
        g = FalkorGraph(
            host=gcfg.get("host", "127.0.0.1"),
            port=gcfg.get("port", 6379),
            password=gcfg.get("password", ""),
            graph_name=gcfg.get("graph_name", "darkweb_threat_intel"),
        )
        if not g.enabled:
            return out
        out["node_counts"] = g.get_counts()
        try:
            res = g._graph.query("MATCH ()-[r]->() RETURN count(r)")
            row = (res.result_set or [[0]])[0]
            out["edge_total"] = int(row[0])
        except Exception:
            pass
        out["available"] = True
    except Exception as e:
        out["error"] = str(e)
    return out


# ---------------------------------------------------------------------------
# Streaming pass
# ---------------------------------------------------------------------------

def _record_passed_filters(rec: dict) -> bool:
    """A record 'passed' all upstream filters when it is one of:
       - English cyber kept (translation_skipped == 'english')
       - Non-English translated and not post-filtered.
    Anything in HTML-noise / spam / not-cyber / pre-translation-filter / unknown
    buckets did not pass — its NER output is noise and shouldn't shape paper
    metrics.
    """
    skipped = rec.get("translation_skipped", False)
    if skipped is False or skipped is None:
        # Translation actually happened — count only if it survived the
        # post-translation cyber filter.
        return not bool(rec.get("post_translation_filtered"))
    return str(skipped) == "english"


def streaming_pass(jsonl_path: Path, dicts: dict) -> dict:
    funnel = Counter()
    skip_reasons = Counter()                  # raw skip-reason strings
    filter_reasons = Counter()                # post-translation filter_reason
    langs = Counter()
    risk_levels = Counter()
    threat_topics = Counter()
    # entities_*: counts taken across ALL records (including noise/spam)
    # entities_passed_*: same but limited to records that survived all
    # upstream filters — this is the honest "paper" number.
    entities_raw = defaultdict(int)
    entities_passed = defaultdict(int)
    entities_filtered = defaultdict(int)      # passed-filter AND dictionary-cleared
    unique_raw = defaultdict(set)
    unique_passed = defaultdict(set)
    unique_filtered = defaultdict(set)
    iocs_total = defaultdict(int)
    correlation_actor = 0
    correlation_campaign = 0
    correlation_cve = 0
    actor_hits = Counter()
    campaign_hits = Counter()
    records_with_analysis = 0
    records_with_entities = 0
    total = 0

    t0 = time.time()
    with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            total += 1

            bucket = classify(rec)
            funnel[bucket] += 1

            skipped = rec.get("translation_skipped", False)
            if skipped:
                r = str(skipped)
                if r.startswith("spam_keyword"):
                    r = "spam_keyword:*"
                elif r.startswith("pre_translation_filter"):
                    r = "pre_translation_filter:*"
                skip_reasons[r] += 1

            if "filter_reason" in rec:
                fr = rec["filter_reason"]
                if fr.startswith("spam_keyword"):
                    fr = "spam_keyword:*"
                elif fr.startswith("not_cybersecurity"):
                    fr = "not_cybersecurity_related"
                filter_reasons[fr] += 1

            lang = rec.get("detected_language") or "unknown"
            langs[lang] += 1

            a = rec.get("analysis") or {}
            passed = _record_passed_filters(rec)
            if a:
                records_with_analysis += 1
                ents = a.get("entities") or []
                if ents:
                    records_with_entities += 1
                for e in ents:
                    label = e.get("label") or "UNKNOWN"
                    val = (e.get("text") or "").strip()
                    val_l = val.lower() if val else ""
                    entities_raw[label] += 1
                    if val_l:
                        unique_raw[label].add(val_l)
                    if passed:
                        entities_passed[label] += 1
                        if val_l:
                            unique_passed[label].add(val_l)
                        if is_cyber_relevant(label, val, dicts):
                            entities_filtered[label] += 1
                            if val_l:
                                unique_filtered[label].add(val_l)
                iocs = a.get("iocs") or {}
                for itype, vals in iocs.items():
                    if isinstance(vals, list):
                        iocs_total[itype] += len(vals)
                risk_levels[(a.get("risk_level") or "INFO").upper()] += 1
                threat_topics[a.get("threat_topic") or "unknown"] += 1

            c = rec.get("correlation") or {}
            if c:
                actors = c.get("matched_threat_actors") or []
                campaigns = c.get("matched_campaigns") or []
                cves = c.get("matched_cves") or []
                if actors:
                    correlation_actor += 1
                    for a_ in actors:
                        name = a_ if isinstance(a_, str) else (a_.get("actor") or a_.get("name") or "unknown")
                        actor_hits[name] += 1
                if campaigns:
                    correlation_campaign += 1
                    for cm in campaigns:
                        name = cm if isinstance(cm, str) else (cm.get("campaign") or cm.get("name") or "unknown")
                        campaign_hits[name] += 1
                if cves:
                    correlation_cve += 1

    elapsed = time.time() - t0
    return {
        "total_records": total,
        "elapsed_s": round(elapsed, 2),
        "rec_per_s": round(total / max(elapsed, 1e-9), 1),
        "funnel": dict(funnel),
        "skip_reasons": dict(skip_reasons),
        "filter_reasons": dict(filter_reasons),
        "languages": dict(langs),
        "risk_levels": dict(risk_levels),
        "threat_topics": dict(threat_topics),
        "entities_raw": dict(entities_raw),
        "entities_passed_filter": dict(entities_passed),
        "entities_filtered": dict(entities_filtered),
        "unique_raw": {k: len(v) for k, v in unique_raw.items()},
        "unique_passed_filter": {k: len(v) for k, v in unique_passed.items()},
        "unique_filtered": {k: len(v) for k, v in unique_filtered.items()},
        "iocs_total": dict(iocs_total),
        "records_with_analysis": records_with_analysis,
        "records_with_entities": records_with_entities,
        "correlation": {
            "records_with_actor": correlation_actor,
            "records_with_campaign": correlation_campaign,
            "records_with_cve": correlation_cve,
            "top_actors": dict(actor_hits.most_common(10)),
            "top_campaigns": dict(campaign_hits.most_common(10)),
        },
    }


# ---------------------------------------------------------------------------
# Funnel assertions
# ---------------------------------------------------------------------------

def assert_funnel_consistency(streamed: dict) -> list[str]:
    """Return a list of warnings; never raises so the script always emits."""
    warnings = []
    total = streamed["total_records"]
    bucket_sum = sum(streamed["funnel"].values())
    if bucket_sum != total:
        warnings.append(
            f"Funnel buckets sum to {bucket_sum} but total_records is {total} "
            f"(off by {total - bucket_sum}). A new skip reason may be unmapped."
        )
    return warnings


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def fmt_pct(n: int, total: int) -> str:
    return f"{(100.0 * n / total):.1f}" if total else "0.0"


def render_markdown(stats: dict) -> str:
    s = stats["streamed"]
    db = stats["sqlite"]
    g = stats["graph"]
    total = s["total_records"]

    out = []
    out.append("# Pipeline Statistics — Full Corpus")
    out.append("")
    out.append(f"- Input JSONL: `{stats['input']}`")
    out.append(f"- Total records: **{total:,}**")
    out.append(f"- One-pass duration: {s['elapsed_s']:.1f}s "
               f"({s['rec_per_s']:.0f} rec/s)")
    out.append("")
    if stats.get("warnings"):
        out.append("> **Warnings:**")
        for w in stats["warnings"]:
            out.append(f"> - {w}")
        out.append("")

    # Table A — Funnel
    out.append("## Table A — Stage Funnel")
    out.append("")
    out.append("| Stage | Bucket | Count | % of total |")
    out.append("|---|---|---:|---:|")
    for key, label in FUNNEL_ORDER:
        n = s["funnel"].get(key, 0)
        out.append(f"| {key} | {label} | {n:,} | {fmt_pct(n, total)} |")
    out.append(f"| — | **Total** | **{total:,}** | 100.0 |")
    out.append("")

    # Persistence row
    out.append("## Persistence")
    out.append("")
    out.append(f"- Records with `analysis` block in JSONL: "
               f"**{s['records_with_analysis']:,}** "
               f"({fmt_pct(s['records_with_analysis'], total)}%)")
    if db.get("available"):
        out.append(f"- SQLite: records={db['records']:,} · "
                   f"entities={db['entities']:,} · "
                   f"iocs={db['iocs']:,} · "
                   f"alerts={db['alerts']:,} · "
                   f"feedback={db['feedback']:,}")
    else:
        out.append("- SQLite: not available")
    if g.get("available"):
        out.append("- FalkorDB nodes: " + ", ".join(
            f"{k}={v:,}" for k, v in g["node_counts"].items()
        ))
        out.append(f"- FalkorDB edges: {g['edge_total']:,}")
    else:
        out.append("- FalkorDB: not available")
    out.append("")

    # Table B — Skip reasons (raw)
    out.append("## Table B — Translation Skip Reasons (raw)")
    out.append("")
    out.append("| Reason | Count | % of total |")
    out.append("|---|---:|---:|")
    for k, v in sorted(s["skip_reasons"].items(), key=lambda x: -x[1]):
        out.append(f"| `{k}` | {v:,} | {fmt_pct(v, total)} |")
    out.append("")

    # Table C — Languages
    out.append("## Table C — Detected Language Distribution")
    out.append("")
    out.append("| Language | Count | % of total |")
    out.append("|---|---:|---:|")
    top_langs = sorted(s["languages"].items(), key=lambda x: -x[1])[:15]
    seen = sum(v for _, v in top_langs)
    for k, v in top_langs:
        out.append(f"| {k} | {v:,} | {fmt_pct(v, total)} |")
    other = total - seen
    if other > 0:
        out.append(f"| (other) | {other:,} | {fmt_pct(other, total)} |")
    out.append("")

    # Table D — Translation evaluation
    translated_kept = s["funnel"].get("translated_kept", 0)
    translated_drop = s["funnel"].get("translated_then_filtered", 0)
    total_translated = translated_kept + translated_drop
    out.append("## Table D — Translation Evaluation")
    out.append("")
    out.append("| Metric | Value |")
    out.append("|---|---:|")
    out.append(f"| Records sent to translator | {total_translated:,} |")
    out.append(f"| Translated → kept (cyber) | {translated_kept:,} |")
    out.append(f"| Translated → dropped (post-filter) | {translated_drop:,} |")
    out.append(f"| Drop rate after translation | "
               f"{fmt_pct(translated_drop, total_translated)}% |")
    out.append("")

    # Table E — Entities (raw + passed-filter + dict-filtered)
    out.append("## Table E — Entity Extraction")
    out.append("")
    out.append("Three columns reflect three increasingly strict gates:")
    out.append("- **Raw**: every entity NER produced (includes noise from cleaner-rejected / spam / pre-filter records — current pipeline runs NER before checking filter status).")
    out.append("- **Passed-filter**: entities only from records that survived all upstream filters (English-cyber-kept + translated-cyber-kept). This is the honest paper number.")
    out.append("- **Dict-filtered**: passed-filter AND, for TOOL / THREAT_ACTOR / MALWARE, the value matches the cybersec dictionary. Other types pass through (regex-derived).")
    out.append("")
    out.append("| Type | Raw mentions | Passed-filter mentions | Dict-filtered mentions | Unique (raw) | Unique (passed) | Unique (dict) |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")
    types = sorted(set(list(s["entities_raw"].keys())
                       + list(s["entities_filtered"].keys())))
    for t in types:
        m_raw = s["entities_raw"].get(t, 0)
        m_pas = s.get("entities_passed_filter", {}).get(t, 0)
        m_flt = s["entities_filtered"].get(t, 0)
        u_raw = s["unique_raw"].get(t, 0)
        u_pas = s.get("unique_passed_filter", {}).get(t, 0)
        u_flt = s["unique_filtered"].get(t, 0)
        out.append(f"| {t} | {m_raw:,} | {m_pas:,} | {m_flt:,} | {u_raw:,} | {u_pas:,} | {u_flt:,} |")
    out.append("")

    # Table F — Risk levels
    out.append("## Table F — Risk Level Distribution")
    out.append("")
    out.append("| Level | Count |")
    out.append("|---|---:|")
    for lvl in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        out.append(f"| {lvl} | {s['risk_levels'].get(lvl, 0):,} |")
    out.append("")

    # Table G — Threat topics
    out.append("## Table G — Threat Topic Distribution")
    out.append("")
    out.append("| Topic | Count |")
    out.append("|---|---:|")
    for k, v in sorted(s["threat_topics"].items(), key=lambda x: -x[1]):
        out.append(f"| {k} | {v:,} |")
    out.append("")

    # Table H — Correlations
    c = s["correlation"]
    out.append("## Table H — Correlation Hits")
    out.append("")
    out.append(f"- Records with matched threat actor: **{c['records_with_actor']:,}**")
    out.append(f"- Records with matched campaign: **{c['records_with_campaign']:,}**")
    out.append(f"- Records with matched CVE: **{c['records_with_cve']:,}**")
    out.append("")
    if c["top_actors"]:
        out.append("**Top actors:**")
        out.append("")
        out.append("| Actor | Mentions |")
        out.append("|---|---:|")
        for k, v in c["top_actors"].items():
            out.append(f"| {k} | {v:,} |")
        out.append("")
    if c["top_campaigns"]:
        out.append("**Top campaigns:**")
        out.append("")
        out.append("| Campaign | Mentions |")
        out.append("|---|---:|")
        for k, v in c["top_campaigns"].items():
            out.append(f"| {k} | {v:,} |")
        out.append("")

    # Table I — Alerts (from SQLite)
    if db.get("available"):
        out.append("## Table I — Alerts (from SQLite)")
        out.append("")
        out.append("| Severity | Count |")
        out.append("|---|---:|")
        for k, v in sorted(db.get("by_severity", {}).items(), key=lambda x: -x[1]):
            out.append(f"| {k} | {v:,} |")
        out.append("")
        if db.get("by_alert_type"):
            out.append("**Top alert types:**")
            out.append("")
            out.append("| Type | Count |")
            out.append("|---|---:|")
            for k, v in db["by_alert_type"].items():
                out.append(f"| {k} | {v:,} |")
            out.append("")

    # Table J — Forum breakdown
    if db.get("by_forum"):
        out.append("## Table J — Source Forum (from SQLite)")
        out.append("")
        out.append("> Note: `source_forum` is set only on records analyzed "
                   "after Phase-1 wiring, so coverage is partial.")
        out.append("")
        out.append("| Forum | Records |")
        out.append("|---|---:|")
        for k, v in db["by_forum"].items():
            out.append(f"| {k} | {v:,} |")
        out.append("")

    return "\n".join(out)


def render_latex(stats: dict) -> str:
    s = stats["streamed"]
    db = stats["sqlite"]
    total = s["total_records"]
    out = []
    out.append("% pipeline_stats_tables.tex — generated by scripts/pipeline_stats.py")
    out.append("% Tables A–K, paper-ready.")
    out.append("")

    # Table A
    out.append(r"\begin{table}[h]\centering")
    out.append(r"\caption{Pipeline stage funnel.}")
    out.append(r"\label{tab:pipeline_funnel}")
    out.append(r"\begin{tabular}{lrr}\hline")
    out.append(r"\textbf{Stage} & \textbf{Records} & \textbf{\% total} \\ \hline")
    for key, label in FUNNEL_ORDER:
        n = s["funnel"].get(key, 0)
        safe = label.replace("&", r"\&").replace("%", r"\%")
        out.append(f"{safe} & {n:,} & {fmt_pct(n, total)} \\\\")
    out.append(rf"\hline \textbf{{Total}} & \textbf{{{total:,}}} & 100.0 \\ \hline")
    out.append(r"\end{tabular}\end{table}")
    out.append("")

    # Table E
    out.append(r"\begin{table}[h]\centering")
    out.append(r"\caption{Entity extraction: raw, post-filter, and dictionary-filtered counts. "
               r"NER is currently applied before the upstream filter is consulted, so the raw "
               r"column includes noise records (cleaner-rejected, spam, pre-filter). "
               r"\textit{Passed-filter} is the honest count restricted to records that survived "
               r"all filtering stages. \textit{Dict} additionally requires TOOL/THREAT\_ACTOR/"
               r"MALWARE values to match the cybersec dictionary.}")
    out.append(r"\label{tab:entities}")
    out.append(r"\begin{tabular}{lrrrrrr}\hline")
    out.append(r"\textbf{Type} & \textbf{Raw} & \textbf{Passed} & \textbf{Dict} "
               r"& \textbf{Uniq Raw} & \textbf{Uniq Passed} & \textbf{Uniq Dict} \\ \hline")
    types = sorted(set(list(s["entities_raw"].keys()) + list(s["entities_filtered"].keys())))
    for t in types:
        m_raw = s["entities_raw"].get(t, 0)
        m_pas = s.get("entities_passed_filter", {}).get(t, 0)
        m_flt = s["entities_filtered"].get(t, 0)
        u_raw = s["unique_raw"].get(t, 0)
        u_pas = s.get("unique_passed_filter", {}).get(t, 0)
        u_flt = s["unique_filtered"].get(t, 0)
        safe_t = t.replace("_", r"\_")
        out.append(f"{safe_t} & {m_raw:,} & {m_pas:,} & {m_flt:,} & {u_raw:,} & {u_pas:,} & {u_flt:,} \\\\")
    out.append(r"\hline\end{tabular}\end{table}")
    out.append("")

    # Table F
    out.append(r"\begin{table}[h]\centering")
    out.append(r"\caption{Risk level distribution.}")
    out.append(r"\label{tab:risk_levels}")
    out.append(r"\begin{tabular}{lr}\hline")
    out.append(r"\textbf{Level} & \textbf{Records} \\ \hline")
    for lvl in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        out.append(f"{lvl} & {s['risk_levels'].get(lvl, 0):,} \\\\")
    out.append(r"\hline\end{tabular}\end{table}")
    out.append("")

    # Table I (alerts) when DB present
    if db.get("available") and db.get("by_severity"):
        out.append(r"\begin{table}[h]\centering")
        out.append(r"\caption{Alert severity distribution (SQLite).}")
        out.append(r"\label{tab:alerts}")
        out.append(r"\begin{tabular}{lr}\hline")
        out.append(r"\textbf{Severity} & \textbf{Count} \\ \hline")
        for k, v in sorted(db["by_severity"].items(), key=lambda x: -x[1]):
            safe = k.replace("&", r"\&")
            out.append(f"{safe} & {v:,} \\\\")
        out.append(r"\hline\end{tabular}\end{table}")
        out.append("")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default=str(DEFAULT_INPUT))
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--out-json", default=str(DEFAULT_OUT_JSON))
    p.add_argument("--out-tex", default=str(DEFAULT_OUT_TEX))
    p.add_argument("--out-md", default=str(DEFAULT_OUT_MD))
    args = p.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"Input not found: {in_path}")

    print(f"Loading cyber dictionaries...", flush=True)
    dicts = load_cyber_dicts()
    print(f"  TOOL={len(dicts['TOOL'])}  THREAT_ACTOR={len(dicts['THREAT_ACTOR'])}  "
          f"MALWARE={len(dicts['MALWARE'])}", flush=True)

    print(f"Streaming pass over {in_path}...", flush=True)
    streamed = streaming_pass(in_path, dicts)
    print(f"  {streamed['total_records']:,} records in {streamed['elapsed_s']}s", flush=True)

    print(f"Querying SQLite at {args.db}...", flush=True)
    db = sqlite_stats(Path(args.db))

    print(f"Querying FalkorDB...", flush=True)
    g = graph_stats()

    stats = {
        "input": str(in_path),
        "db": str(args.db),
        "streamed": streamed,
        "sqlite": db,
        "graph": g,
        "warnings": [],
    }
    stats["warnings"] = assert_funnel_consistency(streamed)

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(stats, indent=2))
    print(f"Wrote {args.out_json}", flush=True)

    Path(args.out_md).write_text(render_markdown(stats))
    print(f"Wrote {args.out_md}", flush=True)

    Path(args.out_tex).write_text(render_latex(stats))
    print(f"Wrote {args.out_tex}", flush=True)

    if stats["warnings"]:
        print("\nWARNINGS:")
        for w in stats["warnings"]:
            print(f"  - {w}")


if __name__ == "__main__":
    main()
