"""
Graph-database mirror for the correlation layer.

Materializes the in-memory adjacency graph maintained by CorrelationEngine
(records ↔ entities ↔ actors ↔ campaigns ↔ CVEs ↔ forums ↔ time buckets)
into FalkorDB so analysts can query it with Cypher and explore it visually
in the FalkorDB Browser.

Design principles:
- SQLite stays the source of truth. The graph is a derived, optional view.
- All writes use Cypher MERGE so re-runs (e.g. via run_full_analysis.py) are
  idempotent and never duplicate nodes or edges.
- Failures are non-fatal: a per-record graph write failure logs a warning and
  increments a counter. The pipeline keeps moving.
- Indexes are created at startup so 10M-edge queries stay fast.

Falls back cleanly if `falkordb` isn't installed: GraphDisabled stub raises
a clear error only on use.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

# Soft-import so the rest of the pipeline keeps working when FalkorDB is
# unavailable (e.g. fresh checkout before `pip install FalkorDB`). The
# constructor handles the missing-import case explicitly.
try:
    from falkordb import FalkorDB, Graph  # type: ignore
    _FALKORDB_AVAILABLE = True
except ImportError:  # pragma: no cover
    FalkorDB = None  # type: ignore
    Graph = None  # type: ignore
    _FALKORDB_AVAILABLE = False


# ---------------------------------------------------------------- ISO week

def _iso_week_key(when: Optional[datetime] = None) -> str:
    """'YYYY-Www' string for a datetime (default: now). Matches the format
    used by CorrelationEngine.temporal_matches so they stay joinable."""
    when = when or datetime.utcnow()
    year, week, _ = when.isocalendar()
    return f"{year}-W{week:02d}"


# ---------------------------------------------------------------- node helpers

def _entity_key(label: str, value: str) -> str:
    """Composite key used as the unique identifier for Entity nodes.

    FalkorDB doesn't support multi-property MERGE keys directly; we serialize
    label+value into a single key so MERGE-by-key works without ambiguity.
    Lowercase the value for hash/IP/email/URL/domain (case-insensitive
    semantics); preserve case for malware and threat actor names where
    casing matters ("LockBit" vs "lockbit" should still merge — we lowercase
    everything for safety, and store the original casing as a property).
    """
    return f"{label}::{(value or '').strip().lower()}"


# ---------------------------------------------------------------- main class

class FalkorGraph:
    """Idempotent graph-DB writer for the CTI pipeline.

    Lifecycle:
        g = FalkorGraph(host, port, password, graph_name)
        g.ensure_indexes()       # idempotent, run once at startup
        g.bulk_upsert_record(record_id, props, entities, actors, ...)  # per record
        g.cleanup()              # at shutdown

    Connection failures during construction are NOT raised — the instance
    enters a degraded `enabled=False` state that no-ops every write. This
    way a caller-side `if g.enabled:` is enough to gate operations and a
    missing FalkorDB doesn't crash the pipeline.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6379,
                 password: str = "", graph_name: str = "darkweb_threat_intel"):
        self.host = host
        self.port = int(port)
        self.password = password or None
        self.graph_name = graph_name
        self.enabled = False
        self._db: Optional[Any] = None
        self._graph: Optional[Any] = None
        self.write_failures = 0
        self.writes = 0

        if not _FALKORDB_AVAILABLE:
            logger.warning(
                "FalkorDB Python client not installed (`pip install FalkorDB`); "
                "graph mirror disabled. The SQLite path is unaffected."
            )
            return

        try:
            self._db = FalkorDB(host=self.host, port=self.port,
                                password=self.password)
            self._graph = self._db.select_graph(self.graph_name)
            # Trip a cheap query to verify the connection works.
            self._graph.query("RETURN 1")
            self.enabled = True
            logger.info(
                "FalkorDB connected at %s:%d, graph=%s",
                self.host, self.port, self.graph_name
            )
        except Exception as e:
            logger.warning(
                "FalkorDB connection failed (%s); graph mirror disabled. "
                "Pipeline will continue with SQLite only.", e
            )
            self.enabled = False

    # ---------------------------------------------------------------- init

    def ensure_indexes(self) -> None:
        """Create the indexes the dashboard pivots on. Idempotent.

        Uses range indexes which back ORDER BY / WHERE / equality lookups.
        At ~10M-edge scale, missing indexes on Entity(value) make pivot
        queries slow enough to block the dashboard.
        """
        if not self.enabled:
            return
        # Note: FalkorDB indexes are per-label, per-property. The Python
        # client API takes the label and property name separately.
        index_specs = [
            ("Entity", "value"),
            ("Entity", "label"),
            ("Record", "id"),
            ("Record", "processed_ts"),
            ("Record", "risk_level"),
            ("Actor", "id"),
            ("Campaign", "id"),
            ("CVE", "id"),
            ("Forum", "name"),
            ("TimeBucket", "iso_week"),
            ("Technique", "id"),
        ]
        for label, prop in index_specs:
            try:
                self._graph.create_node_range_index(label, prop)
            except Exception as e:
                # Already-exists errors are normal on re-init; demote to debug.
                msg = str(e).lower()
                if "already" in msg or "exists" in msg:
                    logger.debug("Index already exists: %s.%s", label, prop)
                else:
                    logger.warning("Failed to create index %s.%s: %s",
                                   label, prop, e)
        logger.info("Graph indexes ensured (%d specs)", len(index_specs))

    # ---------------------------------------------------------------- query

    def _query(self, cypher: str, params: Optional[Dict] = None) -> Any:
        """Wrap a query with consistent error handling + counters."""
        if not self.enabled:
            return None
        try:
            res = self._graph.query(cypher, params or {})
            self.writes += 1
            return res
        except Exception as e:
            self.write_failures += 1
            logger.debug("Graph query failed: %s | cypher=%s | params=%s",
                         e, cypher[:120], params)
            return None

    # ---------------------------------------------------------------- node merges

    def upsert_record(self, record_id: str, props: Dict[str, Any]) -> None:
        """MERGE a Record node by id; SET freshens its mutable properties."""
        if not self.enabled or not record_id:
            return
        # Pull only the fields we model on Record; ignore extras to keep the
        # graph schema stable.
        clean = {
            'id': record_id,
            'language': props.get('detected_language'),
            'risk_score': props.get('risk_score'),
            'risk_level': props.get('risk_level'),
            'threat_topic': props.get('threat_topic'),
            'processed_ts': props.get('processed_ts') or int(datetime.utcnow().timestamp()),
            'source_forum': props.get('source_forum') or props.get('forum'),
            'text_preview': (props.get('translated_text')
                             or props.get('cleaned_text')
                             or props.get('raw_text') or '')[:200],
        }
        # Strip None to avoid setting nulls that would shadow existing values
        # on re-upsert (FalkorDB SET overwrites; we want to leave properties
        # untouched when the new value is null).
        clean = {k: v for k, v in clean.items() if v is not None}
        self._query(
            """MERGE (r:Record {id: $id})
               SET r += $props""",
            {'id': record_id, 'props': clean}
        )

    def upsert_entity(self, label: str, value: str,
                      extra: Optional[Dict] = None) -> None:
        """MERGE a single Entity node identified by (label, value).

        We use a composite key field `key` to avoid the FalkorDB limitation
        on multi-property MERGE keys, and ALSO store label and value
        separately for filtering and display.
        """
        if not self.enabled or not value:
            return
        key = _entity_key(label, value)
        props = {'key': key, 'label': label, 'value': value}
        if extra:
            for k, v in extra.items():
                if v is not None:
                    props[k] = v
        self._query(
            """MERGE (e:Entity {key: $key})
               SET e += $props""",
            {'key': key, 'props': props}
        )

    def upsert_actor(self, profile: Dict[str, Any]) -> None:
        """MERGE an Actor node from a CorrelationEngine ThreatActorProfile."""
        if not self.enabled:
            return
        actor_id = profile.get('id') or profile.get('name', '').lower()
        if not actor_id:
            return
        props = {
            'id': actor_id,
            'name': profile.get('name'),
            'aliases': list(profile.get('aliases', []) or []),
            'country': profile.get('country'),
            'motivation': profile.get('motivation'),
            'targets': list(profile.get('targets', []) or []),
        }
        props = {k: v for k, v in props.items() if v is not None}
        self._query(
            """MERGE (a:Actor {id: $id}) SET a += $props""",
            {'id': actor_id, 'props': props}
        )

    def upsert_campaign(self, campaign: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        cid = campaign.get('id') or campaign.get('name', '').lower().replace(' ', '_')
        if not cid:
            return
        props = {
            'id': cid,
            'name': campaign.get('name'),
            'timeframe_start': (campaign.get('timeframe') or [None, None])[0],
            'timeframe_end': (campaign.get('timeframe') or [None, None])[1],
            'score': campaign.get('score'),
        }
        props = {k: v for k, v in props.items() if v is not None}
        self._query(
            """MERGE (c:Campaign {id: $id}) SET c += $props""",
            {'id': cid, 'props': props}
        )

    def upsert_cve(self, cve_id: str, extra: Optional[Dict] = None) -> None:
        if not self.enabled or not cve_id:
            return
        cve_id = cve_id.upper()
        props = {'id': cve_id}
        if extra:
            for k in ('cvss_score', 'severity', 'description'):
                if extra.get(k) is not None:
                    props[k] = extra[k]
        self._query(
            """MERGE (c:CVE {id: $id}) SET c += $props""",
            {'id': cve_id, 'props': props}
        )

    def upsert_forum(self, name: str) -> None:
        if not self.enabled or not name:
            return
        self._query("MERGE (f:Forum {name: $name})", {'name': name})

    def upsert_timebucket(self, iso_week: str) -> None:
        if not self.enabled or not iso_week:
            return
        try:
            year, week_str = iso_week.split('-W')
            year = int(year)
            week = int(week_str)
        except (ValueError, AttributeError):
            year, week = None, None
        props = {'iso_week': iso_week}
        if year:
            props['year'] = year
        if week:
            props['week'] = week
        self._query(
            """MERGE (t:TimeBucket {iso_week: $iw}) SET t += $props""",
            {'iw': iso_week, 'props': props}
        )

    def upsert_technique(self, technique_id: str) -> None:
        if not self.enabled or not technique_id:
            return
        self._query(
            "MERGE (t:Technique {id: $id})", {'id': technique_id}
        )

    # ---------------------------------------------------------------- edges

    def link_record_entity(self, record_id: str, label: str, value: str,
                           confidence: Optional[float] = None) -> None:
        if not self.enabled or not record_id or not value:
            return
        key = _entity_key(label, value)
        props = {'confidence': confidence} if confidence is not None else {}
        self._query(
            """MATCH (r:Record {id: $rid}), (e:Entity {key: $ek})
               MERGE (r)-[m:MENTIONS]->(e)
               SET m += $props""",
            {'rid': record_id, 'ek': key, 'props': props}
        )

    def link_record_actor(self, record_id: str, actor_id: str) -> None:
        if not self.enabled or not record_id or not actor_id:
            return
        self._query(
            """MATCH (r:Record {id: $rid}), (a:Actor {id: $aid})
               MERGE (r)-[:MENTIONS_ACTOR]->(a)""",
            {'rid': record_id, 'aid': actor_id}
        )

    def link_record_campaign(self, record_id: str, campaign_id: str,
                             score: Optional[float] = None) -> None:
        if not self.enabled or not record_id or not campaign_id:
            return
        self._query(
            """MATCH (r:Record {id: $rid}), (c:Campaign {id: $cid})
               MERGE (r)-[m:MENTIONS_CAMPAIGN]->(c)
               SET m.score = coalesce($score, m.score)""",
            {'rid': record_id, 'cid': campaign_id, 'score': score}
        )

    def link_record_cve(self, record_id: str, cve_id: str) -> None:
        if not self.enabled or not record_id or not cve_id:
            return
        self._query(
            """MATCH (r:Record {id: $rid}), (c:CVE {id: $cid})
               MERGE (r)-[:MENTIONS_CVE]->(c)""",
            {'rid': record_id, 'cid': cve_id.upper()}
        )

    def link_record_forum(self, record_id: str, forum: str) -> None:
        if not self.enabled or not record_id or not forum:
            return
        self._query(
            """MATCH (r:Record {id: $rid}), (f:Forum {name: $f})
               MERGE (r)-[:POSTED_ON]->(f)""",
            {'rid': record_id, 'f': forum}
        )

    def link_record_timebucket(self, record_id: str, iso_week: str) -> None:
        if not self.enabled or not record_id or not iso_week:
            return
        self._query(
            """MATCH (r:Record {id: $rid}), (t:TimeBucket {iso_week: $iw})
               MERGE (r)-[:OCCURRED_IN]->(t)""",
            {'rid': record_id, 'iw': iso_week}
        )

    def link_actor_uses_tool(self, actor_id: str, tool_value: str) -> None:
        if not self.enabled or not actor_id or not tool_value:
            return
        key = _entity_key('TOOL', tool_value)
        # Ensure tool entity exists first
        self.upsert_entity('TOOL', tool_value)
        self._query(
            """MATCH (a:Actor {id: $aid}), (e:Entity {key: $ek})
               MERGE (a)-[:USES]->(e)""",
            {'aid': actor_id, 'ek': key}
        )

    def link_actor_uses_technique(self, actor_id: str, technique_id: str) -> None:
        if not self.enabled or not actor_id or not technique_id:
            return
        self.upsert_technique(technique_id)
        self._query(
            """MATCH (a:Actor {id: $aid}), (t:Technique {id: $tid})
               MERGE (a)-[:USES_TECHNIQUE]->(t)""",
            {'aid': actor_id, 'tid': technique_id}
        )

    def link_campaign_exploits_cve(self, campaign_id: str, cve_id: str) -> None:
        if not self.enabled or not campaign_id or not cve_id:
            return
        self.upsert_cve(cve_id)
        self._query(
            """MATCH (c:Campaign {id: $cid}), (v:CVE {id: $vid})
               MERGE (c)-[:EXPLOITS]->(v)""",
            {'cid': campaign_id, 'vid': cve_id.upper()}
        )

    def link_campaign_attributed_to_actor(self, campaign_id: str,
                                          actor_id: str,
                                          confidence: float = 1.0) -> None:
        if not self.enabled or not campaign_id or not actor_id:
            return
        self._query(
            """MATCH (c:Campaign {id: $cid}), (a:Actor {id: $aid})
               MERGE (c)-[r:ATTRIBUTED_TO]->(a)
               SET r.confidence = $conf""",
            {'cid': campaign_id, 'aid': actor_id, 'conf': float(confidence)}
        )

    # ---------------------------------------------------------------- bulk

    def bulk_upsert_record(self,
                           record_id: str,
                           record_props: Dict[str, Any],
                           entities: Optional[Iterable[Dict]] = None,
                           matched_actors: Optional[Iterable[Dict]] = None,
                           matched_campaigns: Optional[Iterable[Dict]] = None,
                           matched_cves: Optional[Iterable[Dict]] = None,
                           source_forum: Optional[str] = None,
                           processed_ts: Optional[int] = None) -> None:
        """Mirror one analyzed record + all its relationships into the graph.

        Called once per record from BatchProcessor._analyze_record. Designed
        to be called many times per second; uses many small MERGE queries
        (FalkorDB is in-memory + GraphBLAS-fast — this is fine at <50 edges
        per record).
        """
        if not self.enabled or not record_id:
            return
        # Force a record_props copy and inject computed time bucket
        props = dict(record_props or {})
        if processed_ts is not None:
            props['processed_ts'] = processed_ts
        if source_forum and not props.get('source_forum'):
            props['source_forum'] = source_forum

        # 1. Record node
        self.upsert_record(record_id, props)

        # 2. Forum node + edge
        forum = source_forum or props.get('source_forum')
        if forum:
            self.upsert_forum(forum)
            self.link_record_forum(record_id, forum)

        # 3. TimeBucket node + edge
        ts = props.get('processed_ts')
        when = datetime.utcfromtimestamp(ts) if ts else datetime.utcnow()
        iso_week = _iso_week_key(when)
        self.upsert_timebucket(iso_week)
        self.link_record_timebucket(record_id, iso_week)

        # 4. Entities (NER output) → MENTIONS edges
        for ent in (entities or []):
            label = ent.get('label')
            value = ent.get('text') or ent.get('value')
            if not label or not value:
                continue
            self.upsert_entity(label, value,
                               extra={'canonical': (ent.get('metadata') or {}).get('canonical')})
            self.link_record_entity(record_id, label, value,
                                    confidence=ent.get('confidence'))
            # CVEs and structured TOOL/MALWARE/THREAT_ACTOR also get
            # specialized typed nodes so cross-record traversal is direct.
            if label == 'CVE':
                self.upsert_cve(value)
                self.link_record_cve(record_id, value)

        # 5. Matched threat actors → MENTIONS_ACTOR edges
        for actor in (matched_actors or []):
            actor_id = actor.get('id') or actor.get('name', '').lower()
            if not actor_id:
                continue
            self.upsert_actor(actor)
            self.link_record_actor(record_id, actor_id)

        # 6. Matched campaigns → MENTIONS_CAMPAIGN edges
        for camp in (matched_campaigns or []):
            cid = camp.get('id') or camp.get('name', '').lower().replace(' ', '_')
            if not cid:
                continue
            self.upsert_campaign(camp)
            self.link_record_campaign(record_id, cid, score=camp.get('score'))
            # Also link the campaign to its CVEs (idempotent).
            for cve in camp.get('matched_cves', []) or camp.get('cves', []) or []:
                self.link_campaign_exploits_cve(cid, cve)

        # 7. Matched CVEs from NVD lookup (severity-rich) → MENTIONS_CVE edges
        for cve in (matched_cves or []):
            cve_id = (cve.get('cve_id') or cve.get('id') or '').upper()
            if not cve_id:
                continue
            self.upsert_cve(cve_id, extra={
                'cvss_score': cve.get('cvss_score'),
                'severity': cve.get('severity'),
                'description': cve.get('description'),
            })
            self.link_record_cve(record_id, cve_id)

    # ---------------------------------------------------------------- counts

    def get_counts(self) -> Dict[str, int]:
        """Return node-label counts for the dashboard. Cheap (one query)."""
        if not self.enabled:
            return {}
        try:
            res = self._graph.query(
                "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS n"
            )
            counts: Dict[str, int] = {}
            for row in (res.result_set or []):
                if row and row[0]:
                    counts[row[0]] = int(row[1])
            return counts
        except Exception as e:
            logger.debug("get_counts failed: %s", e)
            return {}

    def cleanup(self) -> None:
        if not self.enabled:
            return
        try:
            if self._db is not None:
                self._db.close()
        except Exception as e:
            logger.debug("FalkorDB close failed: %s", e)
        finally:
            logger.info(
                "FalkorGraph cleanup: %d writes, %d failures",
                self.writes, self.write_failures
            )
            self.enabled = False
