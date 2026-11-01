"""
Relevance Filter for DarkWeb Translation Pipeline
Filters content to identify cybersecurity-related conversations.
Based on Algorithm 1 from "Monitoring and Analyzing Cybersecurity Conversations in Darkweb Forums".

Implements three layers, OR-combined:
  1. Keyword + IOC pattern heuristics (always on; fast).
  2. (Optional) zero-shot DeBERTa NLI classifier — works without training data,
     activated by `relevance.zero_shot_enabled: true` in config.
  3. (Optional) fine-tuned binary classifier — loads from `models/relevance_classifier/`
     when present; train it via `scripts/train_relevance_classifier.py`.

The OR-of-signals lifts recall (a record is relevant if ANY layer says so) while
the per-layer thresholds preserve precision.
"""

import re
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class RelevanceFilter:
    """Filters content to detect cybersecurity-related conversations."""
    
    # Cybersecurity-related keywords (from paper: 'attack', 'DDoS', 'CVE', etc.)
    CYBERSECURITY_KEYWORDS = [
        # Attack types
        'attack', 'ddos', 'dos', 'sql injection', 'xss', 'csrf', 'rce', 'lfi', 'rfi',
        'phishing', 'ransomware', 'malware', 'trojan', 'virus', 'worm', 'botnet',
        'exploit', 'vulnerability', 'zero-day', '0day', 'zero day',
        
        # Security identifiers
        'cve', 'cve-', 'cwe', 'mitre', 'apt', 'ttp', 'ioc', 'indicators of compromise',
        
        # Technical terms
        'payload', 'shell', 'backdoor', 'rootkit', 'keylogger', 'rat', 'remote access',
        'privilege escalation', 'lateral movement', 'persistence', 'exfiltration',
        
        # Threat intelligence
        'threat actor', 'hacker', 'cybercriminal', 'apt group', 'campaign',
        'breach', 'data leak', 'credentials', 'password dump', 'database leak',
        
        # Tools and techniques
        'metasploit', 'nmap', 'burp', 'wireshark', 'mimikatz', 'cobalt strike',
        'empire', 'powershell', 'cmd', 'bash', 'python script',
        
        # Network security
        'firewall', 'ids', 'ips', 'siem', 'endpoint', 'network security',
        'intrusion', 'penetration test', 'pentest', 'red team', 'blue team',
        
        # Cryptocurrency/ransomware
        'bitcoin', 'cryptocurrency', 'ransom', 'extortion', 'decrypt',
        
        # Slang and informal terms (from paper)
        'pwn', 'pwned', 'owned', 'hack', 'crack', 'bypass', 'bypassed',
        'leak', 'dox', 'doxxed', 'doxxing',
    ]
    
    # Keywords indicating DEFINITE noise/spam to skip
    SPAM_KEYWORDS = [
        # Adult content spam
        'porn', 'xxx', 'nude', 'naked', 'sex video', 'cam girl',
        'hentai porn', 'lesbian porn', 'gay porn',
        
        # Obvious spam patterns
        'click here', 'buy now', 'order now', 'free trial',
        'limited offer', 'act now', 'call now',
        
        # Pure navigation/UI
        'next page', 'previous page', 'go back', 'home page',
        'click to expand', 'show more', 'load more',
        
        # Copyright/legal boilerplate
        'all rights reserved', 'terms of service', 'privacy policy',
        'cookie policy', 'terms and conditions',
    ]
    
    # Patterns for spam detection
    SPAM_PATTERNS = [
        re.compile(r'\b\d{3}-\d{3}-\d{4}\b'),  # Phone numbers
        re.compile(r'\$\d+\.\d{2}'),  # Prices (excessive)
        re.compile(r'(buy|order|call)\s+(now|today)', re.IGNORECASE),
    ]

    # ----- Pre-translation filter (multilingual) ---------------------------
    # English cyber loanwords that appear unchanged in nearly every language
    # we encounter (Latin, Cyrillic, CJK posts often contain "malware",
    # "ransomware", "RDP", etc. inline). Matching these on the ORIGINAL text
    # avoids wasting the translator on records with no cyber signal at all.
    # English cyber loanwords used unchanged in non-English text. Tightened:
    # - Removed `tor` (collides with German "Tor"/gate, French "tort", etc.)
    # - Removed `onion` (collides with food references, board chrome listing
    #   onion mirrors); use the .onion regex pattern with context instead.
    # - Removed bare `eth` (Ethernet, ethnic, ethyl)
    # - Removed bare `pwn` (matches inside other words)
    # - Removed `breach`/`leak`/`dump` (very common English words; covered
    #   by the post-translation filter on the English text)
    UNIVERSAL_LOANWORDS = [
        'malware', 'ransomware', 'phishing', 'exploit',
        'hacker', 'ddos', 'trojan', 'rootkit', 'backdoor', 'botnet',
        'keylogger', 'spyware', 'adware', 'cve-', 'cwe-',
        '0day', '0-day', 'zero-day', 'zeroday',
        'rdp', 'darkweb', 'darknet',
        'bitcoin', 'ethereum', 'monero', 'cryptocurrency',
        'cobalt strike', 'mimikatz', 'lockbit', 'wannacry',
        'pwned',
    ]
    _UNIVERSAL_LOANWORDS_RE = re.compile(
        r'\b(?:' + '|'.join(re.escape(w) for w in UNIVERSAL_LOANWORDS) + r')\b',
        re.IGNORECASE
    )

    # Universal patterns split by ambiguity. STRONG patterns are ones whose
    # mere presence indicates cyber content unambiguously (CVE, CWE, MITRE
    # techniques). AMBIGUOUS patterns can occur in non-cyber text — image
    # hashes on chan boards (`[a-f0-9]{32}`), `.onion` URLs in forum
    # sidebars, IP addresses in nginx logs, BTC addresses in donation
    # buttons — and only count when surrounded by cyber context words.
    _STRONG_UNIVERSAL_PATTERNS = [
        re.compile(r'\bcve-\d{4}-\d{4,}\b', re.IGNORECASE),
        re.compile(r'\bcwe-\d+\b', re.IGNORECASE),
        re.compile(r'\bT\d{4}(?:\.\d{3})?\b'),                # MITRE technique
    ]
    _AMBIGUOUS_UNIVERSAL_PATTERNS = [
        re.compile(r'\b[a-f0-9]{32}\b', re.IGNORECASE),       # MD5
        re.compile(r'\b[a-f0-9]{40}\b', re.IGNORECASE),       # SHA1
        re.compile(r'\b[a-f0-9]{64}\b', re.IGNORECASE),       # SHA256
        re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),  # IPv4
        re.compile(r'\b[a-z2-7]{16,56}\.onion\b', re.IGNORECASE),
        re.compile(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b'),   # BTC addr
        re.compile(r'\b0x[a-fA-F0-9]{40}\b'),                 # ETH addr
    ]
    # Cyber context words checked in a ±150 char window around an ambiguous
    # pattern. Multilingual on purpose; covers all top languages. Built as
    # a list (not a multi-line string) so an accidental trailing `|` can't
    # create an empty alternative that matches everywhere.
    _CYBER_CONTEXT_TERMS_LIST = [
        # English / loanwords
        'malware', 'ransomware', 'exploit', 'vulnerab', 'hashsum', 'checksum',
        'md5', 'sha1', 'sha2', 'sha-256', 'phishing', 'trojan', 'backdoor',
        'ddos', 'hacker', 'breach', 'leak', 'dump', 'password', 'cve',
        'spyware', 'adware', 'botnet', 'keylogger', 'rootkit', 'payload',
        'c2', 'attack', 'infect', 'cryptolocker', 'wallet', 'seed phrase',
        'stolen', 'stealer', 'encrypted', 'encryption', 'decrypt',
        # Russian
        'уязвим', 'взлом', 'вредонос', 'эксплойт', 'хакер', 'шифр', 'стиллер',
        # German
        'sicherheitslücke', 'sicherheitsluecke', 'schwachstelle',
        'schadsoftware', 'verschlüssel', 'verschluessel', 'angriff',
        # French / Italian / Spanish / Catalan
        'vulnerab', 'attaque', 'piratage', 'cifrat', 'chiffrement',
        'hackeo', 'cifrado', 'attacco', 'hackeraggio',
        # CJK
        '漏洞', '攻击', '攻擊', '黑客', '駭客', '病毒', '木马', '木馬',
        '加密', '后门', '後門', '脆弱性', '攻撃', 'マルウェア',
    ]
    _CYBER_CONTEXT_WORDS = re.compile(
        r'(?:' + '|'.join(re.escape(t) for t in _CYBER_CONTEXT_TERMS_LIST) + r')',
        re.IGNORECASE
    )
    
    def __init__(self,
                 min_length: int = 50,
                 max_length: int = 10000,
                 enable_spam_filter: bool = True,
                 enable_cybersecurity_filter: bool = True,
                 min_cybersecurity_keywords: int = 1,
                 classifier_dir: Optional[str] = None,
                 zero_shot_enabled: bool = False,
                 zero_shot_model: str = "MoritzLaurer/deberta-v3-large-zeroshot-v2.0",
                 classifier_threshold: float = 0.7,
                 multilingual_lexicon_path: Optional[str] = None,
                 pre_translation_min_length: int = 200):
        """
        Initialize relevance filter.

        Args:
            min_length: Minimum text length to consider
            max_length: Maximum text length (longer = likely scraped noise)
            enable_spam_filter: Whether to filter spam keywords
            enable_cybersecurity_filter: Whether to filter for cybersecurity relevance
            min_cybersecurity_keywords: Minimum cybersecurity keywords required
            classifier_dir: Path to fine-tuned binary classifier checkpoint
                (HuggingFace transformers format). If present, used as a third
                signal OR'd with keyword check.
            zero_shot_enabled: Use a zero-shot NLI classifier as a cold-start
                second opinion when no fine-tuned model is available.
            zero_shot_model: HF model id for zero-shot classification.
            classifier_threshold: Minimum classifier probability to count as
                positive. Set high to preserve precision.
        """
        self.min_length = min_length
        self.max_length = max_length
        self.enable_spam_filter = enable_spam_filter
        self.enable_cybersecurity_filter = enable_cybersecurity_filter
        self.min_cybersecurity_keywords = min_cybersecurity_keywords

        # Compile regex patterns for faster matching
        self.cybersec_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in self.CYBERSECURITY_KEYWORDS
        ]

        # Lazy-loaded classifier handles. None → keyword-only.
        self._classifier_dir = classifier_dir
        self._zero_shot_enabled = zero_shot_enabled
        self._zero_shot_model_id = zero_shot_model
        self._classifier_threshold = classifier_threshold
        self._fine_tuned = None       # AutoModelForSequenceClassification + tokenizer
        self._zero_shot = None        # transformers pipeline

        # Multilingual lexicon for the pre-translation filter. Per-language
        # native cyber vocabulary so a non-English post that mentions security
        # only in its source language can pass without first being translated.
        self.pre_translation_min_length = pre_translation_min_length
        self._multilingual_lexicon: Dict[str, "re.Pattern"] = {}
        self._load_multilingual_lexicon(multilingual_lexicon_path)

    def _load_multilingual_lexicon(self, path_override: Optional[str]) -> None:
        """Compile per-language cyber-term regexes from the YAML lexicon.

        Falls back silently to English-only matching if PyYAML is unavailable
        or the file is missing — pre-filter still works via the universal
        loanwords + pattern paths.
        """
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML unavailable; multilingual pre-filter limited to universal loanwords")
            return

        path = Path(path_override) if path_override else None
        if path is None:
            # Default location relative to project root
            path = Path(__file__).resolve().parent.parent / 'data' / 'dictionaries' / 'cyber_terms_multilingual.yaml'
        if not path.exists():
            logger.warning(f"Multilingual lexicon not found at {path}; using loanwords only")
            return

        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not load multilingual lexicon ({e}); using loanwords only")
            return

        compiled: Dict[str, "re.Pattern"] = {}
        for lang, terms in data.items():
            if not terms:
                continue
            # Sort by length desc so multi-word terms match before single-word
            # substrings ("Sicherheits..." before "Sicherheit").
            sorted_terms = sorted({t.strip() for t in terms if t and t.strip()},
                                  key=len, reverse=True)
            if not sorted_terms:
                continue
            # CJK doesn't use \b; for Latin/Cyrillic/Greek/etc., \b works.
            # Use a non-word-boundary regex for CJK languages so it actually
            # matches inside text without spaces.
            cjk_langs = {'zh', 'ja', 'ko', 'th'}
            if lang in cjk_langs:
                pattern = '|'.join(re.escape(t) for t in sorted_terms)
            else:
                pattern = r'\b(?:' + '|'.join(re.escape(t) for t in sorted_terms) + r')\b'
            try:
                compiled[lang] = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                logger.warning(f"Could not compile lexicon for lang={lang}: {e}")
        self._multilingual_lexicon = compiled
        total_terms = sum(len(v) for v in data.values() if v)
        logger.info(f"Loaded multilingual cyber lexicon: {len(compiled)} languages, "
                    f"~{total_terms} terms total")

    def _load_fine_tuned(self):
        """Load a fine-tuned classifier if a checkpoint dir was provided."""
        if self._fine_tuned is not None or not self._classifier_dir:
            return self._fine_tuned
        path = Path(self._classifier_dir)
        if not path.exists():
            return None
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            tok = AutoTokenizer.from_pretrained(str(path))
            mdl = AutoModelForSequenceClassification.from_pretrained(str(path))
            mdl.eval()
            device = "cuda" if torch.cuda.is_available() else "cpu"
            mdl.to(device)
            self._fine_tuned = (tok, mdl, device)
            logger.info("Loaded fine-tuned relevance classifier from %s on %s", path, device)
        except Exception as e:
            logger.warning("Could not load fine-tuned classifier (%s); falling back", e)
            self._fine_tuned = None
        return self._fine_tuned

    def _load_zero_shot(self):
        """Lazy-load DeBERTa-v3 zero-shot pipeline as cold start."""
        if self._zero_shot is not None or not self._zero_shot_enabled:
            return self._zero_shot
        try:
            from transformers import pipeline
            self._zero_shot = pipeline(
                "zero-shot-classification",
                model=self._zero_shot_model_id,
                device_map="auto",
            )
            logger.info("Loaded zero-shot classifier %s", self._zero_shot_model_id)
        except Exception as e:
            logger.warning("Could not load zero-shot classifier (%s); falling back", e)
            self._zero_shot = None
        return self._zero_shot

    def _classifier_score(self, text: str) -> float:
        """Return P(relevant) in [0,1] from whichever classifier is available."""
        ft = self._load_fine_tuned()
        if ft:
            tok, mdl, device = ft
            try:
                import torch
                with torch.no_grad():
                    inputs = tok(text[:1024], return_tensors="pt", truncation=True).to(device)
                    logits = mdl(**inputs).logits
                    probs = logits.softmax(-1).squeeze().tolist()
                # Convention: index 1 = relevant (positive class)
                return float(probs[-1] if isinstance(probs, list) else probs)
            except Exception as e:
                logger.debug("Fine-tuned classifier inference failed: %s", e)
        zs = self._load_zero_shot()
        if zs:
            try:
                out = zs(
                    text[:1024],
                    candidate_labels=["cybersecurity threat discussion",
                                      "off-topic / non-security content"],
                    multi_label=False,
                )
                # `scores` is in the same order as `labels` (sorted desc by score).
                # Find the score for the cybersecurity label.
                if isinstance(out, dict) and "labels" in out and "scores" in out:
                    for lbl, sc in zip(out["labels"], out["scores"]):
                        if "cybersecurity" in lbl.lower():
                            return float(sc)
            except Exception as e:
                logger.debug("Zero-shot classifier inference failed: %s", e)
        return 0.0
    
    def _is_spam(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text is spam.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (is_spam, reason)
        """
        if not self.enable_spam_filter:
            return False, None
        
        text_lower = text.lower()
        
        # Check spam keywords
        for keyword in self.SPAM_KEYWORDS:
            if keyword in text_lower:
                return True, f"spam_keyword:{keyword}"
        
        # Check spam patterns
        for pattern in self.SPAM_PATTERNS:
            if len(pattern.findall(text)) > 3:  # More than 3 occurrences
                return True, "spam_pattern"
        
        return False, None
    
    def _is_cybersecurity_related(self, text: str) -> Tuple[bool, int]:
        """
        Check if text is cybersecurity-related (Algorithm 1: ISCYBERTHREATRELATED).
        Uses keyword-based heuristics as described in the paper.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (is_cybersecurity_related, keyword_count)
        """
        if not self.enable_cybersecurity_filter:
            return True, 0  # If filter disabled, assume all content is relevant
        
        text_lower = text.lower()
        keyword_count = 0
        
        # Count cybersecurity keywords (case-insensitive)
        for pattern in self.cybersec_patterns:
            if pattern.search(text):
                keyword_count += 1
        
        # Also check for CVE patterns (CVE-YYYY-NNNNN)
        cve_pattern = re.compile(r'cve-\d{4}-\d{4,}', re.IGNORECASE)
        if cve_pattern.search(text):
            keyword_count += 2  # CVE is strong indicator
        
        # Check for IOC patterns (IPs, hashes, URLs)
        ip_pattern = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
        hash_pattern = re.compile(r'\b[a-f0-9]{32,64}\b', re.IGNORECASE)  # MD5/SHA256
        if ip_pattern.search(text) or hash_pattern.search(text):
            keyword_count += 1
        
        is_related = keyword_count >= self.min_cybersecurity_keywords
        return is_related, keyword_count
    
    def is_relevant(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text is relevant for translation (cybersecurity-related).
        Implements Algorithm 1: ISCYBERTHREATRELATED() function.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (is_relevant, skip_reason)
        """
        if not text:
            return False, "empty"
        
        # Check minimum length only (long texts are valid - could be forum conversations)
        text_length = len(text)
        if text_length < self.min_length:
            return False, "too_short"
        
        # NOTE: Removed max_length check - long forum conversations are important
        # Long texts are processed (may be split by sentence processor if needed)
        
        # Check for spam (filter out obvious noise first)
        is_spam, spam_reason = self._is_spam(text)
        if is_spam:
            return False, spam_reason
        
        # Check if cybersecurity-related (Algorithm 1 requirement)
        is_cybersec, keyword_count = self._is_cybersecurity_related(text)
        if is_cybersec:
            return True, None

        # OR-of-signals: keyword filter said no — give the optional ML classifier
        # a chance to recover non-English keywords, paraphrased threats, or slang
        # the keyword list doesn't cover. Only counts as positive if confidence
        # exceeds the threshold (preserves precision).
        if self._classifier_dir or self._zero_shot_enabled:
            score = self._classifier_score(text)
            if score >= self._classifier_threshold:
                logger.debug(
                    "Classifier rescued borderline record (P=%.2f >= %.2f)",
                    score, self._classifier_threshold
                )
                return True, None

        return False, f"not_cybersecurity_related (keywords: {keyword_count})"
    
    def is_relevant_multilingual(self, text: str, lang_code: str) -> Tuple[bool, str]:
        """
        Pre-translation cyber-relevance check that works on the ORIGINAL
        (un-translated) text in any supported language.

        Decision rule (any layer matching → pass):
          1. Universal language-agnostic patterns (CVE, hashes, IPs, .onion,
             wallets, MITRE technique IDs).
          2. Universal English cyber loanwords that appear unchanged in
             non-English text (malware, ransomware, RDP, ...).
          3. Per-language native cyber vocabulary (loaded from
             cyber_terms_multilingual.yaml).

        Returns:
            (is_relevant, reason) where reason is "universal_pattern",
            "loanword:<term>", "lang:<code>:<term>", or "no_cyber_signal".

        Short text (< pre_translation_min_length) is always declared
        relevant — no signal is reliable below that length, and translating
        a short input is cheap, so deferring to the post-translation filter
        avoids losing edge cases.
        """
        if not text or len(text) < self.pre_translation_min_length:
            return True, "too_short_to_pre_filter"

        # Layer 1a: strong universal patterns — unambiguous cyber signals.
        for pat in self._STRONG_UNIVERSAL_PATTERNS:
            m = pat.search(text)
            if m:
                return True, f"strong:{m.group()}"

        # Layer 1b: ambiguous universal patterns require cyber context within
        # a ±150 char window — but the match span itself is excluded from
        # the window. Hashes/wallets contain substrings like "c2" and "rat"
        # by chance; without this exclusion they self-trigger their own
        # context check (`a4b5c6d7e8f9a0b1c2d3...` matches "c2" in itself).
        for pat in self._AMBIGUOUS_UNIVERSAL_PATTERNS:
            m = pat.search(text)
            if not m:
                continue
            lo = max(0, m.start() - 150)
            hi = min(len(text), m.end() + 150)
            window_before = text[lo:m.start()]
            window_after = text[m.end():hi]
            if (self._CYBER_CONTEXT_WORDS.search(window_before)
                    or self._CYBER_CONTEXT_WORDS.search(window_after)):
                return True, f"ambiguous_with_context:{m.group()[:20]}"

        # Layer 2: universal loanwords
        m = self._UNIVERSAL_LOANWORDS_RE.search(text)
        if m:
            return True, f"loanword:{m.group()}"

        # Layer 3: language-specific native vocabulary
        lex = self._multilingual_lexicon.get(lang_code)
        if lex is not None:
            m = lex.search(text)
            if m:
                return True, f"lang:{lang_code}:{m.group()}"

        return False, "no_cyber_signal"

    def filter_sentences(self, sentences: list) -> list:
        """
        Filter a list of sentences for relevance.
        
        Args:
            sentences: List of sentences
            
        Returns:
            List of relevant sentences
        """
        relevant = []
        for sentence in sentences:
            is_rel, _ = self.is_relevant(sentence)
            if is_rel:
                relevant.append(sentence)
        
        return relevant
    
    def get_filter_stats(self, text: str) -> dict:
        """
        Get statistics about text filtering.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with stats
        """
        is_rel, skip_reason = self.is_relevant(text)
        
        return {
            'is_relevant': is_rel,
            'skip_reason': skip_reason,
            'length': len(text),
            'word_count': len(text.split()),
            'is_spam': self._is_spam(text)[0]
        }

