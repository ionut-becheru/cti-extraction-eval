"""
Cybersecurity Named Entity Recognition (NER) for DarkWeb Translation Pipeline
Extracts security-relevant entities: CVE, malware, threat actors, tools, IPs, hashes, domains.
Based on the paper's reference to "named entity recognition (using spaCy's NER or similar models)".
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Represents an extracted entity."""
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CybersecNER:
    """
    Cybersecurity Named Entity Recognition module.
    Extracts security-relevant entities using pattern matching and optional spaCy NER.
    """
    
    # Entity types
    ENTITY_TYPES = [
        'CVE',           # CVE identifiers (CVE-YYYY-NNNNN)
        'MALWARE',       # Malware names
        'THREAT_ACTOR',  # APT groups, threat actor names
        'TOOL',          # Security tools, hacking tools
        'IP',            # IP addresses
        'HASH',          # File hashes (MD5, SHA1, SHA256)
        'DOMAIN',        # Domain names
        'URL',           # URLs
        'EMAIL',         # Email addresses
        'CRYPTO_WALLET', # Cryptocurrency wallet addresses
        'PORT',          # Network ports
        'FILEPATH',      # File paths
    ]
    
    # Known malware families/names
    # NOTE: Avoid single common words that could be market names (empire, hive, etc.)
    KNOWN_MALWARE = [
        'emotet', 'trickbot', 'ryuk', 'conti', 'lockbit', 'revil', 'sodinokibi',
        'wannacry', 'notpetya', 'petya', 'locky', 'cerber', 'gandcrab', 'maze',
        'dridex', 'qakbot', 'qbot', 'icedid', 'bazarloader', 'bazarbackdoor',
        'cobalt strike', 'cobaltstrike', 'beacon', 'meterpreter', 'mimikatz',
        'bloodhound', 'empire framework', 'empire c2', 'powershell empire',
        'covenant', 'sliver', 'brute ratel', 'bruteratel',
        'agent tesla', 'formbook', 'lokibot', 'azorult', 'raccoon stealer', 'redline stealer',
        'vidar stealer', 'mars stealer', 'blackcat ransomware', 'alphv ransomware',
        'hive ransomware', 'blackmatter ransomware', 'darkside ransomware',
        'babuk', 'ragnar locker', 'ragnarlocker', 'avaddon', 'netwalker',
        'zeus trojan', 'kronos', 'ursnif', 'gozi', 'nanocore', 'njrat', 'remcos rat',
        'asyncrat', 'quasarrat', 'warzone rat', 'darkcomet', 'poison ivy', 'gh0st rat',
        'plugx', 'shadowpad', 'chinachopper', 'derusbi', 'hikit', 'winnti',
    ]
    
    # Ambiguous terms that need context (excluded from automatic malware detection)
    AMBIGUOUS_TERMS = ['empire', 'hive', 'blackcat', 'raccoon', 'redline', 'vidar', 'darkside', 'zeus']
    
    # Known APT groups and threat actors
    # NOTE: Removed "anonymous" as it's too common (forum usernames, etc.)
    KNOWN_THREAT_ACTORS = [
        'apt1', 'apt2', 'apt3', 'apt10', 'apt28', 'apt29', 'apt32', 'apt33',
        'apt34', 'apt35', 'apt37', 'apt38', 'apt39', 'apt40', 'apt41',
        'fancy bear', 'cozy bear', 'lazarus group', 'kimsuky',
        'turla', 'sandworm', 'equation group', 'fin7', 'fin8', 'fin11', 'fin12',
        'carbanak', 'ta505', 'ta551', 'ta571', 'ta575', 'ta577',
        'lockbit gang', 'conti group', 'revil gang',
        'lapsus$', 'killnet', 'anonymous sudan', 'ghostsec',
        'noname057', 'noname057(16)', 'scattered spider',
        'clop gang', 'cl0p', 'vice society', 'play ransomware group',
        'cuba ransomware', 'royal ransomware',
        'magecart', 'silence group', 'cobalt group', 'mustang panda',
        'stone panda', 'gothic panda', 'putter panda', 'deep panda',
        'ocean lotus', 'oceanlotus', 'apt-c-00', 'bitter apt', 'donot team',
        'sidewinder', 'patchwork', 'dropping elephant', 'confucius',
    ]
    
    # Known security/hacking tools
    KNOWN_TOOLS = [
        'metasploit', 'nmap', 'burp suite', 'burpsuite', 'wireshark', 'tcpdump',
        'john the ripper', 'hashcat', 'hydra', 'medusa', 'aircrack', 'aircrack-ng',
        'sqlmap', 'nikto', 'dirb', 'dirbuster', 'gobuster', 'ffuf', 'wfuzz',
        'nuclei', 'subfinder', 'amass', 'masscan', 'zmap', 'shodan', 'censys',
        'maltego', 'recon-ng', 'theharvester', 'spiderfoot', 'osintframework',
        'ghidra', 'ida pro', 'idapro', 'x64dbg', 'ollydbg', 'radare2', 'r2',
        'binary ninja', 'hopper', 'cutter', 'dnspy', 'dotpeek', 'ilspy',
        'procmon', 'process monitor', 'process explorer', 'autoruns', 'sysinternals',
        'volatility', 'rekall', 'autopsy', 'sleuthkit', 'ftk', 'encase',
        'responder', 'impacket', 'crackmapexec', 'evil-winrm', 'winrm',
        'powersploit', 'nishang', 'powerup', 'powercat', 'peas', 'linpeas', 'winpeas',
        'lazagne', 'pypykatz', 'secretsdump', 'kerbrute', 'rubeus', 'kekeo',
        'sharphound', 'adexplorer', 'ldapsearch', 'rpcclient', 'smbclient',
        'enum4linux', 'crackmapexec', 'psexec', 'wmiexec', 'smbexec', 'atexec',
        'chisel', 'ligolo', 'sshuttle', 'proxychains', 'socat', 'plink',
        'ngrok', 'serveo', 'localtunnel', 'cloudflared',
    ]
    
    # Regex patterns for entity extraction
    PATTERNS = {
        'CVE': re.compile(r'\bCVE-\d{4}-\d{4,}\b', re.IGNORECASE),
        'IP': re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
        'IP_V6': re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'),
        'MD5': re.compile(r'\b[a-fA-F0-9]{32}\b'),
        'SHA1': re.compile(r'\b[a-fA-F0-9]{40}\b'),
        'SHA256': re.compile(r'\b[a-fA-F0-9]{64}\b'),
        'DOMAIN': re.compile(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:com|net|org|io|co|info|biz|onion|i2p|bit|crypto|eth|sol|xyz|top|wang|club|online|site|tech|store|shop|app|dev|cloud|ai|ml|cc|tv|me|us|uk|de|fr|ru|cn|jp|br|in|au|ca|nl|it|es|pl|se|no|fi|dk|cz|at|ch|be|pt|gr|tr|mx|ar|za|nz|sg|hk|tw|kr|th|vn|id|my|ph)\b', re.IGNORECASE),
        'URL': re.compile(r'\bhttps?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE),
        'ONION': re.compile(r'\b[a-z2-7]{16,56}\.onion\b', re.IGNORECASE),
        'EMAIL': re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
        'BTC_WALLET': re.compile(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b'),
        'ETH_WALLET': re.compile(r'\b0x[a-fA-F0-9]{40}\b'),
        'PORT': re.compile(r'\bport\s*[:\s]?\s*(\d{1,5})\b', re.IGNORECASE),
        'FILEPATH_WIN': re.compile(r'\b[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*'),
        'FILEPATH_UNIX': re.compile(r'\b/(?:[^/\s]+/)*[^/\s]+'),
        'MITRE_TECHNIQUE': re.compile(r'\bT\d{4}(?:\.\d{3})?\b'),
        'CWE': re.compile(r'\bCWE-\d+\b', re.IGNORECASE),
    }
    
    # Cybersecurity context terms; used by the disambiguation step to decide
    # whether an ambiguous match (e.g. "empire", "hive", "zeus") is in a
    # cybersec context. Word-boundary match against the ±50 char window —
    # naive substring matching produced false positives (e.g. "tor" inside
    # "historical"), so we compile a single \b-anchored alternation regex.
    _CYBER_CONTEXT_TERMS = (
        'malware', 'ransomware', 'trojan', 'rat', 'c2', 'beacon',
        'payload', 'loader', 'stealer', 'backdoor', 'exploit', 'cve',
        'vulnerability', 'compromise', 'infected', 'infection', 'attacker',
        'threat actor', 'apt', 'campaign', 'phishing', 'breach', 'leak',
        'darkweb', 'dark web', 'tor browser', 'tor network',
        'onion', 'ddos', 'botnet', 'forensic', 'incident', 'soc',
        'red team', 'pentest', 'pentester', 'pentesting',
    )
    _CYBER_CONTEXT_REGEX = re.compile(
        r'\b(?:' + '|'.join(re.escape(t) for t in _CYBER_CONTEXT_TERMS) + r')\b',
        re.IGNORECASE
    )

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the NER module.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        nlp_config = config.get('nlp', {})

        self.enabled = nlp_config.get('enable_cybersec_ner', False)
        self.spacy_model = nlp_config.get('ner_model', 'en_core_web_sm')
        self.extract_types = set(nlp_config.get('extract_entities', self.ENTITY_TYPES))
        self.malware_dict_path = nlp_config.get(
            'malware_dict_path',
            'data/dictionaries/malware_families.yaml'
        )

        # spaCy NLP model (optional)
        self.nlp = None

        # Load malware families from external dictionary (falls back to inline
        # KNOWN_MALWARE if the file isn't present). Each entry can flag itself
        # as `requires_context` so generic words like "empire" only fire when
        # surrounded by cybersec terms.
        self._malware_aliases = {}            # alias_lower -> canonical_lower
        self._malware_context_required = set()  # set of canonical_lower
        self._load_malware_dict()
        self._compile_known_entities()

        if self.enabled:
            self._load_spacy()

        logger.info(
            "CybersecNER initialized (enabled=%s, malware_terms=%d, ambiguous=%d)",
            self.enabled, len(self._malware_aliases), len(self._malware_context_required)
        )

    def _load_malware_dict(self) -> None:
        """Load malware families from data/dictionaries/malware_families.yaml.

        Falls back silently to the inline KNOWN_MALWARE list if the file is
        missing or malformed; logs a warning so the operator notices.
        """
        try:
            import yaml
        except ImportError:
            yaml = None

        path = Path(self.malware_dict_path)
        if not path.is_absolute():
            # resolve relative to project root (one up from src/)
            path = Path(__file__).resolve().parent.parent / self.malware_dict_path

        loaded_from_file = False
        if yaml is not None and path.exists():
            try:
                with open(path) as f:
                    entries = yaml.safe_load(f) or []
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    name = (entry.get('name') or '').strip().lower()
                    if not name:
                        continue
                    self._malware_aliases[name] = name
                    for alias in entry.get('aliases', []) or []:
                        self._malware_aliases[alias.strip().lower()] = name
                    if entry.get('requires_context'):
                        self._malware_context_required.add(name)
                loaded_from_file = True
                logger.info(f"Loaded {len(self._malware_aliases)} malware terms from {path}")
            except Exception as e:
                logger.warning(f"Failed to load {path}: {e}; falling back to inline KNOWN_MALWARE")

        if not loaded_from_file:
            # Backward-compat: use the inline KNOWN_MALWARE list as a flat dict
            for term in self.KNOWN_MALWARE:
                self._malware_aliases[term.lower()] = term.lower()
            for term in self.AMBIGUOUS_TERMS:
                # AMBIGUOUS_TERMS were previously *excluded entirely*; with the
                # context check we can now re-include them safely.
                self._malware_aliases.setdefault(term.lower(), term.lower())
                self._malware_context_required.add(term.lower())

    def _is_in_cyber_context(self, text: str, start: int, end: int) -> bool:
        """Window check: are there cybersec keywords within ±50 chars?"""
        lo = max(0, start - 50)
        hi = min(len(text), end + 50)
        window = text[lo:hi]
        return self._CYBER_CONTEXT_REGEX.search(window) is not None

    def _compile_known_entities(self) -> None:
        """Compile patterns for known malware, threat actors, and tools."""
        all_terms = sorted(self._malware_aliases.keys(), key=len, reverse=True)
        if all_terms:
            self.malware_pattern = re.compile(
                r'\b(' + '|'.join(re.escape(m) for m in all_terms) + r')\b',
                re.IGNORECASE
            )
        else:
            # impossible-to-match pattern as a safe fallback
            self.malware_pattern = re.compile(r'(?!x)x')
        self.threat_actor_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(t) for t in self.KNOWN_THREAT_ACTORS) + r')\b',
            re.IGNORECASE
        )
        self.tool_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(t) for t in self.KNOWN_TOOLS) + r')\b',
            re.IGNORECASE
        )
    
    def _load_spacy(self) -> None:
        """Load spaCy model for additional NER."""
        try:
            import spacy
            self.nlp = spacy.load(self.spacy_model)
            logger.info(f"Loaded spaCy model: {self.spacy_model}")
        except ImportError:
            logger.warning("spaCy not installed, using pattern-based NER only")
        except OSError:
            logger.warning(f"spaCy model {self.spacy_model} not found, using pattern-based NER only")
    
    def _extract_pattern_entities(self, text: str) -> List[Entity]:
        """Extract entities using regex patterns."""
        entities = []
        
        # CVE
        if 'CVE' in self.extract_types:
            for match in self.PATTERNS['CVE'].finditer(text):
                entities.append(Entity(
                    text=match.group().upper(),
                    label='CVE',
                    start=match.start(),
                    end=match.end(),
                    metadata={'type': 'vulnerability_id'}
                ))
        
        # CWE
        if 'CVE' in self.extract_types:  # Include with CVE
            for match in self.PATTERNS['CWE'].finditer(text):
                entities.append(Entity(
                    text=match.group().upper(),
                    label='CWE',
                    start=match.start(),
                    end=match.end(),
                    metadata={'type': 'weakness_id'}
                ))
        
        # MITRE ATT&CK Techniques
        for match in self.PATTERNS['MITRE_TECHNIQUE'].finditer(text):
            entities.append(Entity(
                text=match.group(),
                label='MITRE_TECHNIQUE',
                start=match.start(),
                end=match.end(),
                metadata={'type': 'attack_technique'}
            ))
        
        # IP addresses
        if 'IP' in self.extract_types:
            for match in self.PATTERNS['IP'].finditer(text):
                ip = match.group()
                # Filter out common false positives
                if not ip.startswith('0.') and not ip.startswith('127.'):
                    entities.append(Entity(
                        text=ip,
                        label='IP',
                        start=match.start(),
                        end=match.end(),
                        metadata={'type': 'ipv4'}
                    ))
            
            for match in self.PATTERNS['IP_V6'].finditer(text):
                entities.append(Entity(
                    text=match.group(),
                    label='IP',
                    start=match.start(),
                    end=match.end(),
                    metadata={'type': 'ipv6'}
                ))
        
        # Hashes — extract longest-first and reject any shorter match whose span
        # *overlaps* an already-claimed range, not just exact-equals it. Without
        # overlap-aware dedup, the 40-char SHA1 substring of an SHA256 (or the
        # 32-char MD5 substring of an SHA1) is double-counted.
        if 'HASH' in self.extract_types:
            claimed_hash_spans = []  # list of (start, end) already taken

            def _overlaps(s, e):
                for cs, ce in claimed_hash_spans:
                    if s < ce and e > cs:
                        return True
                return False

            # SHA256 first (longest, 64 hex)
            for match in self.PATTERNS['SHA256'].finditer(text):
                s, e = match.start(), match.end()
                if _overlaps(s, e):
                    continue
                claimed_hash_spans.append((s, e))
                entities.append(Entity(
                    text=match.group().lower(),
                    label='HASH', start=s, end=e,
                    metadata={'type': 'sha256'}
                ))

            # SHA1 (40 hex)
            for match in self.PATTERNS['SHA1'].finditer(text):
                s, e = match.start(), match.end()
                if _overlaps(s, e):
                    continue
                claimed_hash_spans.append((s, e))
                entities.append(Entity(
                    text=match.group().lower(),
                    label='HASH', start=s, end=e,
                    metadata={'type': 'sha1'}
                ))

            # MD5 (32 hex)
            for match in self.PATTERNS['MD5'].finditer(text):
                s, e = match.start(), match.end()
                if _overlaps(s, e):
                    continue
                h = match.group().lower()
                if h == '0' * 32 or h == 'f' * 32:
                    continue
                claimed_hash_spans.append((s, e))
                entities.append(Entity(
                    text=h,
                    label='HASH', start=s, end=e,
                    metadata={'type': 'md5'}
                ))
        
        # Domains and URLs
        if 'DOMAIN' in self.extract_types:
            for match in self.PATTERNS['DOMAIN'].finditer(text):
                entities.append(Entity(
                    text=match.group().lower(),
                    label='DOMAIN',
                    start=match.start(),
                    end=match.end()
                ))
            
            for match in self.PATTERNS['ONION'].finditer(text):
                entities.append(Entity(
                    text=match.group().lower(),
                    label='DOMAIN',
                    start=match.start(),
                    end=match.end(),
                    metadata={'type': 'onion'}
                ))
        
        if 'URL' in self.extract_types:
            for match in self.PATTERNS['URL'].finditer(text):
                entities.append(Entity(
                    text=match.group(),
                    label='URL',
                    start=match.start(),
                    end=match.end()
                ))
        
        # Email
        if 'EMAIL' in self.extract_types:
            for match in self.PATTERNS['EMAIL'].finditer(text):
                entities.append(Entity(
                    text=match.group().lower(),
                    label='EMAIL',
                    start=match.start(),
                    end=match.end()
                ))
        
        # Crypto wallets
        if 'CRYPTO_WALLET' in self.extract_types:
            for match in self.PATTERNS['BTC_WALLET'].finditer(text):
                entities.append(Entity(
                    text=match.group(),
                    label='CRYPTO_WALLET',
                    start=match.start(),
                    end=match.end(),
                    metadata={'type': 'bitcoin'}
                ))
            
            for match in self.PATTERNS['ETH_WALLET'].finditer(text):
                entities.append(Entity(
                    text=match.group().lower(),
                    label='CRYPTO_WALLET',
                    start=match.start(),
                    end=match.end(),
                    metadata={'type': 'ethereum'}
                ))
        
        # Ports
        if 'PORT' in self.extract_types:
            for match in self.PATTERNS['PORT'].finditer(text):
                port_num = int(match.group(1))
                if 1 <= port_num <= 65535:
                    entities.append(Entity(
                        text=str(port_num),
                        label='PORT',
                        start=match.start(),
                        end=match.end()
                    ))
        
        # File paths
        if 'FILEPATH' in self.extract_types:
            for match in self.PATTERNS['FILEPATH_WIN'].finditer(text):
                entities.append(Entity(
                    text=match.group(),
                    label='FILEPATH',
                    start=match.start(),
                    end=match.end(),
                    metadata={'type': 'windows'}
                ))
            
            for match in self.PATTERNS['FILEPATH_UNIX'].finditer(text):
                path = match.group()
                # Filter common false positives
                if len(path) > 3 and not path.startswith('//'):
                    entities.append(Entity(
                        text=path,
                        label='FILEPATH',
                        start=match.start(),
                        end=match.end(),
                        metadata={'type': 'unix'}
                    ))
        
        return entities
    
    def _extract_known_entities(self, text: str) -> List[Entity]:
        """Extract known malware, threat actors, and tools."""
        entities = []

        # Malware — apply context-required disambiguation so generic words
        # ("empire", "hive", "zeus") only emit when the surrounding text is
        # cybersec-flavored.
        if 'MALWARE' in self.extract_types:
            for match in self.malware_pattern.finditer(text):
                matched_alias = match.group().lower()
                canonical = self._malware_aliases.get(matched_alias, matched_alias)
                if (canonical in self._malware_context_required
                        and not self._is_in_cyber_context(text, match.start(), match.end())):
                    logger.debug(
                        "Suppressing ambiguous malware match %r at %d (no cyber context)",
                        match.group(), match.start()
                    )
                    continue
                entities.append(Entity(
                    text=match.group(),
                    label='MALWARE',
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9 if canonical not in self._malware_context_required else 0.75,
                    metadata={'canonical': canonical}
                ))
        
        # Threat actors
        if 'THREAT_ACTOR' in self.extract_types:
            for match in self.threat_actor_pattern.finditer(text):
                entities.append(Entity(
                    text=match.group(),
                    label='THREAT_ACTOR',
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9
                ))
        
        # Tools
        if 'TOOL' in self.extract_types:
            for match in self.tool_pattern.finditer(text):
                entities.append(Entity(
                    text=match.group(),
                    label='TOOL',
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9
                ))
        
        return entities
    
    def _extract_spacy_entities(self, text: str) -> List[Entity]:
        """Extract entities using spaCy NER.

        Expanded mapping vs the original (ORG→THREAT_ACTOR, PRODUCT→TOOL):
        - PERSON: emit only if it appears in the threat-actor dictionary
                  (kills generic forum-username false positives).
        - ORG:    emit if it's in the threat-actor dictionary OR if it appears
                  in cyber context (otherwise spaCy's "Apple Inc" etc. floods).
        - GPE:    emit as TARGET_LOCATION only when in cyber context.
        - MONEY:  emit as RANSOM_AMOUNT — these are interesting CTI signals.
        - EVENT:  emit as CAMPAIGN candidate when in cyber context.
        """
        if not self.nlp:
            return []

        entities = []
        try:
            doc = self.nlp(text)
        except Exception as e:
            logger.warning("spaCy parsing failed: %s", e)
            return []

        # Build a single lookup of dictionary-known names (lowercased) so we can
        # cross-check spaCy candidates without rebuilding it per-entity.
        actor_set = set(t.lower() for t in self.KNOWN_THREAT_ACTORS)
        malware_set = set(self._malware_aliases.keys())
        tool_set = set(t.lower() for t in self.KNOWN_TOOLS)

        for ent in doc.ents:
            label = ent.label_
            text_lc = ent.text.lower()
            in_cyber = self._is_in_cyber_context(text, ent.start_char, ent.end_char)

            mapped = None
            confidence = 0.7
            metadata = {'source': 'spacy', 'original_label': label}

            # NER discipline: spaCy only emits an entity when its text matches
            # an item in our static dictionaries. Without this, generic nouns
            # ("Child", "Preteen", "Gay", "Family") get tagged PRODUCT by
            # spaCy and were promoted to TOOL — completely wrong on dark-web
            # forum text. Dictionary cross-check eliminates that whole class
            # of noise. The "in_cyber" weak-signal fallbacks are also gone
            # for the same reason.
            if label == 'ORG':
                if text_lc in actor_set:
                    mapped = 'THREAT_ACTOR'
                    confidence = 0.9
                elif text_lc in malware_set:
                    mapped = 'MALWARE'
                    confidence = 0.9
                # No `in_cyber` fallback — generates false-positive ORGs
                # ("Microsoft", "Google", random forum names).
            elif label == 'PRODUCT':
                if text_lc in tool_set:
                    mapped = 'TOOL'
                    confidence = 0.9
                # No fallback — was the source of "Child"/"Preteen"/etc. junk.
            elif label == 'PERSON':
                if text_lc in actor_set:
                    mapped = 'THREAT_ACTOR'
                    confidence = 0.85
                # else: skip — too noisy on forum-username-heavy text
            elif label == 'GPE' and in_cyber:
                mapped = 'TARGET_LOCATION'
                confidence = 0.6
            elif label == 'MONEY' and in_cyber:
                mapped = 'RANSOM_AMOUNT'
                confidence = 0.7
            elif label == 'EVENT' and in_cyber:
                mapped = 'CAMPAIGN'
                confidence = 0.6

            if mapped and (mapped in self.extract_types or mapped in
                           ('TARGET_LOCATION', 'RANSOM_AMOUNT', 'CAMPAIGN')):
                entities.append(Entity(
                    text=ent.text,
                    label=mapped,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=confidence,
                    metadata=metadata
                ))

        return entities
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate and overlapping entities."""
        if not entities:
            return []
        
        # Sort by start position, then by length (longer first)
        sorted_entities = sorted(entities, key=lambda e: (e.start, -(e.end - e.start)))
        
        result = []
        last_end = -1
        
        for entity in sorted_entities:
            # Skip if overlapping with previous entity
            if entity.start < last_end:
                continue
            result.append(entity)
            last_end = entity.end
        
        return result
    
    def extract(self, text: str) -> List[Entity]:
        """
        Extract cybersecurity entities from text.

        Args:
            text: Text to extract entities from

        Returns:
            List of extracted entities
        """
        if not self.enabled or not text:
            return []

        all_entities = []

        # Pattern-based extraction
        all_entities.extend(self._extract_pattern_entities(text))

        # Known entities extraction
        all_entities.extend(self._extract_known_entities(text))

        # spaCy extraction
        all_entities.extend(self._extract_spacy_entities(text))

        # Optional supplemental IOC extraction via iocsearcher (Apache-2.0).
        # Activated by `pip install iocsearcher`; handles defanged IOCs and
        # several formats the inline regex misses. Pure addition — never
        # replaces the regex pass, just adds anything the regex didn't catch.
        all_entities.extend(self._extract_iocsearcher_entities(text))

        # Deduplicate
        entities = self._deduplicate_entities(all_entities)

        return entities

    def _extract_iocsearcher_entities(self, text: str) -> List[Entity]:
        """Augment with iocsearcher IOC types when the library is installed."""
        try:
            from iocsearcher.searcher import Searcher  # type: ignore
        except ImportError:
            return []

        try:
            if not hasattr(self, '_iocsearcher'):
                self._iocsearcher = Searcher()
            results = self._iocsearcher.search_data(text)
        except Exception as e:
            logger.debug("iocsearcher failed (continuing with regex IOCs): %s", e)
            return []

        # iocsearcher returns a list of (type, value, ...) tuples or dicts depending
        # on version; normalize defensively.
        type_map = {
            'url': 'URL', 'fqdn': 'DOMAIN', 'ip4': 'IP', 'ipv6': 'IP',
            'email': 'EMAIL', 'md5': 'HASH', 'sha1': 'HASH', 'sha256': 'HASH',
            'cve': 'CVE', 'btc': 'CRYPTO_WALLET', 'eth': 'CRYPTO_WALLET',
            'onion': 'DOMAIN',
        }
        entities = []
        for result in results:
            if isinstance(result, dict):
                ioc_type = result.get('type', '').lower()
                value = result.get('value', '')
            elif isinstance(result, (list, tuple)) and len(result) >= 2:
                ioc_type, value = str(result[0]).lower(), str(result[1])
            else:
                continue
            label = type_map.get(ioc_type)
            if not label or label not in self.extract_types:
                continue
            # Locate the first occurrence in text for span info; iocsearcher
            # gives the value but not always positions.
            idx = text.lower().find(value.lower())
            if idx < 0:
                idx = 0
            entities.append(Entity(
                text=value, label=label, start=idx, end=idx + len(value),
                confidence=0.85,
                metadata={'source': 'iocsearcher', 'ioc_type': ioc_type}
            ))
        return entities
    
    def extract_batch(self, texts: List[str]) -> List[List[Entity]]:
        """
        Extract entities from multiple texts.
        
        Args:
            texts: List of texts
            
        Returns:
            List of entity lists
        """
        return [self.extract(text) for text in texts]
    
    def entities_to_dict(self, entities: List[Entity]) -> List[Dict[str, Any]]:
        """Convert entities to dictionary format."""
        return [
            {
                'text': e.text,
                'label': e.label,
                'start': e.start,
                'end': e.end,
                'confidence': e.confidence,
                'metadata': e.metadata
            }
            for e in entities
        ]
    
    def get_entity_summary(self, entities: List[Entity]) -> Dict[str, List[str]]:
        """
        Get summary of entities grouped by type.
        
        Args:
            entities: List of entities
            
        Returns:
            Dictionary of entity type -> list of entity texts
        """
        summary = defaultdict(list)
        for entity in entities:
            if entity.text not in summary[entity.label]:
                summary[entity.label].append(entity.text)
        return dict(summary)
    
    def get_iocs(self, entities: List[Entity]) -> Dict[str, List[str]]:
        """
        Get Indicators of Compromise (IOCs) from entities.
        
        Args:
            entities: List of entities
            
        Returns:
            Dictionary of IOC type -> list of IOC values
        """
        ioc_types = {'IP', 'HASH', 'DOMAIN', 'URL', 'EMAIL', 'CRYPTO_WALLET'}
        iocs = defaultdict(list)
        
        for entity in entities:
            if entity.label in ioc_types:
                if entity.text not in iocs[entity.label]:
                    iocs[entity.label].append(entity.text)
        
        return dict(iocs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get NER statistics."""
        return {
            'enabled': self.enabled,
            'spacy_loaded': self.nlp is not None,
            'extract_types': list(self.extract_types),
            'known_malware_count': len(self.KNOWN_MALWARE),
            'known_threat_actors_count': len(self.KNOWN_THREAT_ACTORS),
            'known_tools_count': len(self.KNOWN_TOOLS),
        }
