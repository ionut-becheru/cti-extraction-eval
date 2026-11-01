"""
Alerting and SIEM Integration for DarkWeb Translation Pipeline
Generates alerts based on threat signals and exports in SIEM-compatible formats.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Alert:
    """Represents a security alert."""
    alert_id: str = ""
    record_id: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    alert_type: str = ""
    title: str = ""
    description: str = ""
    iocs: List[str] = field(default_factory=list)
    cves: List[str] = field(default_factory=list)
    threat_actors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    created_at: str = ""
    source: str = "darkweb_pipeline"


class AlertingSystem:
    """Generates and exports security alerts."""
    
    # Alert rules based on risk scores and entities. The "critical_cve" rule
    # checks both an explicit critical severity tag and CVSS >= 9.0 — the latter
    # is the PDF-stated escalation that wasn't wired before this change.
    @staticmethod
    def _is_critical_cve(c):
        for cve in c.get("matched_cves", []):
            if cve.get("severity") == "critical":
                return True
            try:
                if float(cve.get("cvss_score") or 0.0) >= 9.0:
                    return True
            except (TypeError, ValueError):
                pass
        return False

    ALERT_RULES = [
        {"name": "critical_cve", "condition": lambda s, e, c: AlertingSystem._is_critical_cve(c), "severity": AlertSeverity.CRITICAL, "type": "vulnerability"},
        {"name": "known_threat_actor", "condition": lambda s, e, c: len(c.get("matched_threat_actors", [])) > 0, "severity": AlertSeverity.HIGH, "type": "threat_actor"},
        {"name": "high_risk", "condition": lambda s, e, c: s.get("risk_score", 0) >= 0.8, "severity": AlertSeverity.HIGH, "type": "high_risk"},
        {"name": "attack_planning", "condition": lambda s, e, c: s.get("threat_topic") == "attack_planning", "severity": AlertSeverity.CRITICAL, "type": "attack_planning"},
        {"name": "ransomware", "condition": lambda s, e, c: s.get("threat_topic") == "ransomware", "severity": AlertSeverity.HIGH, "type": "ransomware"},
        {"name": "data_breach", "condition": lambda s, e, c: s.get("threat_topic") == "data_breach", "severity": AlertSeverity.HIGH, "type": "data_breach"},
        {"name": "matched_campaign", "condition": lambda s, e, c: len(c.get("matched_campaigns", [])) > 0, "severity": AlertSeverity.HIGH, "type": "campaign"},
        {"name": "multiple_iocs", "condition": lambda s, e, c: len(s.get("iocs", {})) >= 3, "severity": AlertSeverity.MEDIUM, "type": "ioc_cluster"},
    ]

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Read from both the top-level `alerting:` block (preferred, matches PDF
        # 5.7) and the legacy `storage:` block. Top-level wins when both exist.
        alerting_config = config.get("alerting", {})
        storage_config = config.get("storage", {})

        self.enabled = alerting_config.get(
            "enable_alerting", storage_config.get("enable_alerting", False)
        )
        self.threshold = alerting_config.get(
            "alert_threshold", storage_config.get("alert_threshold", 0.7)
        )
        self.export_format = alerting_config.get(
            "siem_export_format", storage_config.get("siem_export_format", "json")
        )
        self.export_path = Path(alerting_config.get(
            "siem_export_path", storage_config.get("siem_export_path", "data/alerts")
        ))
        self.export_path.mkdir(parents=True, exist_ok=True)

        self._alert_count = 0
        logger.info(
            f"AlertingSystem initialized (enabled={self.enabled}, threshold={self.threshold})"
        )
    
    def _generate_alert_id(self) -> str:
        self._alert_count += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"ALERT-{timestamp}-{self._alert_count:04d}"
    
    def evaluate_rules(self, signal: Dict, entities: List[Dict], correlation: Dict) -> List[Alert]:
        """Evaluate alert rules and generate alerts."""
        alerts = []
        
        for rule in self.ALERT_RULES:
            try:
                if rule["condition"](signal, entities, correlation):
                    alert = Alert(
                        alert_id=self._generate_alert_id(),
                        record_id=correlation.get("record_id", ""),
                        severity=rule["severity"],
                        alert_type=rule["type"],
                        title=self._generate_title(rule, signal, correlation),
                        description=self._generate_description(rule, signal, correlation),
                        iocs=list(signal.get("iocs", {}).keys()),
                        cves=[c.get("cve_id") for c in correlation.get("matched_cves", [])],
                        threat_actors=[a.get("name") for a in correlation.get("matched_threat_actors", [])],
                        recommendations=correlation.get("recommendations", []),
                        created_at=datetime.now().isoformat()
                    )
                    alerts.append(alert)
            except Exception as e:
                logger.warning(f"Rule {rule['name']} evaluation failed: {e}")
        
        return alerts
    
    def _generate_title(self, rule: Dict, signal: Dict, correlation: Dict) -> str:
        topic = signal.get("threat_topic", "unknown")
        risk = signal.get("risk_level", "unknown")
        return f"[{rule['severity'].value.upper()}] {rule['type'].replace('_', ' ').title()} - {topic}"
    
    def _generate_description(self, rule: Dict, signal: Dict, correlation: Dict) -> str:
        parts = [correlation.get("threat_summary", "Potential threat detected.")]
        if correlation.get("matched_threat_actors"):
            actors = [a.get("name") for a in correlation["matched_threat_actors"]]
            parts.append(f"Threat actors: {', '.join(actors)}")
        if correlation.get("matched_cves"):
            cves = [c.get("cve_id") for c in correlation["matched_cves"][:5]]
            parts.append(f"CVEs: {', '.join(cves)}")
        return " | ".join(parts)
    
    def generate_alert(self, record_id: str, signal: Dict, entities: List[Dict], correlation: Dict) -> List[Alert]:
        """Generate alerts for a processed record."""
        if not self.enabled:
            return []
        
        # Check minimum threshold
        if signal.get("risk_score", 0) < self.threshold and not correlation.get("matched_threat_actors"):
            return []
        
        return self.evaluate_rules(signal, entities, correlation)
    
    def export_alert(self, alert: Alert) -> str:
        """Export alert in configured format."""
        if self.export_format == "json":
            return self._export_json(alert)
        elif self.export_format == "cef":
            return self._export_cef(alert)
        elif self.export_format == "leef":
            return self._export_leef(alert)
        return self._export_json(alert)
    
    def _export_json(self, alert: Alert) -> str:
        data = {
            "alert_id": alert.alert_id, "record_id": alert.record_id,
            "severity": alert.severity.value, "alert_type": alert.alert_type,
            "title": alert.title, "description": alert.description,
            "iocs": alert.iocs, "cves": alert.cves, "threat_actors": alert.threat_actors,
            "recommendations": alert.recommendations, "created_at": alert.created_at,
            "source": alert.source
        }
        filepath = self.export_path / f"{alert.alert_id}.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        return str(filepath)
    
    def _export_cef(self, alert: Alert) -> str:
        """Export in CEF (Common Event Format) for SIEM."""
        severity_map = {"critical": 10, "high": 8, "medium": 5, "low": 3, "info": 1}
        sev = severity_map.get(alert.severity.value, 1)
        cef = f"CEF:0|DarkWebPipeline|ThreatIntel|1.0|{alert.alert_type}|{alert.title}|{sev}|"
        cef += f"msg={alert.description} src=darkweb cs1={','.join(alert.iocs[:5])} cs2={','.join(alert.cves[:5])}"
        filepath = self.export_path / f"{alert.alert_id}.cef"
        with open(filepath, "w") as f:
            f.write(cef)
        return str(filepath)
    
    def _export_leef(self, alert: Alert) -> str:
        """Export in LEEF (Log Event Extended Format) for QRadar."""
        leef = f"LEEF:1.0|DarkWebPipeline|ThreatIntel|1.0|{alert.alert_type}|"
        leef += f"severity={alert.severity.value}\tmsg={alert.description}\tsrc=darkweb"
        filepath = self.export_path / f"{alert.alert_id}.leef"
        with open(filepath, "w") as f:
            f.write(leef)
        return str(filepath)
    
    def to_dict(self, alert: Alert) -> Dict[str, Any]:
        return {
            "alert_id": alert.alert_id, "record_id": alert.record_id,
            "severity": alert.severity.value, "alert_type": alert.alert_type,
            "title": alert.title, "description": alert.description,
            "created_at": alert.created_at
        }
    
    def get_stats(self) -> Dict[str, Any]:
        return {"enabled": self.enabled, "threshold": self.threshold, "format": self.export_format, "alerts_generated": self._alert_count}
