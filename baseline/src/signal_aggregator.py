"""
Signal Aggregator for DarkWeb Translation Pipeline
Combines signals from keyword filter, ML classifier, and NER to calculate
final relevance/risk scores and prioritize records for the correlation layer.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classification."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AggregatedSignal:
    """Represents aggregated signals for a record."""
    relevance_score: float = 0.0
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.INFO
    threat_topic: str = "unknown"
    is_actionable: bool = False
    
    # Individual signal scores
    keyword_score: float = 0.0
    classifier_score: float = 0.0
    ner_score: float = 0.0
    
    # Extracted data
    entities: List[Dict] = field(default_factory=list)
    iocs: Dict[str, List[str]] = field(default_factory=dict)
    
    # Metadata
    signals_used: List[str] = field(default_factory=list)
    confidence: float = 0.0


class SignalAggregator:
    """
    Aggregates signals from multiple NLP components to calculate
    final relevance and risk scores.
    """
    
    # Entity type weights for risk scoring
    ENTITY_RISK_WEIGHTS = {
        'CVE': 0.9,
        'MALWARE': 0.85,
        'THREAT_ACTOR': 0.8,
        'HASH': 0.75,
        'IP': 0.7,
        'DOMAIN': 0.65,
        'URL': 0.6,
        'CRYPTO_WALLET': 0.7,
        'TOOL': 0.5,
        'EMAIL': 0.4,
        'PORT': 0.3,
        'FILEPATH': 0.3,
    }
    
    # Topic risk weights
    TOPIC_RISK_WEIGHTS = {
        'attack_planning': 1.0,
        'vulnerability_exploit': 0.95,
        'ransomware': 0.9,
        'data_breach': 0.85,
        'malware_analysis': 0.8,
        'credential_trading': 0.75,
        'tool_trading': 0.7,
        'ddos': 0.7,
        'phishing': 0.65,
        'general_security': 0.3,
        'non_threat': 0.0,
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the signal aggregator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        nlp_config = config.get('nlp', {})
        
        self.enabled = nlp_config.get('enable_signal_aggregator', False)
        
        # Signal weights (should sum to 1.0)
        self.keyword_weight = nlp_config.get('keyword_weight', 0.3)
        self.classifier_weight = nlp_config.get('classifier_weight', 0.4)
        self.ner_weight = nlp_config.get('ner_weight', 0.3)
        
        # Thresholds
        self.risk_threshold = nlp_config.get('risk_threshold', 0.6)
        self.actionable_threshold = nlp_config.get('actionable_threshold', 0.7)
        
        # Risk level thresholds
        self.risk_thresholds = {
            RiskLevel.CRITICAL: 0.9,
            RiskLevel.HIGH: 0.7,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.LOW: 0.3,
            RiskLevel.INFO: 0.0,
        }
        
        logger.info(f"SignalAggregator initialized (enabled={self.enabled})")
    
    def _calculate_keyword_score(self, keyword_data: Dict[str, Any]) -> float:
        """
        Calculate score from keyword filter results.
        
        Args:
            keyword_data: Results from RelevanceFilter
            
        Returns:
            Score between 0 and 1
        """
        if not keyword_data:
            return 0.0
        
        # Use keyword count normalized
        keyword_count = keyword_data.get('keyword_count', 0)
        is_relevant = keyword_data.get('is_relevant', False)
        
        if not is_relevant:
            return 0.0
        
        # Normalize: 5+ keywords = max score
        return min(keyword_count / 5.0, 1.0)
    
    def _calculate_classifier_score(self, classifier_data: Dict[str, Any]) -> float:
        """
        Calculate score from threat classifier results.
        
        Args:
            classifier_data: Results from ThreatClassifier
            
        Returns:
            Score between 0 and 1
        """
        if not classifier_data:
            return 0.0
        
        confidence = classifier_data.get('confidence', 0.0)
        topic = classifier_data.get('topic', 'non_threat')
        is_threat = classifier_data.get('is_threat', False)
        
        if not is_threat:
            return 0.0
        
        # Weight by topic importance
        topic_weight = self.TOPIC_RISK_WEIGHTS.get(topic, 0.5)
        
        return confidence * topic_weight
    
    def _calculate_ner_score(self, entities: List[Dict]) -> float:
        """
        Calculate score from NER results.
        
        Args:
            entities: List of extracted entities
            
        Returns:
            Score between 0 and 1
        """
        if not entities:
            return 0.0
        
        # Calculate weighted sum of entity types
        total_weight = 0.0
        seen_types = set()
        
        for entity in entities:
            entity_type = entity.get('label', 'UNKNOWN')
            if entity_type not in seen_types:
                weight = self.ENTITY_RISK_WEIGHTS.get(entity_type, 0.3)
                total_weight += weight
                seen_types.add(entity_type)
        
        # Normalize: having 5+ different high-value entity types = max score
        return min(total_weight / 3.0, 1.0)
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """
        Determine risk level from score.
        
        Args:
            risk_score: Risk score between 0 and 1
            
        Returns:
            RiskLevel enum value
        """
        for level, threshold in sorted(
            self.risk_thresholds.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if risk_score >= threshold:
                return level
        return RiskLevel.INFO
    
    def _extract_iocs(self, entities: List[Dict]) -> Dict[str, List[str]]:
        """
        Extract IOCs from entities.
        
        Args:
            entities: List of entities
            
        Returns:
            Dictionary of IOC type -> values
        """
        ioc_types = {'IP', 'HASH', 'DOMAIN', 'URL', 'EMAIL', 'CRYPTO_WALLET', 'CVE'}
        iocs = {}
        
        for entity in entities:
            label = entity.get('label')
            if label in ioc_types:
                if label not in iocs:
                    iocs[label] = []
                text = entity.get('text')
                if text and text not in iocs[label]:
                    iocs[label].append(text)
        
        return iocs
    
    def aggregate(
        self,
        keyword_data: Optional[Dict[str, Any]] = None,
        classifier_data: Optional[Dict[str, Any]] = None,
        entities: Optional[List[Dict]] = None
    ) -> AggregatedSignal:
        """
        Aggregate signals from all NLP components.
        
        Args:
            keyword_data: Results from RelevanceFilter
            classifier_data: Results from ThreatClassifier
            entities: Results from CybersecNER
            
        Returns:
            AggregatedSignal with combined scores
        """
        if not self.enabled:
            return AggregatedSignal()
        
        signals_used = []
        
        # Calculate individual scores
        keyword_score = self._calculate_keyword_score(keyword_data or {})
        if keyword_data:
            signals_used.append('keyword_filter')
        
        classifier_score = self._calculate_classifier_score(classifier_data or {})
        if classifier_data:
            signals_used.append('threat_classifier')
        
        ner_score = self._calculate_ner_score(entities or [])
        if entities:
            signals_used.append('cybersec_ner')
        
        # Calculate weighted relevance score
        relevance_score = (
            self.keyword_weight * keyword_score +
            self.classifier_weight * classifier_score +
            self.ner_weight * ner_score
        )
        
        # Risk score considers both relevance and entity severity.
        # Use an additive, count-scaled boost rather than a flat 1.2x multiplier:
        # the multiplicative form silently became a no-op for already-high relevance
        # scores after the [0,1] clamp, masking the very records that should rank
        # highest. Additive form preserves differentiation at the top.
        risk_score = relevance_score
        if entities:
            high_severity_entities = [
                e for e in entities
                if e.get('label') in ['CVE', 'MALWARE', 'THREAT_ACTOR', 'HASH']
            ]
            if high_severity_entities:
                # 0.15 per high-severity entity type, capped at 0.30 total boost
                boost = min(0.15 * len(set(e.get('label') for e in high_severity_entities)), 0.30)
                risk_score = min(risk_score + boost, 1.0)
        
        # Determine risk level and actionability
        risk_level = self._determine_risk_level(risk_score)
        is_actionable = risk_score >= self.actionable_threshold
        
        # Get threat topic from classifier
        threat_topic = 'unknown'
        if classifier_data:
            threat_topic = classifier_data.get('topic', 'unknown')
        
        # Extract IOCs
        iocs = self._extract_iocs(entities or [])
        
        # Calculate overall confidence
        confidence = relevance_score
        if len(signals_used) > 1:
            # Higher confidence when multiple signals agree
            agreement_bonus = 0.1 * (len(signals_used) - 1)
            confidence = min(confidence + agreement_bonus, 1.0)
        
        return AggregatedSignal(
            relevance_score=relevance_score,
            risk_score=risk_score,
            risk_level=risk_level,
            threat_topic=threat_topic,
            is_actionable=is_actionable,
            keyword_score=keyword_score,
            classifier_score=classifier_score,
            ner_score=ner_score,
            entities=entities or [],
            iocs=iocs,
            signals_used=signals_used,
            confidence=confidence
        )
    
    def aggregate_batch(
        self,
        keyword_data_list: Optional[List[Dict]] = None,
        classifier_data_list: Optional[List[Dict]] = None,
        entities_list: Optional[List[List[Dict]]] = None
    ) -> List[AggregatedSignal]:
        """
        Aggregate signals for multiple records.
        
        Args:
            keyword_data_list: List of keyword filter results
            classifier_data_list: List of classifier results
            entities_list: List of entity lists
            
        Returns:
            List of AggregatedSignal objects
        """
        # Determine batch size from available data
        batch_size = 0
        if keyword_data_list:
            batch_size = len(keyword_data_list)
        elif classifier_data_list:
            batch_size = len(classifier_data_list)
        elif entities_list:
            batch_size = len(entities_list)
        
        if batch_size == 0:
            return []
        
        results = []
        for i in range(batch_size):
            keyword_data = keyword_data_list[i] if keyword_data_list else None
            classifier_data = classifier_data_list[i] if classifier_data_list else None
            entities = entities_list[i] if entities_list else None
            
            results.append(self.aggregate(keyword_data, classifier_data, entities))
        
        return results
    
    def filter_actionable(
        self,
        signals: List[AggregatedSignal]
    ) -> List[AggregatedSignal]:
        """
        Filter to only actionable signals.
        
        Args:
            signals: List of aggregated signals
            
        Returns:
            Filtered list of actionable signals
        """
        return [s for s in signals if s.is_actionable]
    
    def prioritize(
        self,
        signals: List[AggregatedSignal]
    ) -> List[AggregatedSignal]:
        """
        Sort signals by priority (risk score).
        
        Args:
            signals: List of aggregated signals
            
        Returns:
            Sorted list (highest priority first)
        """
        return sorted(signals, key=lambda s: s.risk_score, reverse=True)
    
    def to_dict(self, signal: AggregatedSignal) -> Dict[str, Any]:
        """
        Convert AggregatedSignal to dictionary.
        
        Args:
            signal: AggregatedSignal object
            
        Returns:
            Dictionary representation
        """
        return {
            'relevance_score': signal.relevance_score,
            'risk_score': signal.risk_score,
            'risk_level': signal.risk_level.value,
            'threat_topic': signal.threat_topic,
            'is_actionable': signal.is_actionable,
            'keyword_score': signal.keyword_score,
            'classifier_score': signal.classifier_score,
            'ner_score': signal.ner_score,
            'entities': signal.entities,
            'iocs': signal.iocs,
            'signals_used': signal.signals_used,
            'confidence': signal.confidence,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics."""
        return {
            'enabled': self.enabled,
            'weights': {
                'keyword': self.keyword_weight,
                'classifier': self.classifier_weight,
                'ner': self.ner_weight,
            },
            'thresholds': {
                'risk': self.risk_threshold,
                'actionable': self.actionable_threshold,
            },
        }
