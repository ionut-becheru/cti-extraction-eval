"""
Correlation Engine for DarkWeb Translation Pipeline
Links extracted IOCs/CVEs to known threats, maps threat actor aliases to profiles,
and performs temporal correlation with real-world events.
Based on the paper: "maps detected keywords, entities, or patterns from the Processing Layer 
to known vulnerabilities, exploits, or past cyber incidents"
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """Result from correlation analysis."""
    record_id: str = ""
    correlation_score: float = 0.0
    
    # Correlated threats
    matched_cves: List[Dict] = field(default_factory=list)
    matched_iocs: List[Dict] = field(default_factory=list)
    matched_threat_actors: List[Dict] = field(default_factory=list)
    matched_campaigns: List[Dict] = field(default_factory=list)
    
    # Temporal correlations
    temporal_matches: List[Dict] = field(default_factory=list)
    
    # Graph relationships
    related_records: List[str] = field(default_factory=list)
    
    # Summary
    threat_summary: str = ""
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ThreatActorProfile:
    """Threat actor profile."""
    name: str
    aliases: List[str] = field(default_factory=list)
    country: str = ""
    motivation: str = ""  # financial, espionage, hacktivism
    targets: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    techniques: List[str] = field(default_factory=list)
    campaigns: List[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""
    references: List[str] = field(default_factory=list)


class CorrelationEngine:
    """
    Correlation Engine for linking extracted intelligence to known threats.
    """
    
    # Known threat actor profiles (subset - would be loaded from external source)
    THREAT_ACTOR_PROFILES = {
        'apt28': ThreatActorProfile(
            name='APT28',
            aliases=['Fancy Bear', 'Sofacy', 'Sednit', 'STRONTIUM', 'Forest Blizzard'],
            country='Russia',
            motivation='espionage',
            targets=['government', 'military', 'defense', 'media'],
            tools=['X-Agent', 'X-Tunnel', 'Zebrocy', 'LoJax'],
            techniques=['T1566', 'T1190', 'T1078', 'T1003'],
        ),
        'apt29': ThreatActorProfile(
            name='APT29',
            aliases=['Cozy Bear', 'The Dukes', 'NOBELIUM', 'Midnight Blizzard'],
            country='Russia',
            motivation='espionage',
            targets=['government', 'think tanks', 'healthcare'],
            tools=['WellMess', 'WellMail', 'SUNBURST', 'TEARDROP'],
            techniques=['T1195', 'T1059', 'T1071'],
        ),
        'lazarus': ThreatActorProfile(
            name='Lazarus Group',
            aliases=['Hidden Cobra', 'ZINC', 'Labyrinth Chollima', 'APT38'],
            country='North Korea',
            motivation='financial',
            targets=['financial', 'cryptocurrency', 'defense'],
            tools=['FALLCHILL', 'HARDRAIN', 'HOPLIGHT', 'AppleJeus'],
            techniques=['T1566', 'T1190', 'T1059'],
        ),
        'fin7': ThreatActorProfile(
            name='FIN7',
            aliases=['Carbanak', 'Navigator', 'Carbon Spider'],
            country='Unknown',
            motivation='financial',
            targets=['retail', 'hospitality', 'restaurant'],
            tools=['Carbanak', 'GRIFFON', 'HALFBAKED', 'BELLHOP'],
            techniques=['T1566', 'T1059', 'T1055'],
        ),
        'lockbit': ThreatActorProfile(
            name='LockBit',
            aliases=['LockBit Gang', 'LockBit 2.0', 'LockBit 3.0', 'LockBit Black'],
            country='Unknown',
            motivation='financial',
            targets=['enterprise', 'healthcare', 'government'],
            tools=['LockBit ransomware', 'StealBit'],
            techniques=['T1486', 'T1490', 'T1027'],
        ),
        'conti': ThreatActorProfile(
            name='Conti',
            aliases=['Conti Gang', 'Wizard Spider'],
            country='Russia',
            motivation='financial',
            targets=['enterprise', 'healthcare', 'government'],
            tools=['Conti ransomware', 'BazarLoader', 'TrickBot'],
            techniques=['T1486', 'T1490', 'T1059'],
        ),
    }
    
    # Campaign patterns (simplified - would be loaded from threat intel)
    KNOWN_CAMPAIGNS = {
        'solarwinds': {
            'name': 'SolarWinds Supply Chain Attack',
            'actors': ['APT29'],
            'cves': ['CVE-2020-10148'],
            'iocs_patterns': ['solarwinds', 'orion', 'sunburst'],
            'timeframe': ('2020-03-01', '2020-12-31'),
        },
        'log4shell': {
            'name': 'Log4Shell Exploitation',
            'actors': [],
            'cves': ['CVE-2021-44228', 'CVE-2021-45046', 'CVE-2021-45105'],
            'iocs_patterns': ['log4j', 'jndi', 'ldap://'],
            'timeframe': ('2021-12-09', '2022-06-30'),
        },
        'exchange_proxylogon': {
            'name': 'Microsoft Exchange ProxyLogon',
            'actors': ['HAFNIUM'],
            'cves': ['CVE-2021-26855', 'CVE-2021-26857', 'CVE-2021-26858', 'CVE-2021-27065'],
            'iocs_patterns': ['proxylogon', 'exchange', 'webshell'],
            'timeframe': ('2021-01-01', '2021-06-30'),
        },
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the correlation engine.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        correlation_config = config.get('correlation', {})
        
        self.enabled = correlation_config.get('enable_correlation', False)
        self.correlation_threshold = correlation_config.get('correlation_threshold', 0.7)
        
        # Storage for correlation graph
        self._ioc_to_records: Dict[str, Set[str]] = defaultdict(set)
        self._cve_to_records: Dict[str, Set[str]] = defaultdict(set)
        self._actor_to_records: Dict[str, Set[str]] = defaultdict(set)
        self._record_graph: Dict[str, Set[str]] = defaultdict(set)

        # Temporal mention tracking. Map: entity_key -> {iso_week -> count}.
        # iso_week is the ISO 8601 year-week tuple, joined as "YYYY-Www".
        # The temporal signal fires when the current week's count exceeds
        # `temporal_spike_factor` x the moving average over the previous
        # `temporal_window_weeks`. Window length and factor are configurable.
        self._weekly_mentions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.temporal_window_weeks = correlation_config.get('temporal_window_weeks', 4)
        self.temporal_spike_factor = correlation_config.get('temporal_spike_factor', 3.0)
        self.temporal_min_baseline = correlation_config.get('temporal_min_baseline', 2)
        
        # Build threat actor alias index
        self._alias_to_actor: Dict[str, str] = {}
        for actor_id, profile in self.THREAT_ACTOR_PROFILES.items():
            self._alias_to_actor[profile.name.lower()] = actor_id
            for alias in profile.aliases:
                self._alias_to_actor[alias.lower()] = actor_id
        
        logger.info(f"CorrelationEngine initialized (enabled={self.enabled})")
    
    def _match_threat_actors(
        self,
        entities: List[Dict],
        text: str
    ) -> List[Dict]:
        """
        Match threat actors from entities and text.
        
        Args:
            entities: Extracted entities
            text: Full text for additional matching
            
        Returns:
            List of matched threat actor profiles
        """
        matched = []
        matched_ids = set()
        
        # Check entities
        for entity in entities:
            if entity.get('label') == 'THREAT_ACTOR':
                name = entity.get('text', '').lower()
                if name in self._alias_to_actor:
                    actor_id = self._alias_to_actor[name]
                    if actor_id not in matched_ids:
                        profile = self.THREAT_ACTOR_PROFILES[actor_id]
                        matched.append({
                            'id': actor_id,
                            'name': profile.name,
                            'match_type': 'entity',
                            'matched_text': entity.get('text'),
                            'profile': vars(profile)
                        })
                        matched_ids.add(actor_id)
        
        # Check text for aliases
        text_lower = text.lower()
        for alias, actor_id in self._alias_to_actor.items():
            if actor_id not in matched_ids:
                if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                    profile = self.THREAT_ACTOR_PROFILES[actor_id]
                    matched.append({
                        'id': actor_id,
                        'name': profile.name,
                        'match_type': 'text',
                        'matched_text': alias,
                        'profile': vars(profile)
                    })
                    matched_ids.add(actor_id)
        
        return matched
    
    def _match_campaigns(
        self,
        cves: List[str],
        text: str
    ) -> List[Dict]:
        """
        Match known campaigns from CVEs and text patterns.
        
        Args:
            cves: List of CVE IDs
            text: Full text
            
        Returns:
            List of matched campaigns
        """
        matched = []
        text_lower = text.lower()
        
        for campaign_id, campaign in self.KNOWN_CAMPAIGNS.items():
            score = 0.0
            matched_cves = []
            matched_patterns = []
            
            # Check CVEs
            for cve in cves:
                if cve.upper() in [c.upper() for c in campaign['cves']]:
                    score += 0.5
                    matched_cves.append(cve)
            
            # Check patterns
            for pattern in campaign['iocs_patterns']:
                if pattern.lower() in text_lower:
                    score += 0.25
                    matched_patterns.append(pattern)
            
            if score >= 0.5:
                matched.append({
                    'id': campaign_id,
                    'name': campaign['name'],
                    'score': min(score, 1.0),
                    'matched_cves': matched_cves,
                    'matched_patterns': matched_patterns,
                    'actors': campaign['actors'],
                    'timeframe': campaign['timeframe'],
                })
        
        return matched
    
    def _calculate_correlation_score(
        self,
        matched_cves: List[Dict],
        matched_iocs: List[Dict],
        matched_actors: List[Dict],
        matched_campaigns: List[Dict]
    ) -> float:
        """
        Calculate overall correlation score.
        
        Args:
            matched_cves: CVE matches
            matched_iocs: IOC matches
            matched_actors: Threat actor matches
            matched_campaigns: Campaign matches
            
        Returns:
            Correlation score between 0 and 1
        """
        score = 0.0
        
        # CVE matches (high value)
        cve_score = min(len(matched_cves) * 0.2, 0.4)
        
        # IOC matches (medium value)
        ioc_score = min(len(matched_iocs) * 0.1, 0.3)
        
        # Threat actor matches (high value)
        actor_score = min(len(matched_actors) * 0.15, 0.3)
        
        # Campaign matches (very high value)
        campaign_score = min(len(matched_campaigns) * 0.3, 0.5)
        
        score = min(cve_score + ioc_score + actor_score + campaign_score, 1.0)
        
        return score
    
    def _generate_summary(
        self,
        matched_cves: List[Dict],
        matched_iocs: List[Dict],
        matched_actors: List[Dict],
        matched_campaigns: List[Dict]
    ) -> str:
        """Generate threat summary."""
        parts = []
        
        if matched_campaigns:
            campaign_names = [c['name'] for c in matched_campaigns]
            parts.append(f"Potentially related to campaigns: {', '.join(campaign_names)}.")
        
        if matched_actors:
            actor_names = [a['name'] for a in matched_actors]
            parts.append(f"Threat actors identified: {', '.join(actor_names)}.")
        
        if matched_cves:
            cve_ids = [c.get('cve_id', 'unknown') for c in matched_cves[:5]]
            parts.append(f"CVEs mentioned: {', '.join(cve_ids)}.")
        
        if matched_iocs:
            ioc_count = len(matched_iocs)
            known_count = sum(1 for i in matched_iocs if i.get('found'))
            parts.append(f"IOCs extracted: {ioc_count} ({known_count} known malicious).")
        
        return ' '.join(parts) if parts else "No significant correlations found."
    
    def _generate_recommendations(
        self,
        correlation_score: float,
        matched_cves: List[Dict],
        matched_actors: List[Dict],
        matched_campaigns: List[Dict]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if correlation_score >= 0.8:
            recommendations.append("HIGH PRIORITY: Immediate investigation recommended.")
        
        if matched_cves:
            high_severity = [c for c in matched_cves if c.get('severity') in ['critical', 'high']]
            if high_severity:
                recommendations.append(f"Patch {len(high_severity)} critical/high severity vulnerabilities immediately.")
        
        if matched_actors:
            recommendations.append("Review threat actor TTPs and update detection rules.")
            for actor in matched_actors:
                profile = actor.get('profile', {})
                techniques = profile.get('techniques', [])
                if techniques:
                    recommendations.append(f"Monitor for MITRE ATT&CK techniques: {', '.join(techniques[:5])}")
        
        if matched_campaigns:
            recommendations.append("Check for related IOCs in your environment.")
        
        if not recommendations:
            recommendations.append("Continue monitoring for additional context.")
        
        return recommendations
    
    def correlate(
        self,
        record_id: str,
        text: str,
        entities: List[Dict],
        iocs: Dict[str, List[str]],
        cve_info: Optional[List[Dict]] = None,
        ioc_feed_results: Optional[List[Dict]] = None
    ) -> CorrelationResult:
        """
        Perform correlation analysis on a record.
        
        Args:
            record_id: Unique record identifier
            text: Full text content
            entities: Extracted entities
            iocs: Extracted IOCs
            cve_info: CVE information from NVD
            ioc_feed_results: IOC lookup results from threat feeds
            
        Returns:
            CorrelationResult with all correlations
        """
        if not self.enabled:
            return CorrelationResult(record_id=record_id)
        
        # Match threat actors
        matched_actors = self._match_threat_actors(entities, text)
        
        # Get CVE list
        cve_list = iocs.get('CVE', [])
        for entity in entities:
            if entity.get('label') == 'CVE':
                cve = entity.get('text', '').upper()
                if cve not in cve_list:
                    cve_list.append(cve)
        
        # Match campaigns
        matched_campaigns = self._match_campaigns(cve_list, text)
        
        # Process CVE info
        matched_cves = cve_info or []
        
        # Process IOC feed results
        matched_iocs = ioc_feed_results or []
        
        # Calculate correlation score
        correlation_score = self._calculate_correlation_score(
            matched_cves, matched_iocs, matched_actors, matched_campaigns
        )
        
        # Update correlation graph
        self._update_graph(record_id, entities, iocs, matched_actors)

        # Record this mention against weekly bins and look for spikes.
        self._record_temporal_mentions(matched_actors, matched_campaigns, cve_list)
        temporal_matches = self._compute_temporal_signal(
            matched_actors, matched_campaigns, cve_list
        )

        # Find related records
        related_records = list(self._record_graph.get(record_id, set()))

        # Generate summary and recommendations
        threat_summary = self._generate_summary(
            matched_cves, matched_iocs, matched_actors, matched_campaigns
        )
        recommendations = self._generate_recommendations(
            correlation_score, matched_cves, matched_actors, matched_campaigns
        )

        return CorrelationResult(
            record_id=record_id,
            correlation_score=correlation_score,
            matched_cves=matched_cves,
            matched_iocs=matched_iocs,
            matched_threat_actors=matched_actors,
            matched_campaigns=matched_campaigns,
            temporal_matches=temporal_matches,
            related_records=related_records,
            threat_summary=threat_summary,
            recommendations=recommendations
        )
    
    def _update_graph(
        self,
        record_id: str,
        entities: List[Dict],
        iocs: Dict[str, List[str]],
        matched_actors: List[Dict]
    ) -> None:
        """Update the correlation graph with new record data."""
        # Index by IOCs
        for ioc_type, values in iocs.items():
            for value in values:
                key = f"{ioc_type}:{value}"
                # Link to other records with same IOC
                for other_record in self._ioc_to_records[key]:
                    if other_record != record_id:
                        self._record_graph[record_id].add(other_record)
                        self._record_graph[other_record].add(record_id)
                self._ioc_to_records[key].add(record_id)
        
        # Index by CVEs
        for entity in entities:
            if entity.get('label') == 'CVE':
                cve = entity.get('text', '').upper()
                for other_record in self._cve_to_records[cve]:
                    if other_record != record_id:
                        self._record_graph[record_id].add(other_record)
                        self._record_graph[other_record].add(record_id)
                self._cve_to_records[cve].add(record_id)
        
        # Index by threat actors
        for actor in matched_actors:
            actor_id = actor.get('id')
            for other_record in self._actor_to_records[actor_id]:
                if other_record != record_id:
                    self._record_graph[record_id].add(other_record)
                    self._record_graph[other_record].add(record_id)
            self._actor_to_records[actor_id].add(record_id)
    
    @staticmethod
    def _iso_week_key(when: Optional[datetime] = None) -> str:
        """Return an 'YYYY-Www' string for the given datetime (default: now)."""
        when = when or datetime.utcnow()
        year, week, _ = when.isocalendar()
        return f"{year}-W{week:02d}"

    def _record_temporal_mentions(self, matched_actors, matched_campaigns, cve_list) -> None:
        """Increment weekly counters for any matched actor / campaign / CVE."""
        week = self._iso_week_key()
        for actor in matched_actors or []:
            key = f"actor:{actor.get('id') or actor.get('name') or '?'}"
            self._weekly_mentions[key][week] += 1
        for camp in matched_campaigns or []:
            key = f"campaign:{camp.get('id') or camp.get('name') or '?'}"
            self._weekly_mentions[key][week] += 1
        for cve in cve_list or []:
            key = f"cve:{cve.upper()}"
            self._weekly_mentions[key][week] += 1

    def _compute_temporal_signal(self, matched_actors, matched_campaigns, cve_list) -> List[Dict]:
        """Flag entities whose current-week mention count exceeds the spike threshold.

        For each matched entity (actor / campaign / CVE), compare this week's
        mention count to the moving average of the previous `temporal_window_weeks`
        weeks. Emit a temporal_match record when count > spike_factor * baseline
        and the baseline meets a minimum count to avoid noisy spikes off zero.
        """
        now = datetime.utcnow()
        current_week = self._iso_week_key(now)
        prev_weeks = []
        for k in range(1, self.temporal_window_weeks + 1):
            prev_dt = now - timedelta(weeks=k)
            prev_weeks.append(self._iso_week_key(prev_dt))

        results = []
        targets = []
        for actor in matched_actors or []:
            targets.append(('actor', actor.get('id') or actor.get('name'), actor))
        for camp in matched_campaigns or []:
            targets.append(('campaign', camp.get('id') or camp.get('name'), camp))
        for cve in cve_list or []:
            targets.append(('cve', cve.upper(), {'cve_id': cve.upper()}))

        for kind, ident, payload in targets:
            if not ident:
                continue
            key = f"{kind}:{ident}"
            bins = self._weekly_mentions.get(key, {})
            current_count = bins.get(current_week, 0)
            prev_total = sum(bins.get(w, 0) for w in prev_weeks)
            baseline = prev_total / max(self.temporal_window_weeks, 1)
            if (baseline >= self.temporal_min_baseline
                    and current_count > self.temporal_spike_factor * baseline):
                results.append({
                    'kind': kind,
                    'id': ident,
                    'current_week': current_week,
                    'current_count': current_count,
                    'baseline_avg': baseline,
                    'spike_factor': current_count / baseline if baseline else float('inf'),
                    'payload': payload,
                })
        return results

    def get_related_records(self, record_id: str) -> List[str]:
        """Get records related to a given record."""
        return list(self._record_graph.get(record_id, set()))
    
    def get_records_by_ioc(self, ioc_type: str, ioc_value: str) -> List[str]:
        """Get records containing a specific IOC."""
        key = f"{ioc_type}:{ioc_value}"
        return list(self._ioc_to_records.get(key, set()))
    
    def get_records_by_cve(self, cve_id: str) -> List[str]:
        """Get records mentioning a specific CVE."""
        return list(self._cve_to_records.get(cve_id.upper(), set()))
    
    def get_records_by_actor(self, actor_name: str) -> List[str]:
        """Get records mentioning a specific threat actor."""
        actor_id = self._alias_to_actor.get(actor_name.lower())
        if actor_id:
            return list(self._actor_to_records.get(actor_id, set()))
        return []
    
    def to_dict(self, result: CorrelationResult) -> Dict[str, Any]:
        """Convert CorrelationResult to dictionary."""
        return {
            'record_id': result.record_id,
            'correlation_score': result.correlation_score,
            'matched_cves': result.matched_cves,
            'matched_iocs': result.matched_iocs,
            'matched_threat_actors': result.matched_threat_actors,
            'matched_campaigns': result.matched_campaigns,
            'temporal_matches': result.temporal_matches,
            'related_records': result.related_records,
            'threat_summary': result.threat_summary,
            'recommendations': result.recommendations,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get correlation engine statistics."""
        return {
            'enabled': self.enabled,
            'correlation_threshold': self.correlation_threshold,
            'indexed_iocs': len(self._ioc_to_records),
            'indexed_cves': len(self._cve_to_records),
            'indexed_actors': len(self._actor_to_records),
            'graph_nodes': len(self._record_graph),
            'known_actors': len(self.THREAT_ACTOR_PROFILES),
            'known_campaigns': len(self.KNOWN_CAMPAIGNS),
        }
