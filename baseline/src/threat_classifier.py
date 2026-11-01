"""
Threat-Topic Classifier for DarkWeb Translation Pipeline
ML-based classifier for detecting threat-related content.
Based on the paper: "a BERT-based classifier can be fine-tuned on labeled data to 
distinguish between general chatter and potential threat intelligence"
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ThreatClassifier:
    """
    ML-based threat topic classifier.
    Uses BERT/DistilBERT for threat relevance scoring with weak supervision.
    """
    
    # Threat topic labels
    THREAT_TOPICS = [
        'vulnerability_exploit',    # CVE discussions, exploit code
        'malware_analysis',         # Malware samples, analysis
        'data_breach',              # Leaked data, breaches
        'attack_planning',          # Coordination, target discussion
        'tool_trading',             # Selling/buying tools
        'credential_trading',       # Account/password trading
        'ransomware',               # Ransomware operations
        'phishing',                 # Phishing campaigns
        'ddos',                     # DDoS services/attacks
        'general_security',         # General security discussion
        'non_threat',               # Non-threat content
    ]
    
    # Keywords for weak supervision labeling functions
    TOPIC_KEYWORDS = {
        'vulnerability_exploit': [
            'cve-', 'exploit', 'vulnerability', 'poc', 'proof of concept',
            'rce', 'remote code execution', 'buffer overflow', 'heap overflow',
            'use after free', 'race condition', 'privilege escalation',
            '0day', 'zero-day', 'unpatched', 'patch bypass',
        ],
        'malware_analysis': [
            'malware', 'sample', 'hash', 'ioc', 'indicator',
            'c2', 'command and control', 'beacon', 'payload',
            'dropper', 'loader', 'packer', 'crypter', 'obfuscation',
            'sandbox', 'analysis', 'reverse engineer', 'disassembly',
        ],
        'data_breach': [
            'breach', 'leak', 'dump', 'database', 'leaked',
            'combolist', 'credentials', 'fullz', 'dox',
            'personal data', 'pii', 'ssn', 'credit card',
            'data for sale', 'fresh dump',
        ],
        'attack_planning': [
            'target', 'attack', 'operation', 'campaign',
            'hit list', 'victims', 'infrastructure',
            'we will attack', 'planning to', 'next target',
        ],
        'tool_trading': [
            'for sale', 'selling', 'buying', 'want to buy',
            'tool', 'kit', 'builder', 'panel', 'source code',
            'rat', 'stealer', 'crypter', 'botnet',
            'lifetime', 'subscription', 'license',
        ],
        'credential_trading': [
            'accounts', 'login', 'passwords', 'credentials',
            'combo', 'valid', 'fresh', 'working',
            'netflix', 'spotify', 'vpn', 'ssh', 'rdp',
            'bank', 'paypal', 'crypto', 'wallet',
        ],
        'ransomware': [
            'ransom', 'encrypt', 'decrypt', 'bitcoin',
            'payment', 'deadline', 'victim', 'negotiations',
            'lockbit', 'conti', 'revil', 'blackcat',
            'data will be published', 'pay or',
        ],
        'phishing': [
            'phish', 'scam', 'fake', 'clone',
            'landing page', 'email template', 'sms',
            'credential harvesting', 'social engineering',
            'look-alike', 'typosquat',
        ],
        'ddos': [
            'ddos', 'dos', 'flood', 'amplification',
            'botnet', 'stresser', 'booter', 'layer 7',
            'syn flood', 'udp flood', 'http flood',
            'take down', 'offline',
        ],
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the threat classifier.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        nlp_config = config.get('nlp', {})
        
        self.enabled = nlp_config.get('enable_threat_classifier', False)
        self.model_name = nlp_config.get('threat_classifier_model', 'distilbert-base-uncased')
        self.threshold = nlp_config.get('threat_classifier_threshold', 0.5)
        self.cache_dir = Path(config['paths'].get('models_cache', 'models'))
        
        # ML model components
        self.model = None
        self.tokenizer = None
        self.device = None
        
        # Weak supervision compiled patterns
        self._compile_patterns()
        
        if self.enabled:
            self._load_model()
        
        logger.info(f"ThreatClassifier initialized (enabled={self.enabled})")
    
    def _compile_patterns(self) -> None:
        """Compile keyword patterns for weak supervision."""
        self.topic_patterns = {}
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            pattern = re.compile(
                r'\b(' + '|'.join(re.escape(kw) for kw in keywords) + r')\b',
                re.IGNORECASE
            )
            self.topic_patterns[topic] = pattern
    
    def _load_model(self) -> None:
        """Load the transformer model for classification."""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading threat classifier model: {self.model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=str(self.cache_dir)
            )
            
            # Try to load fine-tuned model, fall back to base model
            model_path = self.cache_dir / "threat_classifier"
            if model_path.exists():
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    str(model_path),
                    num_labels=len(self.THREAT_TOPICS)
                )
                logger.info("Loaded fine-tuned threat classifier")
            else:
                # Use base model with random classification head
                # Will need to be fine-tuned for best results
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name,
                    num_labels=len(self.THREAT_TOPICS),
                    cache_dir=str(self.cache_dir)
                )
                logger.info("Loaded base model (not fine-tuned, using weak supervision)")
            
            self.model.to(self.device)
            self.model.eval()
            
        except ImportError:
            logger.warning("transformers not installed, using weak supervision only")
            self.model = None
        except Exception as e:
            logger.warning(f"Failed to load model: {e}, using weak supervision only")
            self.model = None
    
    def _weak_supervision_classify(self, text: str) -> Dict[str, float]:
        """
        Classify using weak supervision (keyword-based labeling functions).
        
        Args:
            text: Text to classify
            
        Returns:
            Dictionary of topic -> confidence score
        """
        scores = {}
        text_lower = text.lower()
        
        for topic, pattern in self.topic_patterns.items():
            matches = pattern.findall(text_lower)
            # Score based on number of unique keyword matches
            unique_matches = len(set(matches))
            # Normalize to 0-1 range (cap at 5 matches for max score)
            scores[topic] = min(unique_matches / 5.0, 1.0)
        
        # Non-threat score is inverse of max threat score
        max_threat_score = max(scores.values()) if scores else 0
        scores['non_threat'] = 1.0 - max_threat_score
        scores['general_security'] = 0.5 if max_threat_score > 0 else 0.0
        
        return scores
    
    def _model_classify(self, text: str) -> Dict[str, float]:
        """
        Classify using the ML model.
        
        Args:
            text: Text to classify
            
        Returns:
            Dictionary of topic -> confidence score
        """
        if not self.model or not self.tokenizer:
            return {}
        
        try:
            import torch
            
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)
                probs = probs.cpu().numpy()[0]
            
            # Map to topic names
            scores = {
                self.THREAT_TOPICS[i]: float(probs[i])
                for i in range(len(self.THREAT_TOPICS))
            }
            
            return scores
            
        except Exception as e:
            logger.warning(f"Model classification failed: {e}")
            return {}
    
    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify text for threat topics.
        
        Args:
            text: Text to classify
            
        Returns:
            Classification result with scores and predicted topic
        """
        if not self.enabled or not text:
            return {
                'is_threat': False,
                'confidence': 0.0,
                'topic': 'non_threat',
                'scores': {}
            }
        
        # Get weak supervision scores
        ws_scores = self._weak_supervision_classify(text)
        
        # Get model scores if available
        model_scores = self._model_classify(text)
        
        # Combine scores (prefer model if available)
        if model_scores:
            # Weighted combination: 70% model, 30% weak supervision
            combined_scores = {}
            for topic in self.THREAT_TOPICS:
                ws = ws_scores.get(topic, 0)
                ml = model_scores.get(topic, 0)
                combined_scores[topic] = 0.7 * ml + 0.3 * ws
        else:
            combined_scores = ws_scores
        
        # Find top topic
        if combined_scores:
            top_topic = max(combined_scores.items(), key=lambda x: x[1])
            topic_name = top_topic[0]
            confidence = top_topic[1]
        else:
            topic_name = 'non_threat'
            confidence = 0.0
        
        # Determine if threat
        is_threat = (
            topic_name != 'non_threat' and 
            topic_name != 'general_security' and
            confidence >= self.threshold
        )
        
        return {
            'is_threat': is_threat,
            'confidence': confidence,
            'topic': topic_name,
            'scores': combined_scores,
            'method': 'hybrid' if model_scores else 'weak_supervision'
        }
    
    def classify_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Classify multiple texts.
        
        Args:
            texts: List of texts
            
        Returns:
            List of classification results
        """
        return [self.classify(text) for text in texts]
    
    def get_threat_score(self, text: str) -> float:
        """
        Get overall threat score for text (0-1).
        
        Args:
            text: Text to score
            
        Returns:
            Threat score between 0 and 1
        """
        result = self.classify(text)
        if result['topic'] in ['non_threat', 'general_security']:
            return 0.0
        return result['confidence']
    
    def generate_weak_labels(self, texts: List[str]) -> List[Tuple[str, str, float]]:
        """
        Generate weak supervision labels for training data.
        Uses labeling functions (LFs) as described in the paper.
        
        Args:
            texts: List of texts to label
            
        Returns:
            List of (text, label, confidence) tuples
        """
        labeled_data = []
        
        for text in texts:
            ws_scores = self._weak_supervision_classify(text)
            
            # Only label high-confidence examples
            max_score = max(ws_scores.values())
            if max_score >= 0.6:  # High confidence threshold
                top_topic = max(ws_scores.items(), key=lambda x: x[1])[0]
                labeled_data.append((text, top_topic, max_score))
            else:
                # Abstain (no confident label)
                labeled_data.append((text, None, 0.0))
        
        return labeled_data
    
    def save_model(self, path: Optional[Path] = None) -> None:
        """Save the fine-tuned model."""
        if not self.model:
            return
        
        save_path = path or (self.cache_dir / "threat_classifier")
        save_path.mkdir(parents=True, exist_ok=True)
        
        self.model.save_pretrained(str(save_path))
        self.tokenizer.save_pretrained(str(save_path))
        logger.info(f"Model saved to {save_path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get classifier statistics."""
        return {
            'enabled': self.enabled,
            'model_loaded': self.model is not None,
            'model_name': self.model_name,
            'threshold': self.threshold,
            'num_topics': len(self.THREAT_TOPICS),
            'topics': self.THREAT_TOPICS,
        }
    
    def cleanup(self) -> None:
        """Cleanup model resources."""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        logger.info("ThreatClassifier cleaned up")
