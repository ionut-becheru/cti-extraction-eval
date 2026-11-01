"""MITRE ATT&CK Enterprise STIX 2.1 → ingest records.

Pulls intrusion-set, malware, and tool objects; uses their descriptions as
raw_text and enriches with aliases + associated techniques so the NER
dictionary and MITRE_TECHNIQUE regex both hit.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Iterator

from .common import (
    cache_path, download, normalize_record, _clean_mitre_markdown, _session,
)

logger = logging.getLogger("ingest.mitre")

STIX_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/"
    "enterprise-attack/enterprise-attack.json"
)


def fetch_and_yield_records(cache_dir: Path, max_records: int | None = None,
                            **_kwargs) -> Iterator[dict]:
    src = "mitre_attack"
    json_path = cache_path(cache_dir, src, "enterprise-attack.json")
    download(STIX_URL, json_path, session=_session())

    with open(json_path, encoding="utf-8") as f:
        bundle = json.load(f)

    objects = bundle.get("objects", [])
    logger.info("mitre: %d STIX objects in bundle", len(objects))

    # Build a quick index: id → object. We'll use it for technique lookups.
    by_id = {o.get("id"): o for o in objects if "id" in o}

    # Map intrusion-set / malware / tool ids → set of technique stix-ids
    # (via "relationship" objects of type "uses").
    uses_techniques: dict[str, set[str]] = defaultdict(set)
    for o in objects:
        if (o.get("type") == "relationship"
                and o.get("relationship_type") == "uses"
                and o.get("source_ref")
                and o.get("target_ref", "").startswith("attack-pattern--")):
            uses_techniques[o["source_ref"]].add(o["target_ref"])

    n_yielded = 0
    for o in objects:
        otype = o.get("type")
        if otype not in ("intrusion-set", "malware", "tool"):
            continue
        if o.get("revoked") or o.get("x_mitre_deprecated"):
            continue

        name = (o.get("name") or "").strip()
        desc = _clean_mitre_markdown(o.get("description", "") or "")
        if not name or not desc:
            continue

        # Find external_references → ATT&CK ID like G0016 / S0099 / etc.
        attack_id = ""
        url = ""
        for ref in o.get("external_references", []) or []:
            if ref.get("source_name") == "mitre-attack":
                attack_id = ref.get("external_id", "")
                url = ref.get("url", "")
                break

        # Aliases (also a strong NER signal — produces multiple dict hits per record)
        aliases = o.get("aliases", []) or []
        if not aliases:
            # MALWARE/TOOL store aliases under x_mitre_aliases
            aliases = o.get("x_mitre_aliases", []) or []
        aliases = [a for a in aliases if a and a != name]

        # Associated technique IDs (T1059, T1566.001 etc.) — used by MITRE_TECHNIQUE regex
        tech_ids: list[str] = []
        for tref in uses_techniques.get(o["id"], []):
            tobj = by_id.get(tref)
            if not tobj:
                continue
            for ref in tobj.get("external_references", []) or []:
                if ref.get("source_name") == "mitre-attack":
                    tid = ref.get("external_id", "")
                    if tid.startswith("T"):
                        tech_ids.append(tid)
                        break

        # Build raw_text: header line + description + aliases + technique list
        type_label = {
            "intrusion-set": "Threat actor",
            "malware":       "Malware",
            "tool":          "Tool",
        }[otype]
        header = f"{type_label} {name}"
        if attack_id:
            header += f" ({attack_id})"
        if aliases:
            header += f". Also known as: {', '.join(aliases[:10])}."
        body = desc
        if tech_ids:
            uniq = sorted(set(tech_ids))
            body += " Associated MITRE ATT&CK techniques: " + ", ".join(uniq[:25]) + "."

        raw_text = f"{header}. {body}"
        rec = normalize_record(
            raw_text,
            source_forum=src,
            timestamp=o.get("modified") or o.get("created"),
            url=url,
            file_type="json",
            file_info="mitre-attack-stix-data enterprise-attack",
        )
        if rec is None:
            continue
        yield rec
        n_yielded += 1
        if max_records and n_yielded >= max_records:
            break
    logger.info("mitre: yielded %d records", n_yielded)
