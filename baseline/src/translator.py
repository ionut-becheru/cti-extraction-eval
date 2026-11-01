"""
Translator for DarkWeb Translation Pipeline
Manages multiple translation models and performs GPU-optimized batch translation.
"""

import logging
import re
import time
from typing import List, Dict, Tuple, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from collections import defaultdict

logger = logging.getLogger(__name__)


class TranslationModel:
    """Wrapper for a single translation model."""
    
    def __init__(self, model_name: str, device: str, use_fp16: bool = False):
        """
        Initialize translation model.

        Args:
            model_name: HuggingFace model identifier
            device: Device to load model on ('cuda' or 'cpu')
            use_fp16: Whether to use mixed precision (fp16)
        """
        self.model_name = model_name
        self.device = device
        self.use_fp16 = use_fp16
        self.tokenizer = None
        self.model = None
        self.load_time = None
        self._is_half = False  # explicit tracking; never .half() a half model

    def _model_dtype(self):
        if self.model is None:
            return None
        try:
            return next(self.model.parameters()).dtype
        except StopIteration:
            return None

    def _ensure_precision(self, want_half: bool) -> None:
        """Cast model to the requested precision exactly once. Idempotent."""
        if self.model is None:
            return
        current_half = self._model_dtype() == torch.float16
        if want_half and not current_half:
            self.model = self.model.half()
            self._is_half = True
        elif not want_half and current_half:
            self.model = self.model.float()
            self._is_half = False

    def load(self) -> None:
        """Load the model and tokenizer."""
        if self.model is not None:
            return  # Already loaded

        start_time = time.time()
        logger.info(f"Loading translation model: {self.model_name}")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)

            if self.device == 'cuda' and torch.cuda.is_available():
                try:
                    self.model = self.model.to(self.device)
                    if self.use_fp16:
                        self._ensure_precision(want_half=True)
                        logger.info("Using fp16 (mixed precision)")
                except RuntimeError as cuda_error:
                    logger.warning(f"CUDA error during load: {cuda_error}; falling back to CPU fp32")
                    self.device = 'cpu'
                    self.use_fp16 = False
                    self.model = self.model.to('cpu')
                    # Critical: undo any half-cast so CPU inference doesn't run on fp16
                    # (CPU fp16 ops error out or produce NaN for many seq2seq layers).
                    self._ensure_precision(want_half=False)

            self.model.eval()
            self.load_time = time.time() - start_time
            logger.info(f"Model loaded on {self.device} in {self.load_time:.2f}s "
                        f"(dtype={self._model_dtype()})")

        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise

    def offload_to_cpu(self) -> None:
        """Move model to CPU RAM to free GPU VRAM (faster than full reload)."""
        if self.model is not None and self.device != 'cpu':
            self.model = self.model.to('cpu')
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"Offloaded model to CPU RAM: {self.model_name}")

    def reload_to_gpu(self) -> None:
        """Move model back to GPU from CPU RAM."""
        if self.model is not None and torch.cuda.is_available():
            self.model = self.model.to('cuda')
            # Idempotent precision adjustment - safe to call repeatedly.
            self._ensure_precision(want_half=self.use_fp16)
            logger.info(f"Reloaded model to GPU: {self.model_name} (dtype={self._model_dtype()})")

    def unload(self) -> None:
        """Unload the model to free memory."""
        if self.model is not None:
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info(f"Unloaded model: {self.model_name}")
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None
    
    # ISO-639-1 → BCP-47+script codes accepted by NLLB. Covers the languages
    # listed in our translator config; others fall through to "eng_Latn" which
    # NLLB then identifies on its own (slightly less accurate but won't crash).
    _NLLB_LANG_CODES = {
        'ru': 'rus_Cyrl', 'de': 'deu_Latn', 'fr': 'fra_Latn', 'es': 'spa_Latn',
        'it': 'ita_Latn', 'pt': 'por_Latn', 'nl': 'nld_Latn', 'pl': 'pol_Latn',
        'cs': 'ces_Latn', 'sv': 'swe_Latn', 'no': 'nob_Latn', 'da': 'dan_Latn',
        'fi': 'fin_Latn', 'et': 'est_Latn', 'tr': 'tur_Latn', 'ar': 'arb_Arab',
        'he': 'heb_Hebr', 'zh': 'zho_Hans', 'ja': 'jpn_Jpan', 'ko': 'kor_Hang',
        'vi': 'vie_Latn', 'th': 'tha_Thai', 'id': 'ind_Latn', 'hi': 'hin_Deva',
        'bg': 'bul_Cyrl', 'el': 'ell_Grek', 'ro': 'ron_Latn', 'uk': 'ukr_Cyrl',
        'hr': 'hrv_Latn', 'sk': 'slk_Latn', 'sl': 'slv_Latn', 'lt': 'lit_Latn',
        'lv': 'lvs_Latn', 'ca': 'cat_Latn', 'mk': 'mkd_Cyrl',
    }

    def _is_nllb_model(self) -> bool:
        return 'nllb' in (self.model_name or '').lower()

    def translate_batch(self, texts: List[str], max_length: int = 512,
                       num_beams: int = 4, early_stopping: bool = True,
                       source_lang: Optional[str] = None) -> List[str]:
        """
        Translate a batch of texts.

        Args:
            texts: List of texts to translate
            max_length: Maximum length of generated translation
            num_beams: Number of beams for beam search
            early_stopping: Whether to stop early in beam search
            source_lang: ISO-639-1 source language (e.g. 'ru'). Only used when
                this model is NLLB-style — NLLB needs both the tokenizer's
                `src_lang` set to a BCP-47+script code (e.g. 'rus_Cyrl') and
                a `forced_bos_token_id` for the target language. MarianMT
                models embed that information in the model itself and ignore
                this argument.

        Returns:
            List of translated texts
        """
        if not self.is_loaded():
            self.load()

        try:
            # NLLB requires source-language hint on the tokenizer + forced
            # BOS for the target language. Set them per call so a single
            # NLLB instance can serve multiple source languages.
            forced_bos_id = None
            if self._is_nllb_model() and source_lang:
                src = self._NLLB_LANG_CODES.get(source_lang, 'eng_Latn')
                self.tokenizer.src_lang = src
                eng_id = self.tokenizer.convert_tokens_to_ids('eng_Latn')
                if eng_id is not None and eng_id != self.tokenizer.unk_token_id:
                    forced_bos_id = eng_id

            inputs = self.tokenizer(
                texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=max_length
            )

            if self.device == 'cuda' and torch.cuda.is_available():
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generation. `no_repeat_ngram_size=3` + `repetition_penalty=1.3`
            # defang MarianMT's degenerate-loop failure mode (input >512 tok
            # + greedy decoding → "German, German, German..." for thousands
            # of tokens). They cost <5% throughput and are safe for short
            # inputs and for NLLB.
            gen_kwargs = dict(
                max_length=max_length,
                num_beams=num_beams,
                early_stopping=early_stopping,
                no_repeat_ngram_size=3,
                repetition_penalty=1.3,
            )
            if forced_bos_id is not None:
                gen_kwargs['forced_bos_token_id'] = forced_bos_id

            with torch.no_grad():
                outputs = self.model.generate(**inputs, **gen_kwargs)

            translations = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
            return translations
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise


class Translator:
    """Manages multiple translation models and performs batch translation."""
    
    def __init__(self, config: Dict):
        """
        Initialize translator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.language_models = config['translation']['language_models']
        self.fallback_model_name = config['translation']['fallback_model']
        self.translation_batch_size = config['translation']['translation_batch_size']
        self.max_length = config['translation']['max_length']
        self.num_beams = config['translation']['num_beams']
        self.early_stopping = config['translation']['early_stopping']
        self.max_retries = config['translation']['max_retries']
        self.retry_beam_sizes = config['translation']['retry_beam_sizes']
        
        # GPU settings
        self.device = config['gpu']['device'] if config['gpu']['enabled'] else 'cpu'
        self.use_fp16 = config['gpu']['mixed_precision']
        self.max_models_in_memory = config['gpu']['max_models_in_memory']
        
        # Check GPU availability
        if self.device == 'cuda' and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            self.device = 'cpu'
            self.use_fp16 = False
        
        # Model cache (GPU) and CPU offload cache (uses RAM instead of VRAM)
        self.loaded_models: Dict[str, TranslationModel] = {}
        self.model_usage_count: Dict[str, int] = defaultdict(int)
        self._cpu_cache: Dict[str, TranslationModel] = {}  # Models offloaded to RAM

        # Per-run failure attribution so we can stat-summarize at end of run instead
        # of only seeing scattered log lines for thousands of silent empty translations.
        self.failure_stats: Dict[str, int] = defaultdict(int)

        logger.info(f"Translator initialized with device: {self.device}")

    @staticmethod
    def _is_degenerate(translation: str, min_unique_ratio: float = 0.20,
                       min_length: int = 60) -> bool:
        """Detect MarianMT's degenerate-repetition output.

        Symptom: the model outputs the same word or short phrase hundreds of
        times in a row (e.g. "German, German, German..." 800x). Heuristic:
        word-level unique-ratio. A normal translation has 60-90% unique words;
        a degenerate one has <20%. Only applied to outputs above ``min_length``
        so we don't flag short legitimate translations like "Yes." or "OK".
        """
        if not translation or len(translation) < min_length:
            return False
        words = translation.split()
        if len(words) < 20:
            return False
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < min_unique_ratio:
            return True
        # Also catch the "X. X. X." pattern: same 1-3 word fragment repeated
        # via punctuation (slips past the unique-word check sometimes).
        chunks = [c.strip() for c in translation.split(".") if c.strip()]
        if len(chunks) >= 10:
            unique_chunk_ratio = len(set(chunks)) / len(chunks)
            if unique_chunk_ratio < 0.30:
                return True
        return False
    
    def _get_model_name(self, language_code: str) -> str:
        """
        Get the appropriate model name for a language.

        Strategy controlled by config['translation']['strategy']:
          - "marian"  (default-legacy): use the per-language Helsinki MarianMT
              model when available, fall back to NLLB-200 only for unsupported
              languages. Fast (~300 MB models) but loses Russian-specific
              entities on long forum text per local benchmarks.
          - "nllb"    (recommended):    always use the configured fallback
              (NLLB-200-distilled-600M by default). One model, 200 languages,
              better entity preservation on long inputs. ~1.2 GB resident.
          - "auto":                     same as marian unless input is very
              long (chunked) and the language has known degenerate behavior;
              currently equivalent to marian.
        """
        strategy = self.config.get('translation', {}).get('strategy', 'marian')
        if strategy == 'nllb':
            return self.fallback_model_name
        return self.language_models.get(language_code, self.fallback_model_name)
    
    def _load_model(self, model_name: str) -> TranslationModel:
        """
        Load a translation model, managing memory.
        
        Args:
            model_name: Model identifier
            
        Returns:
            Loaded TranslationModel
        """
        # If already loaded on GPU, return it
        if model_name in self.loaded_models:
            model = self.loaded_models[model_name]
            self.model_usage_count[model_name] += 1
            # If it was offloaded to CPU, move it back to GPU
            if model.is_loaded() and model.model is not None and str(next(model.model.parameters()).device) == 'cpu' and self.device == 'cuda':
                model.reload_to_gpu()
            return model
        
        # Check if model is in CPU cache (offloaded but not deleted)
        if model_name in self._cpu_cache:
            model = self._cpu_cache.pop(model_name)
            model.reload_to_gpu()
            self.loaded_models[model_name] = model
            self.model_usage_count[model_name] = 1
            return model
        
        # Need to make room if at GPU capacity
        if len(self.loaded_models) >= self.max_models_in_memory:
            # Offload least recently used model to CPU RAM instead of deleting
            lru_model = min(self.model_usage_count.items(), key=lambda x: x[1])
            lru_model_name = lru_model[0]
            self.loaded_models[lru_model_name].offload_to_cpu()
            self._cpu_cache[lru_model_name] = self.loaded_models[lru_model_name]
            del self.loaded_models[lru_model_name]
            del self.model_usage_count[lru_model_name]
        
        # Load new model from disk
        model = TranslationModel(model_name, self.device, self.use_fp16)
        model.load()
        self.loaded_models[model_name] = model
        self.model_usage_count[model_name] = 1
        
        return model
    
    # Sentence-boundary regex shared by chunked translation. Conservative —
    # splits on . ! ? followed by whitespace, plus paragraph breaks. Avoids
    # spaCy because we want this fast and language-agnostic.
    _CHUNK_SPLIT_RE = re.compile(r'(?<=[.!?])\s+|\n{2,}')

    def _chunk_text(self, text: str, tokenizer, max_tokens: int = 400) -> List[str]:
        """Split long text into sentence-bounded chunks of ≤max_tokens.

        MarianMT and NLLB cap at 512 input tokens; pushing past that produces
        truncated, incoherent output (and on greedy decoding, sometimes the
        degenerate "X X X..." loop). This greedy packer keeps chunks at
        ≤400 tokens (safety margin) while preserving sentence boundaries so
        translations rejoin cleanly. Run-on sentences longer than the cap are
        hard-sliced as a last resort.
        """
        sentences = [s.strip() for s in self._CHUNK_SPLIT_RE.split(text) if s.strip()]
        if not sentences:
            return [text]
        chunks: List[str] = []
        current: List[str] = []
        current_tok = 0
        for sent in sentences:
            sent_tok = len(tokenizer(sent, add_special_tokens=False)['input_ids'])
            if sent_tok > max_tokens:
                if current:
                    chunks.append(' '.join(current))
                    current, current_tok = [], 0
                ids = tokenizer(sent, add_special_tokens=False)['input_ids']
                for i in range(0, len(ids), max_tokens):
                    chunks.append(tokenizer.decode(ids[i:i + max_tokens]))
                continue
            if current_tok + sent_tok > max_tokens and current:
                chunks.append(' '.join(current))
                current, current_tok = [], 0
            current.append(sent)
            current_tok += sent_tok
        if current:
            chunks.append(' '.join(current))
        return chunks

    def translate_text(self, text: str, language_code: str) -> Tuple[str, bool, str]:
        """
        Translate a single text with retry logic and automatic chunking
        for long inputs.

        Args:
            text: Text to translate
            language_code: Source language code

        Returns:
            Tuple of (translated_text, success, model_used)
        """
        model_name = self._get_model_name(language_code)

        # Hard cap: a single record over `max_translate_chars` is truncated
        # at a sentence boundary BEFORE chunking. A 100 KB scraped news index
        # adds nothing useful past the first ~15 KB of body text; capping
        # here bounds per-record translation time and prevents pathological
        # records from dominating the run.
        max_translate_chars = self.config.get('translation', {}).get(
            'max_translate_chars', 20000)
        if max_translate_chars and len(text) > max_translate_chars:
            cut = text.rfind('. ', 0, max_translate_chars)
            text = text[:cut + 1] if cut > max_translate_chars // 2 else text[:max_translate_chars]
            logger.debug(
                "Truncated input from %d to %d chars before translation",
                len(text), len(text)
            )

        # Estimate token length using a cheap proxy: rough rule of 4 chars
        # per token. Fall back to actual tokenization once the model is
        # loaded if we're near the boundary.
        if len(text) > 1500:  # guaranteed to need chunking
            try:
                model = self._load_model(model_name)
                chunks = self._chunk_text(text, model.tokenizer, max_tokens=400)
                if len(chunks) > 1:
                    return self._translate_chunks(chunks, language_code, model_name)
            except Exception as e:
                logger.warning(
                    f"Chunking failed (will retry without chunking): {e}"
                )

        last_exc_class = None
        for attempt in range(self.max_retries):
            try:
                model = self._load_model(model_name)

                # Adjust beam size for retries
                num_beams = self.retry_beam_sizes[attempt] if attempt < len(self.retry_beam_sizes) else 1

                translation = model.translate_batch(
                    [text],
                    max_length=self.max_length,
                    num_beams=num_beams,
                    early_stopping=self.early_stopping,
                    source_lang=language_code,
                )[0]

                # Validate translation
                if translation and len(translation.strip()) > 0:
                    return translation, True, model_name

                logger.warning(
                    f"Empty translation on attempt {attempt + 1} "
                    f"(lang={language_code}, model={model_name}, input_len={len(text)})"
                )
                last_exc_class = "EmptyOutput"

            except Exception as e:
                last_exc_class = type(e).__name__
                logger.warning(
                    f"Translation attempt {attempt + 1} failed: {last_exc_class}: {e} "
                    f"(lang={language_code}, model={model_name}, input='{text[:80]}')"
                )

        # All retries failed
        self.failure_stats[last_exc_class or "Unknown"] += 1
        logger.error(
            f"Failed to translate after {self.max_retries} attempts: lang={language_code}, "
            f"reason={last_exc_class}, input='{text[:120]}'"
        )
        return "", False, model_name

    def _translate_chunks(self, chunks: List[str], language_code: str,
                          model_name: str) -> Tuple[str, bool, str]:
        """Translate a pre-chunked list and concatenate.

        Sub-batches the chunks at `translation_batch_size` so a single big
        document (e.g. a 50 KB forum thread split into 100 chunks) does not
        get sent to the GPU as one forward pass — that triggered OOM at
        ~22.8 GB on the 4090. Per-sub-batch failures are absorbed; a failing
        sub-batch falls back to one-chunk-at-a-time inside it. A single bad
        chunk cannot poison the whole record.
        """
        model = self._load_model(model_name)
        sub_bs = max(1, self.translation_batch_size)
        outs: List[str] = []
        for i in range(0, len(chunks), sub_bs):
            sub = chunks[i:i + sub_bs]
            try:
                outs.extend(model.translate_batch(
                    sub,
                    max_length=self.max_length,
                    num_beams=self.num_beams,
                    early_stopping=self.early_stopping,
                    source_lang=language_code,
                ))
            except Exception as e:
                logger.warning(
                    "Chunked sub-batch failed (%s: %s); falling back to "
                    "one chunk at a time for this slice (%d chunks)",
                    type(e).__name__, e, len(sub)
                )
                # Free any allocator scraps before retrying serially.
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                for c in sub:
                    try:
                        outs.append(model.translate_batch(
                            [c], max_length=self.max_length,
                            num_beams=1, early_stopping=self.early_stopping,
                            source_lang=language_code)[0])
                    except Exception as e2:
                        logger.debug("Single-chunk retry failed: %s: %s",
                                     type(e2).__name__, e2)
                        outs.append("")
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
        joined = ' '.join(o for o in outs if o)
        if not joined.strip():
            return "", False, model_name
        return joined, True, model_name
    
    def translate_batch(self, texts: List[str], language_code: str) -> List[Tuple[str, bool]]:
        """
        Translate a batch of texts in the same language.
        
        Args:
            texts: List of texts to translate
            language_code: Source language code (same for all texts)
            
        Returns:
            List of tuples (translated_text, success)
        """
        if not texts:
            return []
        
        model_name = self._get_model_name(language_code)
        results = []
        n_total = len(texts)
        log_every = max(25, 200 // self.translation_batch_size)  # log every ~200 texts for large batches
        
        # Process in sub-batches. For inputs that exceed the model's safe
        # token cap, route through the chunked path; otherwise translate
        # the batch directly. We test the cheap char-length proxy first to
        # avoid tokenizing every short input.
        for i in range(0, len(texts), self.translation_batch_size):
            batch = texts[i:i + self.translation_batch_size]
            batch_num = i // self.translation_batch_size

            try:
                model = self._load_model(model_name)
                max_translate_chars = self.config.get('translation', {}).get(
                    'max_translate_chars', 20000)
                translations = []
                for text in batch:
                    if max_translate_chars and len(text) > max_translate_chars:
                        cut = text.rfind('. ', 0, max_translate_chars)
                        text = (text[:cut + 1] if cut > max_translate_chars // 2
                                else text[:max_translate_chars])
                    if len(text) > 1500:
                        chunks = self._chunk_text(text, model.tokenizer, max_tokens=400)
                        if len(chunks) > 1:
                            joined, ok, _ = self._translate_chunks(
                                chunks, language_code, model_name)
                            translations.append(joined if ok else "")
                            continue
                    translations.extend(model.translate_batch(
                        [text],
                        max_length=self.max_length,
                        num_beams=self.num_beams,
                        early_stopping=self.early_stopping,
                        source_lang=language_code,
                    ))

                # Validate each translation. Beyond emptiness, detect the
                # degenerate-repetition failure mode (see _is_degenerate).
                for translation in translations:
                    if not translation or len(translation.strip()) == 0:
                        results.append(("", False))
                    elif self._is_degenerate(translation):
                        self.failure_stats["DegenerateOutput"] += 1
                        logger.warning(
                            "Translation flagged as degenerate (repetition); "
                            "marking failed: '%s...'", translation[:120]
                        )
                        results.append(("", False))
                    else:
                        results.append((translation, True))
                
                # Progress log for large batches so the run doesn't look stuck
                if n_total > 100 and batch_num > 0 and batch_num % log_every == 0:
                    done = min(i + self.translation_batch_size, n_total)
                    logger.info(f"Translation progress {language_code}: {done}/{n_total} texts")
                        
            except Exception as e:
                exc_class = type(e).__name__
                self.failure_stats[exc_class] += len(batch)
                logger.error(
                    f"Batch translation failed: {exc_class}: {e} "
                    f"(lang={language_code}, model={model_name}, batch_size={len(batch)}, "
                    f"first_input='{batch[0][:80] if batch else ''}')"
                )
                for _ in batch:
                    results.append(("", False))

        return results
    
    def translate_grouped_texts(self, grouped_texts: Dict[str, List[Tuple[int, str]]]) -> Dict[int, Tuple[str, bool, str]]:
        """
        Translate texts grouped by language.
        
        Args:
            grouped_texts: Dictionary mapping language_code to list of (index, text) tuples
            
        Returns:
            Dictionary mapping index to (translated_text, success, model_used)
        """
        results = {}
        
        for language_code, text_list in grouped_texts.items():
            if not text_list:
                continue
            
            logger.info(f"Translating {len(text_list)} texts from {language_code}")
            
            # Extract texts and indices
            indices = [idx for idx, _ in text_list]
            texts = [text for _, text in text_list]
            
            # Get model name
            model_name = self._get_model_name(language_code)
            
            # Translate batch
            translations = self.translate_batch(texts, language_code)
            
            # Map results back to indices
            for idx, (translation, success) in zip(indices, translations):
                results[idx] = (translation, success, model_name)
        
        return results
    
    def cleanup(self) -> None:
        """Unload all models and free memory."""
        logger.info("Cleaning up translator resources")
        if self.failure_stats:
            total = sum(self.failure_stats.values())
            breakdown = ", ".join(f"{k}={v}" for k, v in sorted(
                self.failure_stats.items(), key=lambda kv: -kv[1]))
            logger.warning(f"Translation failures this run: {total} total ({breakdown})")
        for model_name, model in self.loaded_models.items():
            model.unload()
        self.loaded_models.clear()
        self.model_usage_count.clear()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

