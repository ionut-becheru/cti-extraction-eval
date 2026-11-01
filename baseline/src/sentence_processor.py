"""
Sentence Processor for DarkWeb Translation Pipeline
Handles sentence-level text processing and translation.
"""

import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class SentenceProcessor:
    """Processes text at sentence level for efficient translation."""
    
    # Sentence boundary patterns
    SENTENCE_BOUNDARIES = re.compile(r'([.!?]+)\s+|\n{2,}')
    
    # Abbreviations to avoid false sentence splits
    ABBREVIATIONS = {
        'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr',
        'inc', 'ltd', 'co', 'corp',
        'etc', 'vs', 'i.e', 'e.g',
        'a.m', 'p.m',
    }
    
    def __init__(self,
                 min_sentence_length: int = 15,
                 max_sentence_length: int = 500,
                 merge_short_sentences: bool = True,
                 max_sentences_per_record: int = 200):
        """
        Initialize sentence processor.

        Args:
            min_sentence_length: Minimum length for a valid sentence
            max_sentence_length: Maximum length for a sentence
            merge_short_sentences: Whether to merge consecutive short sentences
            max_sentences_per_record: Hard cap on sentences emitted from a single
                record. Prevents one pathological 50KB post from exploding into
                thousands of GPU translation tasks and starving the pipeline.
        """
        self.min_sentence_length = min_sentence_length
        self.max_sentence_length = max_sentence_length
        self.merge_short_sentences = merge_short_sentences
        self.max_sentences_per_record = max_sentences_per_record
    
    def split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        if not text:
            return []
        
        # Simple split on sentence boundaries
        parts = self.SENTENCE_BOUNDARIES.split(text)
        
        sentences = []
        current = ""
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            
            # Check if this is a boundary marker (., !, ?, etc.)
            if re.match(r'^[.!?]+$', part):
                if current:
                    current += part
                continue
            
            # Add to current sentence
            if current:
                current += " " + part
            else:
                current = part
            
            # Check if we should end the sentence
            # (if it ends with punctuation and is long enough)
            if re.search(r'[.!?]$', current) and len(current) >= self.min_sentence_length:
                sentences.append(current)
                current = ""
        
        # Add any remaining text
        if current and len(current) >= self.min_sentence_length:
            sentences.append(current)
        
        # Filter and validate sentences
        valid_sentences = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < self.min_sentence_length:
                continue  # Skip too-short sentences
            elif len(sent) <= self.max_sentence_length:
                valid_sentences.append(sent)
            else:
                # Chunk very long "sentences" (probably malformed text)
                # Split at word boundaries
                chunks = self._chunk_long_text(sent, self.max_sentence_length)
                valid_sentences.extend(chunks)
        
        # Merge short consecutive sentences if enabled
        if self.merge_short_sentences and valid_sentences:
            valid_sentences = self._merge_short_sentences(valid_sentences)

        # Cap explosion from one giant pathological record. Without this, a 50KB
        # forum post with aggressive newlines turns into thousands of GPU forward
        # passes; the rest of the batch waits hours on a single record.
        if len(valid_sentences) > self.max_sentences_per_record:
            logger.warning(
                "Sentence count %d exceeded cap %d; truncating",
                len(valid_sentences), self.max_sentences_per_record
            )
            valid_sentences = valid_sentences[:self.max_sentences_per_record]

        return valid_sentences
    
    def _merge_short_sentences(self, sentences: List[str]) -> List[str]:
        """
        Merge consecutive short sentences into longer ones.
        
        Args:
            sentences: List of sentences
            
        Returns:
            List with merged sentences
        """
        if len(sentences) <= 1:
            return sentences
        
        merged = []
        current = sentences[0]
        
        for i in range(1, len(sentences)):
            next_sent = sentences[i]
            
            # If both are short, merge them
            if len(current) < 100 and len(next_sent) < 100:
                current += " " + next_sent
            else:
                merged.append(current)
                current = next_sent
        
        # Add the last sentence
        if current:
            merged.append(current)
        
        return merged
    
    def _chunk_long_text(self, text: str, max_length: int) -> List[str]:
        """
        Split very long text into chunks at word boundaries.
        
        Args:
            text: Long text to chunk
            max_length: Maximum chunk length
            
        Returns:
            List of text chunks
        """
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_len = len(word) + 1  # +1 for space
            
            if current_length + word_len > max_length and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += word_len
        
        # Add remaining
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def process_for_translation(self, text: str) -> Tuple[List[str], dict]:
        """
        Process text into sentence chunks ready for translation.
        
        Args:
            text: Text to process
            
        Returns:
            Tuple of (sentences, statistics)
        """
        sentences = self.split_sentences(text)
        
        stats = {
            'original_length': len(text),
            'num_sentences': len(sentences),
            'avg_sentence_length': sum(len(s) for s in sentences) / len(sentences) if sentences else 0,
            'total_chars': sum(len(s) for s in sentences)
        }
        
        return sentences, stats
    
    def reconstruct_text(self, sentences: List[str]) -> str:
        """
        Reconstruct text from translated sentences.
        
        Args:
            sentences: List of sentences
            
        Returns:
            Reconstructed text
        """
        # Join sentences with proper spacing
        text = " ".join(sentences)
        
        # Clean up excessive spacing
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text

