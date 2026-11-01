"""
Threat Intelligence Feeds Integration for DarkWeb Translation Pipeline
Integrates with external threat feeds (MISP, OTX, NVD) for IOC matching and CVE lookup.
Based on the paper: "correlates the insights extracted from conversations with known threat intelligence"
"""

import json
import logging
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)


@dataclass
class ThreatFeedResult:
    """Result from threat feed lookup."""
    found: bool = False
    source: str = ""
    ioc_type: str = ""
    ioc_value: str = ""
    threat_info: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    severity: str = "unknown"
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    references: List[str] = field(default_factory=list)


@dataclass
class CVEInfo:
    """CVE information from NVD."""
    cve_id: str = ""
    description: str = ""
    severity: str = "unknown"
    cvss_score: float = 0.0
    cvss_vector: str = ""
    published_date: str = ""
    modified_date: str = ""
    affected_products: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    cwe_ids: List[str] = field(default_factory=list)
    has_exploit: bool = False


class ThreatIntelFeeds:
    """
    Threat Intelligence Feeds integration.
    Supports MISP, AlienVault OTX, and NVD.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize threat intel feeds.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        correlation_config = config.get('correlation', {})
        
        self.enabled = correlation_config.get('enable_threat_feeds', False)
        
        # API credentials
        self.misp_url = correlation_config.get('misp_url', '')
        self.misp_key = correlation_config.get('misp_key', '')
        self.otx_key = correlation_config.get('otx_key', '')
        self.nvd_api_key = correlation_config.get('nvd_api_key', '')
        
        # Cache settings
        self.cache_ttl = correlation_config.get('feed_cache_ttl', 3600)  # 1 hour
        self.cache_dir = Path(config.get('paths', {}).get('models_cache', 'models')) / 'threat_cache'
        
        # Initialize caches
        self._ioc_cache: Dict[str, ThreatFeedResult] = {}
        self._cve_cache: Dict[str, CVEInfo] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        # Initialize API clients
        self._misp_client = None
        self._otx_client = None
        
        if self.enabled:
            self._init_clients()
            self._load_cache()
        
        logger.info(f"ThreatIntelFeeds initialized (enabled={self.enabled})")
    
    def _init_clients(self) -> None:
        """Initialize API clients."""
        # MISP client
        if self.misp_url and self.misp_key:
            try:
                from pymisp import PyMISP
                self._misp_client = PyMISP(
                    self.misp_url,
                    self.misp_key,
                    ssl=False
                )
                logger.info("MISP client initialized")
            except ImportError:
                logger.warning("pymisp not installed, MISP integration disabled")
            except Exception as e:
                logger.warning(f"Failed to initialize MISP: {e}")
        
        # OTX client
        if self.otx_key:
            try:
                from OTXv2 import OTXv2
                self._otx_client = OTXv2(self.otx_key)
                logger.info("OTX client initialized")
            except ImportError:
                logger.warning("OTXv2 not installed, OTX integration disabled")
            except Exception as e:
                logger.warning(f"Failed to initialize OTX: {e}")
    
    def _load_cache(self) -> None:
        """Load cached threat data from disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load IOC cache
        ioc_cache_file = self.cache_dir / "ioc_cache.json"
        if ioc_cache_file.exists():
            try:
                with open(ioc_cache_file, 'r') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        self._ioc_cache[key] = ThreatFeedResult(**value)
                logger.info(f"Loaded {len(self._ioc_cache)} cached IOCs")
            except Exception as e:
                logger.warning(f"Failed to load IOC cache: {e}")
        
        # Load CVE cache
        cve_cache_file = self.cache_dir / "cve_cache.json"
        if cve_cache_file.exists():
            try:
                with open(cve_cache_file, 'r') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        self._cve_cache[key] = CVEInfo(**value)
                logger.info(f"Loaded {len(self._cve_cache)} cached CVEs")
            except Exception as e:
                logger.warning(f"Failed to load CVE cache: {e}")
    
    def _save_cache(self) -> None:
        """Save cached threat data to disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Save IOC cache
        try:
            ioc_data = {k: vars(v) for k, v in self._ioc_cache.items()}
            with open(self.cache_dir / "ioc_cache.json", 'w') as f:
                json.dump(ioc_data, f)
        except Exception as e:
            logger.warning(f"Failed to save IOC cache: {e}")
        
        # Save CVE cache
        try:
            cve_data = {k: vars(v) for k, v in self._cve_cache.items()}
            with open(self.cache_dir / "cve_cache.json", 'w') as f:
                json.dump(cve_data, f)
        except Exception as e:
            logger.warning(f"Failed to save CVE cache: {e}")
    
    def _get_cache_key(self, ioc_type: str, ioc_value: str) -> str:
        """Generate cache key for IOC."""
        return hashlib.md5(f"{ioc_type}:{ioc_value}".encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[cache_key] < self.cache_ttl
    
    def _lookup_misp(self, ioc_type: str, ioc_value: str) -> Optional[ThreatFeedResult]:
        """
        Lookup IOC in MISP.
        
        Args:
            ioc_type: Type of IOC (IP, HASH, DOMAIN, etc.)
            ioc_value: IOC value
            
        Returns:
            ThreatFeedResult or None
        """
        if not self._misp_client:
            return None
        
        try:
            # Map our IOC types to MISP types
            misp_type_map = {
                'IP': 'ip-dst',
                'HASH': 'md5',
                'DOMAIN': 'domain',
                'URL': 'url',
                'EMAIL': 'email-src',
            }
            
            misp_type = misp_type_map.get(ioc_type)
            if not misp_type:
                return None
            
            # Search MISP
            results = self._misp_client.search(
                value=ioc_value,
                type_attribute=misp_type
            )
            
            if results and 'response' in results:
                events = results['response']
                if events:
                    event = events[0]['Event']
                    return ThreatFeedResult(
                        found=True,
                        source='MISP',
                        ioc_type=ioc_type,
                        ioc_value=ioc_value,
                        threat_info={
                            'event_id': event.get('id'),
                            'event_info': event.get('info'),
                            'threat_level': event.get('threat_level_id'),
                        },
                        tags=[tag['name'] for tag in event.get('Tag', [])],
                        severity=self._misp_threat_level_to_severity(event.get('threat_level_id')),
                        first_seen=event.get('date'),
                        references=[f"{self.misp_url}/events/view/{event.get('id')}"]
                    )
        except Exception as e:
            logger.warning(f"MISP lookup failed: {e}")
        
        return None
    
    def _misp_threat_level_to_severity(self, threat_level: str) -> str:
        """Convert MISP threat level to severity."""
        mapping = {
            '1': 'critical',
            '2': 'high',
            '3': 'medium',
            '4': 'low',
        }
        return mapping.get(str(threat_level), 'unknown')
    
    def _lookup_otx(self, ioc_type: str, ioc_value: str) -> Optional[ThreatFeedResult]:
        """
        Lookup IOC in AlienVault OTX.
        
        Args:
            ioc_type: Type of IOC
            ioc_value: IOC value
            
        Returns:
            ThreatFeedResult or None
        """
        if not self._otx_client:
            return None
        
        try:
            # Map our IOC types to OTX types
            otx_section_map = {
                'IP': ('IPv4', 'general'),
                'DOMAIN': ('domain', 'general'),
                'HASH': ('file', 'general'),
                'URL': ('url', 'general'),
            }
            
            otx_info = otx_section_map.get(ioc_type)
            if not otx_info:
                return None
            
            indicator_type, section = otx_info
            
            # Query OTX
            result = self._otx_client.get_indicator_details_by_section(
                indicator_type,
                ioc_value,
                section
            )
            
            if result:
                pulse_count = result.get('pulse_info', {}).get('count', 0)
                if pulse_count > 0:
                    pulses = result.get('pulse_info', {}).get('pulses', [])
                    tags = []
                    for pulse in pulses[:5]:  # Get tags from first 5 pulses
                        tags.extend(pulse.get('tags', []))
                    
                    return ThreatFeedResult(
                        found=True,
                        source='OTX',
                        ioc_type=ioc_type,
                        ioc_value=ioc_value,
                        threat_info={
                            'pulse_count': pulse_count,
                            'pulses': [p.get('name') for p in pulses[:5]],
                        },
                        tags=list(set(tags))[:20],
                        severity=self._otx_pulse_count_to_severity(pulse_count),
                        references=[f"https://otx.alienvault.com/indicator/{indicator_type}/{ioc_value}"]
                    )
        except Exception as e:
            logger.warning(f"OTX lookup failed: {e}")
        
        return None
    
    def _otx_pulse_count_to_severity(self, count: int) -> str:
        """Convert OTX pulse count to severity."""
        if count >= 10:
            return 'critical'
        elif count >= 5:
            return 'high'
        elif count >= 2:
            return 'medium'
        elif count >= 1:
            return 'low'
        return 'unknown'
    
    def _lookup_nvd(self, cve_id: str) -> Optional[CVEInfo]:
        """
        Lookup CVE in NVD.
        
        Args:
            cve_id: CVE identifier (e.g., CVE-2021-44228)
            
        Returns:
            CVEInfo or None
        """
        try:
            import requests
            
            # NVD API 2.0 endpoint
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0"
            params = {'cveId': cve_id}
            
            headers = {}
            if self.nvd_api_key:
                headers['apiKey'] = self.nvd_api_key
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                vulnerabilities = data.get('vulnerabilities', [])
                
                if vulnerabilities:
                    vuln = vulnerabilities[0]['cve']
                    
                    # Extract CVSS score
                    cvss_score = 0.0
                    cvss_vector = ""
                    severity = "unknown"
                    
                    metrics = vuln.get('metrics', {})
                    if 'cvssMetricV31' in metrics:
                        cvss_data = metrics['cvssMetricV31'][0]['cvssData']
                        cvss_score = cvss_data.get('baseScore', 0)
                        cvss_vector = cvss_data.get('vectorString', '')
                        severity = cvss_data.get('baseSeverity', 'UNKNOWN').lower()
                    elif 'cvssMetricV2' in metrics:
                        cvss_data = metrics['cvssMetricV2'][0]['cvssData']
                        cvss_score = cvss_data.get('baseScore', 0)
                        cvss_vector = cvss_data.get('vectorString', '')
                    
                    # Extract descriptions
                    descriptions = vuln.get('descriptions', [])
                    description = ""
                    for desc in descriptions:
                        if desc.get('lang') == 'en':
                            description = desc.get('value', '')
                            break
                    
                    # Extract CWEs
                    cwe_ids = []
                    weaknesses = vuln.get('weaknesses', [])
                    for weakness in weaknesses:
                        for desc in weakness.get('description', []):
                            if desc.get('value', '').startswith('CWE-'):
                                cwe_ids.append(desc['value'])
                    
                    # Extract references
                    refs = vuln.get('references', [])
                    references = [ref.get('url') for ref in refs[:10]]
                    
                    # Check for exploit
                    has_exploit = any(
                        'exploit' in ref.get('tags', [])
                        for ref in refs
                    )
                    
                    return CVEInfo(
                        cve_id=cve_id,
                        description=description,
                        severity=severity,
                        cvss_score=cvss_score,
                        cvss_vector=cvss_vector,
                        published_date=vuln.get('published', ''),
                        modified_date=vuln.get('lastModified', ''),
                        references=references,
                        cwe_ids=cwe_ids,
                        has_exploit=has_exploit
                    )
        except ImportError:
            logger.warning("requests library not available for NVD lookup")
        except Exception as e:
            logger.warning(f"NVD lookup failed: {e}")
        
        return None
    
    def lookup_ioc(self, ioc_type: str, ioc_value: str) -> ThreatFeedResult:
        """
        Lookup IOC across all configured threat feeds.
        
        Args:
            ioc_type: Type of IOC (IP, HASH, DOMAIN, URL, EMAIL)
            ioc_value: IOC value
            
        Returns:
            ThreatFeedResult with combined information
        """
        if not self.enabled:
            return ThreatFeedResult(ioc_type=ioc_type, ioc_value=ioc_value)
        
        # Check cache
        cache_key = self._get_cache_key(ioc_type, ioc_value)
        if cache_key in self._ioc_cache and self._is_cache_valid(cache_key):
            return self._ioc_cache[cache_key]
        
        # Try each feed
        result = None
        
        # Try MISP first
        result = self._lookup_misp(ioc_type, ioc_value)
        
        # Try OTX if MISP didn't find it
        if not result or not result.found:
            otx_result = self._lookup_otx(ioc_type, ioc_value)
            if otx_result and otx_result.found:
                result = otx_result
        
        # Default result if nothing found
        if not result:
            result = ThreatFeedResult(
                found=False,
                ioc_type=ioc_type,
                ioc_value=ioc_value
            )
        
        # Cache result
        self._ioc_cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()
        
        return result
    
    def lookup_cve(self, cve_id: str) -> CVEInfo:
        """
        Lookup CVE information.
        
        Args:
            cve_id: CVE identifier
            
        Returns:
            CVEInfo with vulnerability details
        """
        if not self.enabled:
            return CVEInfo(cve_id=cve_id)
        
        # Normalize CVE ID
        cve_id = cve_id.upper()
        if not re.match(r'^CVE-\d{4}-\d{4,}$', cve_id):
            return CVEInfo(cve_id=cve_id)
        
        # Check cache
        if cve_id in self._cve_cache and self._is_cache_valid(cve_id):
            return self._cve_cache[cve_id]
        
        # Lookup in NVD
        result = self._lookup_nvd(cve_id)
        
        if not result:
            result = CVEInfo(cve_id=cve_id)
        
        # Cache result
        self._cve_cache[cve_id] = result
        self._cache_timestamps[cve_id] = time.time()
        
        return result
    
    def lookup_iocs_batch(
        self,
        iocs: Dict[str, List[str]]
    ) -> Dict[str, List[ThreatFeedResult]]:
        """
        Lookup multiple IOCs.
        
        Args:
            iocs: Dictionary of ioc_type -> list of values
            
        Returns:
            Dictionary of ioc_type -> list of results
        """
        results = {}
        
        for ioc_type, values in iocs.items():
            results[ioc_type] = []
            for value in values:
                result = self.lookup_ioc(ioc_type, value)
                results[ioc_type].append(result)
                
                # Rate limiting
                time.sleep(0.1)
        
        return results
    
    def lookup_cves_batch(self, cve_ids: List[str]) -> List[CVEInfo]:
        """
        Lookup multiple CVEs.
        
        Args:
            cve_ids: List of CVE identifiers
            
        Returns:
            List of CVEInfo objects
        """
        results = []
        
        for cve_id in cve_ids:
            result = self.lookup_cve(cve_id)
            results.append(result)
            
            # Rate limiting (NVD has strict limits)
            time.sleep(0.6 if not self.nvd_api_key else 0.1)
        
        return results
    
    def get_known_threats(
        self,
        iocs: Dict[str, List[str]]
    ) -> List[ThreatFeedResult]:
        """
        Get only IOCs that are known threats.
        
        Args:
            iocs: Dictionary of ioc_type -> list of values
            
        Returns:
            List of ThreatFeedResults for known threats
        """
        known_threats = []
        
        results = self.lookup_iocs_batch(iocs)
        for ioc_type, feed_results in results.items():
            for result in feed_results:
                if result.found:
                    known_threats.append(result)
        
        return known_threats
    
    def to_dict(self, result: ThreatFeedResult) -> Dict[str, Any]:
        """Convert ThreatFeedResult to dictionary."""
        return {
            'found': result.found,
            'source': result.source,
            'ioc_type': result.ioc_type,
            'ioc_value': result.ioc_value,
            'threat_info': result.threat_info,
            'tags': result.tags,
            'severity': result.severity,
            'first_seen': result.first_seen,
            'last_seen': result.last_seen,
            'references': result.references,
        }
    
    def cve_to_dict(self, cve_info: CVEInfo) -> Dict[str, Any]:
        """Convert CVEInfo to dictionary."""
        return {
            'cve_id': cve_info.cve_id,
            'description': cve_info.description,
            'severity': cve_info.severity,
            'cvss_score': cve_info.cvss_score,
            'cvss_vector': cve_info.cvss_vector,
            'published_date': cve_info.published_date,
            'modified_date': cve_info.modified_date,
            'affected_products': cve_info.affected_products,
            'references': cve_info.references,
            'cwe_ids': cve_info.cwe_ids,
            'has_exploit': cve_info.has_exploit,
        }
    
    def cleanup(self) -> None:
        """Save cache and cleanup."""
        self._save_cache()
        logger.info("ThreatIntelFeeds cleaned up")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get feed statistics."""
        return {
            'enabled': self.enabled,
            'misp_configured': bool(self.misp_url and self.misp_key),
            'otx_configured': bool(self.otx_key),
            'nvd_configured': True,  # NVD doesn't require key
            'ioc_cache_size': len(self._ioc_cache),
            'cve_cache_size': len(self._cve_cache),
        }
