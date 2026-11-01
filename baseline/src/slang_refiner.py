"""
Cyber Slang Refiner for DarkWeb Translation Pipeline
Post-edit refinement using LLM to clarify cybersecurity slang, acronyms, and informal expressions.
Based on Algorithm 2 lines 26-28 from the paper.

Supports:
- OpenAI GPT-3.5 API
- Local models via transformers (Mistral, Llama)
- Caching for repeated slang patterns
"""

import re
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


class SlangRefiner:
    """
    Refines translated text by clarifying cybersecurity slang and acronyms.
    Uses LLM (GPT-3.5 or local Mistral/Llama) for post-edit refinement.
    """
    
    # Common cybersecurity slang/acronyms that need clarification
    CYBER_SLANG = {
        'rat': 'Remote Access Trojan (RAT)',
        'apt': 'Advanced Persistent Threat (APT)',
        'ttp': 'Tactics, Techniques, and Procedures (TTP)',
        'ioc': 'Indicator of Compromise (IOC)',
        'c2': 'Command and Control (C2)',
        'c&c': 'Command and Control (C&C)',
        'poc': 'Proof of Concept (PoC)',
        'rce': 'Remote Code Execution (RCE)',
        'lfi': 'Local File Inclusion (LFI)',
        'rfi': 'Remote File Inclusion (RFI)',
        'sqli': 'SQL Injection (SQLi)',
        'xss': 'Cross-Site Scripting (XSS)',
        'csrf': 'Cross-Site Request Forgery (CSRF)',
        'ssrf': 'Server-Side Request Forgery (SSRF)',
        'idor': 'Insecure Direct Object Reference (IDOR)',
        'bof': 'Buffer Overflow (BOF)',
        'dos': 'Denial of Service (DoS)',
        'ddos': 'Distributed Denial of Service (DDoS)',
        'mitm': 'Man-in-the-Middle (MitM)',
        'osint': 'Open Source Intelligence (OSINT)',
        'opsec': 'Operational Security (OPSEC)',
        'soc': 'Security Operations Center (SOC)',
        'siem': 'Security Information and Event Management (SIEM)',
        'edr': 'Endpoint Detection and Response (EDR)',
        'av': 'Antivirus (AV)',
        'ids': 'Intrusion Detection System (IDS)',
        'ips': 'Intrusion Prevention System (IPS)',
        'waf': 'Web Application Firewall (WAF)',
        'vpn': 'Virtual Private Network (VPN)',
        'tor': 'The Onion Router (Tor)',
        'pwn': 'compromise/exploit (pwn)',
        'pwned': 'compromised/exploited (pwned)',
        '0day': 'zero-day vulnerability (0day)',
        'zeroday': 'zero-day vulnerability',
        'creds': 'credentials',
        'cred': 'credential',
        'privesc': 'privilege escalation',
        'priv esc': 'privilege escalation',
        'lat mov': 'lateral movement',
        'lateral mov': 'lateral movement',
        'exfil': 'exfiltration',
        'phish': 'phishing',
        'spearphish': 'spear phishing',
        'worm': 'self-propagating malware (worm)',
        'rootkit': 'rootkit (kernel-level malware)',
        'keylogger': 'keystroke logger (keylogger)',
        'ransomware': 'ransomware (encryption-based extortion malware)',
        'crypter': 'crypter (malware obfuscation tool)',
        'packer': 'packer (executable compression/obfuscation tool)',
        'dropper': 'dropper (malware delivery component)',
        'loader': 'loader (malware delivery component)',
        'stager': 'stager (initial payload component)',
        'beacon': 'beacon (C2 communication component)',
        'implant': 'implant (persistent backdoor)',
        'webshell': 'web shell (web-based backdoor)',
        'rev shell': 'reverse shell',
        'bind shell': 'bind shell',
        'meterpreter': 'Meterpreter (Metasploit payload)',
        'msf': 'Metasploit Framework (MSF)',
        'burp': 'Burp Suite (web security testing tool)',
        'nmap': 'Nmap (network scanner)',
        'mimikatz': 'Mimikatz (credential extraction tool)',
        'cobaltstrike': 'Cobalt Strike (adversary simulation tool)',
        'cs': 'Cobalt Strike (CS)',
        'bloodhound': 'BloodHound (AD enumeration tool)',
        'hashcat': 'Hashcat (password cracker)',
        'jtr': 'John the Ripper (password cracker)',
        'hydra': 'Hydra (brute force tool)',
        'sqlmap': 'SQLMap (SQL injection tool)',
        'ghidra': 'Ghidra (reverse engineering tool)',
        'ida': 'IDA Pro (disassembler)',
        'ollydbg': 'OllyDbg (debugger)',
        'x64dbg': 'x64dbg (debugger)',
        'dox': 'dox (publish personal information)',
        'doxxed': 'doxxed (had personal information published)',
        'dump': 'data dump (leaked database)',
        'combolist': 'combo list (username/password pairs)',
        'fullz': 'fullz (complete identity information)',
        'cvv': 'CVV (card verification value)',
        'bin': 'BIN (bank identification number)',
        'skimmer': 'skimmer (card data theft device)',
        'carder': 'carder (credit card fraudster)',
        'se': 'social engineering (SE)',
        'vishing': 'voice phishing (vishing)',
        'smishing': 'SMS phishing (smishing)',
    }
    
    # System prompt for LLM refinement
    SYSTEM_PROMPT = """You are an expert cybersecurity analyst. Your task is to clarify translations involving cybersecurity slang, acronyms, and informal expressions into clear and accurate cybersecurity terminology.

Rules:
1. Expand acronyms on first use (e.g., "RAT" -> "Remote Access Trojan (RAT)")
2. Clarify slang terms (e.g., "pwned" -> "compromised")
3. Keep the original meaning and context
4. Do not add information that wasn't in the original
5. If the text is already clear, return it unchanged
6. Preserve technical details like CVE numbers, IP addresses, hashes

Examples:
- "Just dropped a RAT on their network, easy creds now." -> "I just deployed a Remote Access Trojan (RAT) onto their network, gaining easy access to credentials."
- "Got 0day for this CVE, works on unpatched boxes" -> "I have a zero-day exploit for this CVE, it works on unpatched systems."
- "Pwned the AD, now doing lat mov to DC" -> "Compromised the Active Directory, now performing lateral movement to the Domain Controller."
"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the slang refiner.
        
        Args:
            config: Configuration dictionary with refinement settings
        """
        self.config = config
        refinement_config = config.get('refinement', {})
        
        self.enabled = refinement_config.get('enabled', False)
        self.model_type = refinement_config.get('model_type', 'local')  # 'openai' or 'local'
        # Default to Qwen2.5-7B-Instruct (Apache-2.0; ~15GB BF16 — fits 4090 Ti
        # alongside translators, runs comfortably on DGX Spark). Swappable to
        # Mistral via the `model_name` config key for paper alignment.
        self.model_name = refinement_config.get('model_name', 'Qwen/Qwen2.5-7B-Instruct')
        self.openai_api_key = refinement_config.get('openai_api_key', None)
        self.cache_enabled = refinement_config.get('cache_enabled', True)
        self.cache_dir = Path(refinement_config.get('cache_dir', 'data/refinement_cache'))
        self.batch_size = refinement_config.get('batch_size', 8)
        self.max_text_length = refinement_config.get('max_text_length', 2000)
        self.min_slang_count = refinement_config.get('min_slang_count', 1)
        # Cap LLM generation so a long input can't trigger a 10+ second call.
        # 256 is plenty for a refinement that mostly substitutes slang inline.
        self.max_new_tokens = refinement_config.get('max_new_tokens', 256)
        # Watchdog: kill an LLM call that exceeds this and fall back to dict
        # refinement, rather than stalling the entire pipeline.
        self.timeout_s = float(refinement_config.get('timeout_s', 30.0))
        
        # Initialize model
        self.model = None
        self.tokenizer = None
        self.openai_client = None
        
        # Initialize cache
        self._cache: Dict[str, str] = {}
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_cache()
        
        if self.enabled:
            self._initialize_model()
        
        logger.info(f"SlangRefiner initialized (enabled={self.enabled}, model_type={self.model_type})")
    
    def _initialize_model(self) -> None:
        """Initialize the LLM model based on configuration."""
        if self.model_type == 'openai':
            self._initialize_openai()
        else:
            self._initialize_local_model()
    
    def _initialize_openai(self) -> None:
        """Initialize OpenAI client."""
        try:
            import openai
            if self.openai_api_key:
                self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized")
            else:
                logger.warning("OpenAI API key not provided, refinement disabled")
                self.enabled = False
        except ImportError:
            logger.warning("openai package not installed, falling back to local model")
            self.model_type = 'local'
            self._initialize_local_model()
    
    def _initialize_local_model(self) -> None:
        """Initialize local model (Mistral/Llama) via transformers."""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            logger.info(f"Loading local model: {self.model_name}")
            
            # Check for GPU
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=self.config['paths'].get('models_cache', 'models')
            )
            
            # Load model with appropriate settings
            if device == "cuda":
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    cache_dir=self.config['paths'].get('models_cache', 'models')
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    cache_dir=self.config['paths'].get('models_cache', 'models')
                )
            
            logger.info(f"Local model loaded on {device}")
            
        except Exception as e:
            logger.error(f"Failed to load local model: {e}")
            logger.info("Falling back to dictionary-based refinement only")
            self.model = None
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        cache_file = self.cache_dir / "slang_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} cached refinements")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self._cache = {}
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        if not self.cache_enabled:
            return
        
        cache_file = self.cache_dir / "slang_cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _count_slang_terms(self, text: str) -> int:
        """Count cybersecurity slang terms in text."""
        text_lower = text.lower()
        count = 0
        for slang in self.CYBER_SLANG.keys():
            # Use word boundary matching
            pattern = r'\b' + re.escape(slang) + r'\b'
            if re.search(pattern, text_lower):
                count += 1
        return count
    
    def _needs_refinement(self, text: str) -> bool:
        """Check if text needs LLM refinement (has enough slang terms)."""
        return self._count_slang_terms(text) >= self.min_slang_count
    
    def _dictionary_refine(self, text: str) -> str:
        """
        Apply dictionary-based slang expansion (fast, no LLM).
        Expands acronyms on first occurrence.
        """
        refined = text
        expanded = set()  # Track already expanded terms
        
        for slang, expansion in self.CYBER_SLANG.items():
            # Only expand if not already expanded
            if slang.lower() not in expanded:
                # Case-insensitive replacement with word boundaries
                pattern = r'\b(' + re.escape(slang) + r')\b'
                match = re.search(pattern, refined, re.IGNORECASE)
                if match:
                    # Only expand first occurrence
                    original = match.group(1)
                    # Preserve original case for the acronym in parentheses
                    if '(' in expansion:
                        # Already has acronym, just use expansion
                        replacement = expansion
                    else:
                        replacement = expansion
                    
                    refined = re.sub(pattern, replacement, refined, count=1, flags=re.IGNORECASE)
                    expanded.add(slang.lower())
        
        return refined
    
    def _llm_refine_openai(self, text: str) -> str:
        """Refine text using OpenAI GPT-3.5."""
        if not self.openai_client:
            return text
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Clarify this cybersecurity text:\n\n{text}"}
                ],
                max_tokens=len(text) + 200,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI refinement failed: {e}")
            return text
    
    def _build_prompt(self, text: str) -> str:
        """Build the LLM prompt using the model's chat template when available
        (Qwen, Llama-3, recent models) and falling back to Mistral's
        [INST]...[/INST] convention otherwise. Different families need
        different prompt formats; using the tokenizer's built-in template is
        the only way to stay neutral."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Clarify this cybersecurity text:\n\n{text}"},
        ]
        try:
            return self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except (AttributeError, ValueError):
            return (f"<s>[INST] {self.SYSTEM_PROMPT}\n\n"
                    f"Clarify this cybersecurity text:\n\n{text}\n[/INST]")

    def _generate_with_timeout(self, inputs):
        """Run model.generate() in a thread; if it doesn't return within
        timeout_s, abandon it and return None. The hung thread becomes a
        daemon so it doesn't prevent process exit; we accept the orphaned
        compute as the price of bounded wall time."""
        import threading
        import torch

        result_holder: List = [None, None]

        def _worker():
            try:
                with torch.no_grad():
                    out = self.model.generate(
                        **inputs,
                        max_new_tokens=self.max_new_tokens,
                        temperature=0.3,
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id,
                    )
                result_holder[0] = out
            except BaseException as e:  # noqa
                result_holder[1] = e

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join(timeout=self.timeout_s)
        if t.is_alive():
            logger.warning(
                "LLM generate exceeded %ss; abandoning thread and falling back to dict refinement",
                self.timeout_s
            )
            return None
        if result_holder[1] is not None:
            logger.warning(f"LLM generate raised: {result_holder[1]}")
            return None
        return result_holder[0]

    def _llm_refine_local(self, text: str) -> str:
        """Refine text using local model. Bounded by timeout + max_new_tokens."""
        if not self.model or not self.tokenizer:
            return text

        try:
            prompt = self._build_prompt(text)
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
            if hasattr(self.model, 'device'):
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            outputs = self._generate_with_timeout(inputs)
            if outputs is None:
                return text  # timeout / error: dictionary path will run

            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Try to peel off the prompt prefix; both chat-templated and
            # [INST]-style prompts end with the response right after.
            if '[/INST]' in full_response:
                response = full_response.split('[/INST]')[-1].strip()
            elif 'assistant' in full_response.lower():
                # Qwen chat template ends with "<|im_start|>assistant\n"
                response = full_response.rsplit('assistant', 1)[-1].strip()
            else:
                response = full_response[len(prompt):].strip()
            return response if response else text

        except Exception as e:
            logger.warning(f"Local model refinement failed: {e}")
            return text
    
    def refine(self, text: str) -> Tuple[str, bool]:
        """
        Refine translated text by clarifying cybersecurity slang.
        
        Args:
            text: Translated text to refine
            
        Returns:
            Tuple of (refined_text, was_refined)
        """
        if not self.enabled or not text:
            return text, False
        
        # Check cache first
        if self.cache_enabled:
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                return self._cache[cache_key], True
        
        # Truncate if too long
        original_text = text
        if len(text) > self.max_text_length:
            text = text[:self.max_text_length]
        
        # Check if refinement is needed
        if not self._needs_refinement(text):
            # Still apply dictionary refinement for consistency
            refined = self._dictionary_refine(text)
            was_refined = refined != text
            return refined, was_refined
        
        # Apply LLM refinement
        if self.model_type == 'openai' and self.openai_client:
            refined = self._llm_refine_openai(text)
        elif self.model:
            refined = self._llm_refine_local(text)
        else:
            # Fallback to dictionary-only
            refined = self._dictionary_refine(text)
        
        # Cache result
        if self.cache_enabled and refined != original_text:
            self._cache[cache_key] = refined
            # Periodically save cache
            if len(self._cache) % 100 == 0:
                self._save_cache()
        
        return refined, refined != original_text
    
    def refine_batch(self, texts: List[str]) -> List[Tuple[str, bool]]:
        """
        Refine a batch of texts.
        
        Args:
            texts: List of texts to refine
            
        Returns:
            List of (refined_text, was_refined) tuples
        """
        results = []
        for text in texts:
            results.append(self.refine(text))
        return results
    
    def cleanup(self) -> None:
        """Cleanup resources and save cache."""
        if self.cache_enabled:
            self._save_cache()
        
        # Clear model from memory
        if self.model is not None:
            del self.model
            self.model = None
        
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        logger.info("SlangRefiner cleaned up")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get refinement statistics."""
        return {
            'enabled': self.enabled,
            'model_type': self.model_type,
            'model_name': self.model_name,
            'cache_size': len(self._cache),
            'slang_dictionary_size': len(self.CYBER_SLANG)
        }
