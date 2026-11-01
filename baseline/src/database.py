"""Database Layer for DarkWeb Translation Pipeline."""
import json, logging, sqlite3, hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ThreatDatabase:
    # Tables only — no indexes. CREATE TABLE IF NOT EXISTS is a no-op on
    # existing DBs and won't add new columns to a pre-existing `records`
    # table; that's what _MIGRATIONS is for.
    _TABLES_SCHEMA = """
    CREATE TABLE IF NOT EXISTS records (
        id TEXT PRIMARY KEY,
        raw_text TEXT,
        translated_text TEXT,
        detected_language TEXT,
        risk_score REAL,
        risk_level TEXT,
        threat_topic TEXT,
        entities_json TEXT,
        iocs_json TEXT,
        processed_at TEXT,
        processed_ts INTEGER,
        source_forum TEXT
    );
    CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY,
        record_id TEXT,
        entity_type TEXT,
        entity_value TEXT
    );
    CREATE TABLE IF NOT EXISTS iocs (
        id INTEGER PRIMARY KEY,
        record_id TEXT,
        ioc_type TEXT,
        ioc_value TEXT
    );
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY,
        record_id TEXT,
        alert_type TEXT,
        severity TEXT,
        title TEXT,
        description TEXT,
        created_at TEXT,
        acknowledged INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY,
        record_id TEXT,
        analyst TEXT,
        label TEXT,
        confidence REAL,
        comment TEXT,
        created_at TEXT
    );
    """

    # Indexes — must run AFTER migrations because some reference newly-added
    # columns (processed_ts, source_forum). Splitting from _TABLES_SCHEMA so
    # an upgraded run on an old DB doesn't blow up before ALTER TABLE has a
    # chance to add the columns.
    _INDEXES_SCHEMA = """
    CREATE INDEX IF NOT EXISTS idx_records_lang ON records(detected_language);
    CREATE INDEX IF NOT EXISTS idx_records_topic ON records(threat_topic);
    CREATE INDEX IF NOT EXISTS idx_records_risk ON records(risk_level);
    CREATE INDEX IF NOT EXISTS idx_records_risk_score ON records(risk_score DESC);
    CREATE INDEX IF NOT EXISTS idx_records_ts ON records(processed_ts);
    CREATE INDEX IF NOT EXISTS idx_records_forum ON records(source_forum);
    CREATE INDEX IF NOT EXISTS idx_entities_record ON entities(record_id);
    CREATE INDEX IF NOT EXISTS idx_entities_value ON entities(entity_value);
    CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
    CREATE INDEX IF NOT EXISTS idx_iocs_record ON iocs(record_id);
    CREATE INDEX IF NOT EXISTS idx_iocs_value ON iocs(ioc_value);
    CREATE INDEX IF NOT EXISTS idx_alerts_record ON alerts(record_id);
    CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
    CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);
    CREATE INDEX IF NOT EXISTS idx_alerts_ack ON alerts(acknowledged);
    """

    # Backwards-compat alias so any external caller of the old `SCHEMA`
    # constant still works (combines tables + indexes; only safe on a fresh
    # DB; the proper init path uses the split scripts plus _MIGRATIONS).
    SCHEMA = _TABLES_SCHEMA + _INDEXES_SCHEMA

    # Columns added after initial release; ALTER TABLE on existing DBs.
    _MIGRATIONS = [
        "ALTER TABLE records ADD COLUMN processed_ts INTEGER",
        "ALTER TABLE records ADD COLUMN source_forum TEXT",
    ]

    def __init__(self, config: Dict[str, Any]):
        self.db_path = Path(config.get("storage", {}).get("database_path", "data/threat_intel.db"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # Step 1: tables (idempotent; CREATE TABLE IF NOT EXISTS is a no-op
        # on existing tables and does NOT add new columns to them).
        self._conn.executescript(self._TABLES_SCHEMA)
        # Step 2: column migrations for DBs created before this iteration.
        for stmt in self._MIGRATIONS:
            try:
                self._conn.execute(stmt)
            except sqlite3.OperationalError:
                pass  # column already exists
        # Step 3: indexes — now safe because every column they reference is
        # guaranteed to exist (either from CREATE TABLE on a fresh DB, or
        # from the ALTER TABLE migrations above on an upgraded DB).
        self._conn.executescript(self._INDEXES_SCHEMA)
        self._conn.commit()
        logger.info(f"Database at {self.db_path}")
    
    def insert_record(self, record: Dict, analysis: Dict = None, correlation: Dict = None) -> str:
        analysis = analysis or {}
        raw = record.get("raw_text", "") or ""
        # Stable hash over the full raw text; raw_text[:200] alone collided on long forum
        # threads with identical preambles. SHA1 to keep the existing 40-char id width-ish.
        rid = hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()
        cur = self._conn.cursor()
        # Delete child rows first so re-inserting on resume doesn't accumulate duplicates.
        cur.execute("DELETE FROM entities WHERE record_id = ?", (rid,))
        cur.execute("DELETE FROM iocs WHERE record_id = ?", (rid,))
        cur.execute("DELETE FROM alerts WHERE record_id = ?", (rid,))
        now = datetime.now()
        cur.execute(
            """INSERT OR REPLACE INTO records
               (id, raw_text, translated_text, detected_language, risk_score, risk_level,
                threat_topic, entities_json, iocs_json, processed_at, processed_ts, source_forum)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rid, raw, record.get("translated_text"), record.get("detected_language"),
             analysis.get("risk_score"), analysis.get("risk_level"), analysis.get("threat_topic"),
             json.dumps(analysis.get("entities", [])), json.dumps(analysis.get("iocs", {})),
             now.isoformat(), int(now.timestamp()),
             record.get("source_forum") or record.get("forum") or record.get("source"))
        )
        for entity in analysis.get("entities", []):
            cur.execute("INSERT INTO entities (record_id, entity_type, entity_value) VALUES (?,?,?)", (rid, entity.get("label"), entity.get("text")))
        for ioc_type, values in analysis.get("iocs", {}).items():
            for v in values:
                cur.execute("INSERT INTO iocs (record_id, ioc_type, ioc_value) VALUES (?,?,?)", (rid, ioc_type, v))
        self._conn.commit()
        return rid

    def insert_feedback(self, record_id: str, analyst: str, label: str,
                        confidence: float = 1.0, comment: str = "") -> int:
        """Persist analyst feedback for the manual-labeling page in the dashboard."""
        cur = self._conn.cursor()
        cur.execute(
            """INSERT INTO feedback (record_id, analyst, label, confidence, comment, created_at)
               VALUES (?,?,?,?,?,?)""",
            (record_id, analyst, label, float(confidence), comment, datetime.now().isoformat())
        )
        self._conn.commit()
        return cur.lastrowid

    def acknowledge_alert(self, alert_id: int) -> None:
        """Mark an alert as reviewed so it stops appearing in the live feed."""
        self._conn.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))
        self._conn.commit()

    # ---- Indexed pivot queries used by the dashboard redesign -----------------

    def get_distinct_languages(self) -> List[str]:
        cur = self._conn.execute(
            "SELECT DISTINCT detected_language FROM records WHERE detected_language IS NOT NULL"
        )
        return [r[0] for r in cur.fetchall()]

    def get_distinct_severities(self) -> List[str]:
        cur = self._conn.execute(
            "SELECT DISTINCT severity FROM alerts WHERE severity IS NOT NULL"
        )
        return [r[0] for r in cur.fetchall()]

    def search_by_entity(self, entity_type: str, value: str, limit: int = 200) -> List[Dict]:
        cur = self._conn.execute(
            """SELECT r.* FROM records r
               JOIN entities e ON e.record_id = r.id
               WHERE e.entity_type = ? AND e.entity_value LIKE ?
               ORDER BY r.processed_ts DESC LIMIT ?""",
            (entity_type, f"%{value}%", limit)
        )
        return [dict(r) for r in cur.fetchall()]

    def get_alerts_in_range(self, start_ts: int, end_ts: int,
                            severity: Optional[str] = None, limit: int = 500) -> List[Dict]:
        sql = ("SELECT * FROM alerts WHERE created_at >= datetime(?, 'unixepoch') "
               "AND created_at <= datetime(?, 'unixepoch')")
        params = [start_ts, end_ts]
        if severity:
            sql += " AND severity = ?"
            params.append(severity)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]
    
    def get_record(self, record_id: str) -> Optional[Dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM records WHERE id = ?", [record_id])
        row = cur.fetchone()
        return dict(row) if row else None
    
    def search_records(self, query: str = None, limit: int = 100) -> List[Dict]:
        cur = self._conn.cursor()
        if query:
            cur.execute("SELECT * FROM records WHERE translated_text LIKE ? LIMIT ?", [f"%{query}%", limit])
        else:
            cur.execute("SELECT * FROM records ORDER BY risk_score DESC LIMIT ?", [limit])
        return [dict(r) for r in cur.fetchall()]
    
    def insert_alert(self, record_id: str, alert_type: str, severity: str, title: str, desc: str) -> int:
        cur = self._conn.cursor()
        cur.execute("INSERT INTO alerts (record_id, alert_type, severity, title, description, created_at) VALUES (?,?,?,?,?,?)",
            (record_id, alert_type, severity, title, desc, datetime.now().isoformat()))
        self._conn.commit()
        return cur.lastrowid
    
    def get_alerts(self, limit: int = 100) -> List[Dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM alerts WHERE acknowledged=0 ORDER BY created_at DESC LIMIT ?", [limit])
        return [dict(r) for r in cur.fetchall()]
    
    def get_statistics(self) -> Dict[str, Any]:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM records")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged=0")
        alerts = cur.fetchone()[0]
        return {"total_records": total, "unacknowledged_alerts": alerts}
    
    def close(self):
        if self._conn:
            self._conn.close()
