"""
Content Cleaner for DarkWeb Translation Pipeline
Removes HTML, JavaScript, and other noise from scraped content.
"""

import re
import logging
from typing import Optional

try:
    import regex as _regex_with_timeout  # third-party regex with timeout= support
    _HAS_REGEX_TIMEOUT = True
except ImportError:
    _regex_with_timeout = None
    _HAS_REGEX_TIMEOUT = False

logger = logging.getLogger(__name__)

# Hard ceiling for any single regex application. Forum posts beyond this length
# are pathological for HTML/JS removal regardless of pattern; we truncate before
# applying script/style sub() to prevent worst-case backtracking on malformed input.
_REGEX_MAX_INPUT = 200_000

# Wall-clock timeout for the script/style sub() calls when the `regex` library
# is available. 5 s is generous compared to the ~ms typical case.
_REGEX_TIMEOUT_S = 5.0


def _safe_sub(pattern_src: str, flags: int, replacement: str, text: str) -> str:
    """Apply a regex substitution with a wall-clock timeout when possible.

    Falls back to stdlib `re` (no timeout) when the third-party `regex` library
    isn't installed; in that case input is hard-truncated to _REGEX_MAX_INPUT.
    """
    if len(text) > _REGEX_MAX_INPUT:
        text = text[:_REGEX_MAX_INPUT]
    if _HAS_REGEX_TIMEOUT:
        try:
            return _regex_with_timeout.sub(
                pattern_src, replacement, text, flags=flags, timeout=_REGEX_TIMEOUT_S
            )
        except _regex_with_timeout.error:
            return text
        except TimeoutError:
            logger.warning(
                "Regex timeout (>%ss) in pattern %r; returning input unchanged",
                _REGEX_TIMEOUT_S, pattern_src[:60]
            )
            return text
    return re.sub(pattern_src, replacement, text, flags=flags)


class ContentCleaner:
    """Cleans and preprocesses text content."""

    # Patterns for noise detection
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
    STYLE_PATTERN = re.compile(r'<style[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)
    # Source strings for the timeout-aware path
    _SCRIPT_SRC = r'<script[^>]*>.*?</script>'
    _STYLE_SRC = r'<style[^>]*>.*?</style>'
    JS_FUNCTION_PATTERN = re.compile(r'\bfunction\s+\w+\s*\([^)]*\)\s*\{', re.IGNORECASE)
    JS_VAR_PATTERN = re.compile(r'\b(var|let|const)\s+\w+\s*=', re.IGNORECASE)
    HTML_ENTITY_PATTERN = re.compile(r'&[a-zA-Z]+;|&#\d+;')
    URL_PATTERN = re.compile(r'https?://\S+')
    EXCESSIVE_WHITESPACE = re.compile(r'\s+')
    
    # Common HTML/JS noise strings
    NOISE_STRINGS = [
        'window._cstart',
        'function envFlush',
        'requireLazy',
        'CavalryLogger',
        '<?xml',
        '<!DOCTYPE',
        'javascript:void',
        'addEventListener',
        'getElementById',
        'querySelector',
    ]
    
    # Spam/irrelevant content patterns
    SPAM_PATTERNS = [
        '404 not found',
        'page not found',
        'access denied',
        'forbidden',
        'no intro collection',
        'no-intro',
        'bitcoin what is it',
        'what is bitcoin',
        'crypto wiki',
        'cryptowiki',
        'parltrack beta',
    ]
    
    def __init__(self, 
                 remove_html: bool = True,
                 remove_urls: bool = False,
                 min_word_count: int = 3):
        """
        Initialize content cleaner.
        
        Args:
            remove_html: Whether to remove HTML tags
            remove_urls: Whether to remove URLs
            min_word_count: Minimum number of words for valid content
        """
        self.remove_html = remove_html
        self.remove_urls = remove_urls
        self.min_word_count = min_word_count
    
    def is_html_noise(self, text: str) -> bool:
        """
        Check if text is primarily HTML/JavaScript noise or spam.
        
        Args:
            text: Text to check
            
        Returns:
            True if text is noise/spam
        """
        if not text:
            return True
        
        text_lower = text.lower()
        sample = text_lower[:1000]  # Check first 1000 chars
        
        # Check for noise strings
        for noise in self.NOISE_STRINGS:
            if noise.lower() in sample:
                return True
        
        # Check for spam patterns
        for spam in self.SPAM_PATTERNS:
            if spam in text_lower:
                return True
        
        # Check if text has excessive HTML tags
        html_tags = len(self.HTML_TAG_PATTERN.findall(text[:5000]))  # Limit regex scope
        if html_tags > 10:
            return True
        
        # Check if text has JavaScript functions (limit scope for speed)
        if len(self.JS_FUNCTION_PATTERN.findall(text[:5000])) > 3:
            return True
        
        # Check if text has excessive variable declarations
        if len(self.JS_VAR_PATTERN.findall(text[:5000])) > 5:
            return True
        
        return False
    
    def clean(self, text: str) -> Optional[str]:
        """
        Clean text content.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text or None if too much noise
        """
        if not text or len(text.strip()) == 0:
            return None
        
        # For very long texts, use fast cleaning path
        LONG_TEXT_THRESHOLD = 50000
        if len(text) > LONG_TEXT_THRESHOLD:
            return self._clean_long_text(text)
        
        # Check for HTML/JS noise first
        if self.is_html_noise(text):
            logger.debug("Detected HTML/JS noise, skipping")
            return None
        
        cleaned = text

        # Remove script and style tags with content (timeout-protected)
        cleaned = _safe_sub(self._SCRIPT_SRC, re.DOTALL | re.IGNORECASE, '', cleaned)
        cleaned = _safe_sub(self._STYLE_SRC, re.DOTALL | re.IGNORECASE, '', cleaned)
        
        # Remove HTML tags
        if self.remove_html:
            cleaned = self.HTML_TAG_PATTERN.sub(' ', cleaned)
        
        # Decode HTML entities
        cleaned = self.HTML_ENTITY_PATTERN.sub(' ', cleaned)
        
        # Remove URLs if requested
        if self.remove_urls:
            cleaned = self.URL_PATTERN.sub(' ', cleaned)
        
        # Clean up whitespace
        cleaned = self.EXCESSIVE_WHITESPACE.sub(' ', cleaned)
        cleaned = cleaned.strip()
        
        # Check if enough content remains
        word_count = len(cleaned.split())
        if word_count < self.min_word_count:
            logger.debug(f"Too few words after cleaning: {word_count}")
            return None
        
        return cleaned
    
    def _clean_long_text(self, text: str) -> Optional[str]:
        """
        Fast cleaning path for very long texts (>50K chars).
        Uses chunked processing and aggressive noise removal.
        
        Args:
            text: Long text to clean
            
        Returns:
            Cleaned text or None if too much noise
        """
        # Quick noise check - if first 2K chars are mostly JS/code, reject early
        sample = text[:2000].lower()
        js_indicators = ['function(', 'function ', 'var ', 'const ', 'let ', 
                        'window.', 'document.', '=>', '===', '!==', '();',
                        'return ', 'this.', 'null,', 'true,', 'false,']
        js_count = sum(1 for ind in js_indicators if ind in sample)
        
        if js_count >= 5:
            logger.debug("Long text is primarily JavaScript code, skipping")
            return None
        
        # Check for noise strings
        for noise in self.NOISE_STRINGS:
            if noise.lower() in sample:
                logger.debug(f"Long text contains noise marker: {noise}")
                return None
        
        CHUNK_SIZE = 20000  # Process in 20K chunks
        cleaned_chunks = []
        
        # Process text in chunks
        for i in range(0, len(text), CHUNK_SIZE):
            chunk = text[i:i + CHUNK_SIZE]
            
            # Fast tag removal using string operations
            chunk = self._fast_remove_tags(chunk, 'script')
            chunk = self._fast_remove_tags(chunk, 'style')
            
            # Fast HTML tag removal
            if self.remove_html:
                chunk = self._fast_remove_html_tags(chunk)
            
            # Remove JavaScript-like code patterns (line by line)
            lines = chunk.split('\n')
            clean_lines = []
            for line in lines:
                line_lower = line.lower().strip()
                # Skip lines that look like code
                if any(ind in line_lower for ind in ['function(', 'function ', 'var ', 'const ', 'let ',
                                                      '=>', '===', '!==', '});', ']);', 'return ', 'this.']):
                    continue
                # Skip lines with excessive special characters (likely code)
                special_count = sum(1 for c in line if c in '{}[]();,=>')
                if len(line) > 10 and special_count / len(line) > 0.15:
                    continue
                clean_lines.append(line)
            chunk = ' '.join(clean_lines)
            
            # Fast entity cleanup (common ones only)
            chunk = chunk.replace('&nbsp;', ' ')
            chunk = chunk.replace('&amp;', '&')
            chunk = chunk.replace('&lt;', '<')
            chunk = chunk.replace('&gt;', '>')
            chunk = chunk.replace('&quot;', '"')
            
            # Remove excessive whitespace
            words = chunk.split()
            chunk = ' '.join(words)
            
            if chunk and len(chunk) > 20:  # Only keep substantial chunks
                cleaned_chunks.append(chunk)
        
        cleaned = ' '.join(cleaned_chunks)
        
        # Final validation
        word_count = len(cleaned.split())
        if word_count < self.min_word_count:
            return None
        
        # If cleaned text is less than 5% of original, probably too much noise was removed
        if len(cleaned) < len(text) * 0.05:
            logger.debug(f"Too much content removed ({len(cleaned)}/{len(text)} chars)")
            return None
        
        return cleaned
    
    def _fast_remove_tags(self, text: str, tag: str) -> str:
        """Fast removal of specific tags using string find (no regex)."""
        result = []
        pos = 0
        open_tag = f'<{tag}'
        close_tag = f'</{tag}>'
        
        while pos < len(text):
            # Find opening tag
            start = text.lower().find(open_tag, pos)
            if start == -1:
                result.append(text[pos:])
                break
            
            # Add text before tag
            result.append(text[pos:start])
            
            # Find closing tag
            end = text.lower().find(close_tag, start)
            if end == -1:
                # No closing tag, skip rest
                break
            
            pos = end + len(close_tag)
        
        return ''.join(result)
    
    def _fast_remove_html_tags(self, text: str) -> str:
        """Fast HTML tag removal using character-by-character scan."""
        result = []
        in_tag = False
        
        for char in text:
            if char == '<':
                in_tag = True
            elif char == '>':
                in_tag = False
                result.append(' ')  # Replace tag with space
            elif not in_tag:
                result.append(char)
        
        return ''.join(result)
    
    def extract_sentences(self, text: str) -> list:
        """
        Extract sentences from text.
        
        Args:
            text: Text to split into sentences
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with NLTK)
        # Split on period, exclamation, question mark followed by space/newline
        sentences = re.split(r'[.!?]+\s+|\n+', text)
        
        # Filter out empty or very short sentences
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        return sentences

