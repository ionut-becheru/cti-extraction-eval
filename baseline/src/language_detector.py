"""
Language Detector for DarkWeb Translation Pipeline.

Default: fastText `lid.176.bin` (Joulin et al. 2017).

GlotLID upgrade path: if `language_detection.use_glotlid: true` is set in the
config (or `model_path` ends with `glotlid.bin` / `model_v3.bin`), we still
load via the fastText `load_model()` API since GlotLID ships as a fastText
model. The only call-site change is the model file. GlotLID v3 reports
+22 absolute F1 on noisy/short/code-mixed text vs lid.176 on DIVERS-Bench
(arXiv:2509.17768, Sept 2025).

Download GlotLID v3 from:
  https://huggingface.co/cis-lmu/glotlid/resolve/main/model_v3.bin
"""

import re
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import fasttext

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Fast language detection using fastText."""
    
    # Mapping from fastText language codes to translation model codes
    LANGUAGE_CODE_MAPPING = {
        '__label__en': 'en',
        '__label__ru': 'ru',
        '__label__de': 'de',
        '__label__fr': 'fr',
        '__label__es': 'es',
        '__label__it': 'it',
        '__label__pt': 'pt',
        '__label__nl': 'nl',
        '__label__pl': 'pl',
        '__label__cs': 'cs',
        '__label__sv': 'sv',
        '__label__no': 'no',
        '__label__da': 'da',
        '__label__fi': 'fi',
        '__label__et': 'et',
        '__label__tr': 'tr',
        '__label__ar': 'ar',
        '__label__he': 'he',
        '__label__zh': 'zh',
        '__label__ja': 'ja',
        '__label__ko': 'ko',
        '__label__vi': 'vi',
        '__label__th': 'th',
        '__label__id': 'id',
        '__label__hi': 'hi',
        '__label__bg': 'bg',
        '__label__el': 'el',
        '__label__ro': 'ro',
        '__label__uk': 'uk',
        '__label__hr': 'hr',
        '__label__sk': 'sk',
        '__label__sl': 'sl',
        '__label__lt': 'lt',
        '__label__lv': 'lv',
        '__label__ca': 'ca',
        '__label__mk': 'mk',
        '__label__cy': 'cy',
        '__label__so': 'so',
        '__label__af': 'af',
        '__label__tl': 'tl',
        '__label__sw': 'sw',
        '__label__sq': 'sq',
        '__label__te': 'te',
        '__label__kn': 'kn',
        '__label__ur': 'ur',
        '__label__hu': 'hu',
        '__label__bn': 'bn',
    }

    # GlotLID labels are ISO 639-3 + script ("eng_Latn", "rus_Cyrl", "zho_Hans").
    # Mapping covers the languages our translation models support; anything else
    # falls back to 'unknown'.
    GLOTLID_TO_ISO2 = {
        'eng': 'en', 'rus': 'ru', 'deu': 'de', 'fra': 'fr', 'spa': 'es',
        'ita': 'it', 'por': 'pt', 'nld': 'nl', 'pol': 'pl', 'ces': 'cs',
        'swe': 'sv', 'nor': 'no', 'nob': 'no', 'nno': 'no',
        'dan': 'da', 'fin': 'fi', 'est': 'et', 'tur': 'tr',
        'ara': 'ar', 'heb': 'he', 'zho': 'zh', 'cmn': 'zh',
        'jpn': 'ja', 'kor': 'ko', 'vie': 'vi', 'tha': 'th', 'ind': 'id',
        'hin': 'hi', 'bul': 'bg', 'ell': 'el', 'ron': 'ro', 'ukr': 'uk',
        'hrv': 'hr', 'slk': 'sk', 'slv': 'sl', 'lit': 'lt', 'lav': 'lv',
        'cat': 'ca', 'mkd': 'mk', 'cym': 'cy', 'som': 'so', 'afr': 'af',
        'tgl': 'tl', 'swa': 'sw', 'sqi': 'sq', 'tel': 'te', 'kan': 'kn',
        'urd': 'ur', 'hun': 'hu', 'ben': 'bn',
    }

    def _normalize_lid_label(self, label: str) -> str:
        """Map a fastText / GlotLID label to a 2-letter language code or 'unknown'."""
        if label in self.LANGUAGE_CODE_MAPPING:
            return self.LANGUAGE_CODE_MAPPING[label]
        # GlotLID style: __label__eng_Latn -> 'eng'
        if label.startswith('__label__'):
            stripped = label[len('__label__'):].split('_', 1)[0]
            return self.GLOTLID_TO_ISO2.get(stripped, 'unknown')
        return 'unknown'

    # py3langid's normalized probabilities run lower than fastText's softmax
    # outputs on short or jargon-heavy text — 0.5 is too strict for it.
    # These are the per-backend defaults applied when the caller passes the
    # legacy confidence_threshold=0.5 sentinel (or nothing).
    _DEFAULT_THRESHOLDS = {
        "py3langid": 0.3,
        "fasttext": 0.5,
        "glotlid": 0.5,
    }

    def __init__(self, model_path: str, confidence_threshold: float = 0.5,
                 backend: str = "auto"):
        """
        Initialize language detector.

        Args:
            model_path: Path to fastText-format language detection model
                (only used by the `fasttext` / `glotlid` backend).
            confidence_threshold: Minimum confidence for language detection.
            backend: One of "auto", "fasttext", "glotlid", "py3langid".
                - "py3langid": pure-Python, ~3500 rec/s on this hardware,
                   97 languages, no native deps. Recommended unless you need
                   GlotLID's 2102-language coverage.
                - "fasttext": loads `lid.176.bin` (176 langs).
                - "glotlid": loads GlotLID v3 (2102 langs); same fastText API.
                - "auto" (default): py3langid if model_path doesn't exist or
                   isn't given; otherwise fasttext/glotlid by filename.
        """
        self.model_path = model_path
        self.model = None
        self._short_text_skipped = 0
        self._low_confidence = 0
        self._lid_errors = 0

        fname = Path(model_path).name.lower() if model_path else ""
        if backend == "auto":
            if model_path and Path(model_path).exists():
                backend = "glotlid" if ("glotlid" in fname or "model_v3.bin" in fname) else "fasttext"
            else:
                backend = "py3langid"
        self.backend = backend
        self.is_glotlid = (backend == "glotlid")

        # If the caller used the legacy default 0.5, swap in the per-backend
        # default. Anything else is treated as a user override and kept as-is.
        if confidence_threshold == 0.5:
            confidence_threshold = self._DEFAULT_THRESHOLDS.get(backend, 0.5)
        self.confidence_threshold = confidence_threshold

        logger.info(
            "Initializing language detector backend=%s threshold=%.2f%s",
            self.backend, self.confidence_threshold,
            f" model={model_path}" if backend in ("fasttext", "glotlid") else ""
        )

    def load_model(self) -> None:
        """Load the underlying model (lazy)."""
        if self.model is not None:
            return
        if self.backend == "py3langid":
            self._load_py3langid()
        else:
            self._load_fasttext()

    def _load_py3langid(self) -> None:
        """Pure-Python langid; no native deps, ~3500 rec/s, 97 languages."""
        import py3langid
        # py3langid is a singleton-ish module; create one identifier instance
        # so we keep the model probabilities loaded once.
        from py3langid.langid import LanguageIdentifier, MODEL_FILE
        self.model = LanguageIdentifier.from_pickled_model(
            MODEL_FILE, norm_probs=True
        )
        logger.info("py3langid model loaded (%d languages)", len(self.model.nb_classes))

    def _load_fasttext(self) -> None:
        """fastText / GlotLID, with NumPy-2 compat shim."""
        kind = 'GlotLID' if self.is_glotlid else 'fastText'
        logger.info(f"Loading {kind} model...")
        fasttext.FastText.eprint = lambda x: None
        # NumPy 2.2+ compat: fasttext 0.9.3's _FastText.predict() returns
        # `np.array(probs, copy=False)` which NumPy ≥2.2 rejects. Patch the
        # method once per process to use np.asarray() — same semantics.
        self._patch_fasttext_numpy2_compat()
        self.model = fasttext.load_model(self.model_path)
        logger.info(f"{kind} model loaded successfully")

    @staticmethod
    def _patch_fasttext_numpy2_compat() -> None:
        """Monkey-patch fasttext 0.9.x to work with NumPy ≥2.2.

        NumPy 2.2 made `np.array(obj, copy=False)` raise instead of falling
        back to a copy when one is unavoidable. fasttext's predict() does
        exactly that on the probability array. We replace predict with a
        version that uses np.asarray, which is the documented forward-
        compatible spelling. Idempotent: a sentinel attribute prevents
        repeated patching.
        """
        import numpy as np
        from fasttext.FastText import _FastText
        if getattr(_FastText, "_numpy2_patched", False):
            return

        def _patched_predict(self, text, k=1, threshold=0.0, on_unicode_error="strict"):
            def check(entry):
                if entry.find("\n") != -1:
                    raise ValueError("predict processes one line at a time (remove '\\n')")
                return entry + "\n"

            if isinstance(text, list):
                text = [check(e) for e in text]
                return self.f.multilinePredict(text, k, threshold, on_unicode_error)

            text = check(text)
            predictions = self.f.predict(text, k, threshold, on_unicode_error)
            if predictions:
                probs, labels = zip(*predictions)
            else:
                probs, labels = ([], ())
            return labels, np.asarray(probs)

        _FastText.predict = _patched_predict
        _FastText._numpy2_patched = True
        logger.debug("Applied fasttext NumPy-2 compat patch")
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for language detection.
        Samples from multiple positions for long texts to catch content
        that might be buried deeper (after headers, HTML, etc.)
        
        Args:
            text: Raw text
            
        Returns:
            Preprocessed text (combined samples for long texts)
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # For shorter texts, just use first 1000 chars
        if len(text) <= 5000:
            return text[:1000].strip()
        
        # For longer texts, sample from multiple positions
        # This catches important content buried deeper in the text
        samples = []
        text_len = len(text)
        
        # Sample 1: First 500 chars (might be headers/noise, but check anyway)
        samples.append(text[:500])
        
        # Sample 2: Around 25% position
        pos_25 = text_len // 4
        samples.append(text[pos_25:pos_25 + 500])
        
        # Sample 3: Middle
        mid = text_len // 2
        samples.append(text[mid:mid + 500])
        
        # Sample 4: Around 75% position
        pos_75 = (text_len * 3) // 4
        samples.append(text[pos_75:pos_75 + 500])
        
        # Combine samples (2000 chars total, spread across text)
        return ' '.join(samples).strip()
    
    def _predict_one(self, text: str) -> Tuple[str, float]:
        """Backend-dispatched single-text prediction. Returns (raw_lang, confidence)."""
        if self.backend == "py3langid":
            lang, prob = self.model.classify(text)
            return lang, float(prob)
        # fastText / GlotLID
        predictions = self.model.predict(text, k=1)
        label = predictions[0][0]
        confidence = float(predictions[1][0])
        return self._normalize_lid_label(label), confidence

    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect language of a single text.

        Args:
            text: Text to detect language for

        Returns:
            Tuple of (language_code, confidence)
        """
        if self.model is None:
            self.load_model()

        # Preprocess
        text = self._preprocess_text(text)

        if not text or len(text) < 10:
            return 'too_short', 0.0

        # Replace newlines with spaces (matters for fastText; harmless for py3langid)
        text = text.replace('\n', ' ')

        try:
            lang_code, confidence = self._predict_one(text)
            if confidence < self.confidence_threshold:
                return 'unknown', confidence
            return lang_code, confidence

        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return 'unknown', 0.0
    
    def detect_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """
        Detect languages for a batch of texts.

        Args:
            texts: List of texts to detect languages for

        Returns:
            List of tuples (language_code, confidence). Short or low-confidence
            inputs return ('unknown', 0.0); we count those for diagnostics on
            cleanup so silent drops at scale are auditable, and downstream
            post-translation cybersec keyword re-filter can still try the
            original text since it's preserved by the caller.
        """
        if self.model is None:
            self.load_model()

        results = []

        # Preprocess all texts
        preprocessed = [self._preprocess_text(text) for text in texts]

        for i, text in enumerate(preprocessed):
            if not text or len(text) < 10:
                self._short_text_skipped += 1
                logger.debug(
                    "LID skipped: text too short (len=%d) at batch index %d",
                    len(text or ''), i
                )
                # Distinct from 'unknown' (LID-low-confidence) so paper stats
                # can break down filtering vs model failures separately.
                results.append(('too_short', 0.0))
                continue

            # Replace newlines
            text = text.replace('\n', ' ')

            try:
                lang_code, confidence = self._predict_one(text)
                if confidence < self.confidence_threshold:
                    self._low_confidence += 1
                    logger.debug(
                        "LID low confidence: %.3f < %.3f at batch index %d",
                        confidence, self.confidence_threshold, i
                    )
                    results.append(('unknown', confidence))
                else:
                    results.append((lang_code, confidence))

            except Exception as e:
                self._lid_errors += 1
                logger.warning(f"Language detection failed for text {i}: {e}")
                results.append(('unknown', 0.0))

        return results

    def get_skip_stats(self) -> Dict[str, int]:
        """Diagnostics: how many records were silently mapped to 'unknown' and why."""
        return {
            'short_text_skipped': self._short_text_skipped,
            'low_confidence': self._low_confidence,
            'lid_errors': self._lid_errors,
        }
    
    def get_language_stats(self, detections: List[Tuple[str, float]]) -> Dict[str, int]:
        """
        Get statistics from a batch of language detections.
        
        Args:
            detections: List of (language_code, confidence) tuples
            
        Returns:
            Dictionary mapping language codes to counts
        """
        stats = {}
        for lang_code, _ in detections:
            stats[lang_code] = stats.get(lang_code, 0) + 1
        return stats

