"""
Checkpoint Manager for DarkWeb Translation Pipeline
Handles saving and loading of processing state for resumability.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpointing and resuming of translation pipeline."""

    def __init__(self, checkpoint_dir: str, keep_last_n: int = 3):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoints
            keep_last_n: Number of recent checkpoints to keep
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.keep_last_n = keep_last_n
        self.checkpoint_file = self.checkpoint_dir / "progress.json"
        self.temp_checkpoint_file = self.checkpoint_dir / "progress.tmp.json"

        if self.temp_checkpoint_file.exists():
            logger.warning(f"Removing orphaned temp checkpoint from prior crash: {self.temp_checkpoint_file}")
            try:
                self.temp_checkpoint_file.unlink()
            except OSError as e:
                logger.error(f"Could not remove orphaned temp checkpoint: {e}")

    def save_checkpoint(self, state: Dict[str, Any]) -> None:
        """
        Save checkpoint atomically.

        Uses os.replace() which is atomic on POSIX and Windows, so a crash mid-save
        leaves either the old checkpoint or the new one intact, never a partial file.

        Args:
            state: State dictionary to save
        """
        new_state = dict(state)
        new_state['timestamp'] = datetime.now().isoformat()

        try:
            with open(self.temp_checkpoint_file, 'w') as f:
                json.dump(new_state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            os.replace(str(self.temp_checkpoint_file), str(self.checkpoint_file))

            if self.keep_last_n > 0:
                backup_name = f"progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                backup_path = self.checkpoint_dir / backup_name
                try:
                    with open(self.checkpoint_file, 'rb') as src, open(backup_path, 'wb') as dst:
                        dst.write(src.read())
                except OSError as e:
                    logger.warning(f"Failed to create checkpoint backup: {e}")

            logger.info(f"Checkpoint saved at record {new_state.get('last_processed_index', 0)}")
            self._cleanup_old_backups()

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            if self.temp_checkpoint_file.exists():
                try:
                    self.temp_checkpoint_file.unlink()
                except OSError:
                    pass
            raise
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Load the most recent checkpoint.
        
        Returns:
            State dictionary if checkpoint exists, None otherwise
        """
        if not self.checkpoint_file.exists():
            logger.info("No checkpoint found, starting from beginning")
            return None
        
        try:
            with open(self.checkpoint_file, 'r') as f:
                state = json.load(f)
            
            logger.info(f"Loaded checkpoint from {state.get('timestamp', 'unknown time')}")
            logger.info(f"Resuming from record {state.get('last_processed_index', 0)}")
            
            return state
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            logger.warning("Starting from beginning")
            return None
    
    def get_starting_index(self) -> int:
        """
        Get the index to start/resume processing from.
        
        Returns:
            Starting index (0 if no checkpoint)
        """
        state = self.load_checkpoint()
        if state is None:
            return 0
        return state.get('last_processed_index', 0) + 1  # Start from next record
    
    def _cleanup_old_backups(self) -> None:
        """Remove old backup checkpoints, keeping only the most recent N."""
        try:
            # Get all backup checkpoint files
            backups = sorted(
                [f for f in self.checkpoint_dir.glob("progress_*.json")],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            # Remove old backups
            for old_backup in backups[self.keep_last_n:]:
                old_backup.unlink()
                logger.debug(f"Removed old backup: {old_backup.name}")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")
    
    def create_initial_state(self) -> Dict[str, Any]:
        """
        Create initial state dictionary.

        Returns:
            Initial state with default values
        """
        return {
            'last_processed_index': -1,
            'total_processed': 0,
            'output_byte_offset': 0,
            'output_records_written': 0,
            'language_distribution': {},
            'translation_stats': {
                'successful': 0,
                'failed': 0,
                'skipped_english': 0,
                'skipped_too_short': 0,
                'skipped_too_long': 0
            },
            'processing_times': {
                'language_detection': 0.0,
                'translation': 0.0,
                'total': 0.0
            },
            'start_time': datetime.now().isoformat()
        }

    def truncate_output_to_checkpoint(self, output_path: Path, state: Dict[str, Any]) -> int:
        """
        Truncate the output JSONL to the byte offset recorded at the last checkpoint.

        This is the dedup guarantee on resume: if the previous run crashed mid-batch
        after writing extra records past the last successful checkpoint, those records
        are removed before we reopen for append, so re-processing those input indices
        does not produce duplicates.

        Args:
            output_path: Path to the output JSONL file
            state: Loaded checkpoint state (must contain 'output_byte_offset')

        Returns:
            The byte offset to which the file was truncated.
        """
        target_offset = int(state.get('output_byte_offset', 0))
        if not output_path.exists():
            return 0

        actual_size = output_path.stat().st_size
        if actual_size <= target_offset:
            return actual_size

        logger.warning(
            f"Truncating output {output_path} from {actual_size} to {target_offset} bytes "
            f"({actual_size - target_offset} bytes of post-checkpoint data discarded for resume safety)"
        )
        with open(output_path, 'r+b') as f:
            f.truncate(target_offset)
            f.flush()
            os.fsync(f.fileno())
        return target_offset
    
    def update_state(self, state: Dict[str, Any], 
                    record_index: int,
                    detected_language: str,
                    translation_successful: bool = True,
                    skip_reason: Optional[str] = None) -> None:
        """
        Update state with new record information.
        
        Args:
            state: Current state dictionary
            record_index: Index of processed record
            detected_language: Detected language code
            translation_successful: Whether translation was successful
            skip_reason: Reason for skipping (if applicable)
        """
        state['last_processed_index'] = record_index
        state['total_processed'] += 1
        
        # Update language distribution
        if 'language_distribution' not in state:
            state['language_distribution'] = {}
        state['language_distribution'][detected_language] = \
            state['language_distribution'].get(detected_language, 0) + 1
        
        # Update translation stats
        if skip_reason:
            key = f'skipped_{skip_reason}'
            state['translation_stats'][key] = state['translation_stats'].get(key, 0) + 1
        elif translation_successful:
            state['translation_stats']['successful'] += 1
        else:
            state['translation_stats']['failed'] += 1
    
    def get_statistics_summary(self, state: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of processing statistics.

        The output is split into three sections so paper-quality numbers can
        be lifted directly without conflating noise rejection (cleaner output
        was empty), too-short text (no signal for LID), LID model failures
        (low-confidence prediction), and confident detections.
        """
        total = max(state['total_processed'], 1)
        lang_dist = state.get('language_distribution', {})

        # Bucket the language codes into the four paper-relevant categories.
        NOISE_KEYS = {'noise'}
        TOOSHORT_KEYS = {'too_short'}
        UNKNOWN_KEYS = {'unknown'}
        noise_count = sum(v for k, v in lang_dist.items() if k in NOISE_KEYS)
        tooshort_count = sum(v for k, v in lang_dist.items() if k in TOOSHORT_KEYS)
        unknown_count = sum(v for k, v in lang_dist.items() if k in UNKNOWN_KEYS)
        detected = {k: v for k, v in lang_dist.items()
                    if k not in NOISE_KEYS | TOOSHORT_KEYS | UNKNOWN_KEYS}
        detected_total = sum(detected.values())

        lines = [
            "\n" + "=" * 60,
            "PROCESSING STATISTICS",
            "=" * 60,
            f"Total processed: {state['total_processed']}",
            f"Last index: {state['last_processed_index']}",
            "",
            "Filtering breakdown (mutually exclusive, sums to total):",
            f"  Cleaner-rejected (noise/HTML/JS): {noise_count} ({noise_count/total*100:.1f}%)",
            f"  Too short for LID (<10 chars):    {tooshort_count} ({tooshort_count/total*100:.1f}%)",
            f"  LID low-confidence (true unknown):{unknown_count} ({unknown_count/total*100:.1f}%)",
            f"  Language detected:                 {detected_total} ({detected_total/total*100:.1f}%)",
            "",
            "Translation Stats:",
            f"  Successful: {state['translation_stats']['successful']}",
            f"  Failed: {state['translation_stats']['failed']}",
            f"  Skipped (English): {state['translation_stats']['skipped_english']}",
            f"  Skipped (too short): {state['translation_stats'].get('skipped_too_short', 0)}",
            f"  Skipped (too long): {state['translation_stats'].get('skipped_too_long', 0)}",
            f"  Skipped (noise): {state['translation_stats'].get('skipped_html_noise', 0)}",
            "",
            f"Top detected languages (of {detected_total} confidently classified):"
        ]
        for lang, count in sorted(detected.items(), key=lambda x: -x[1])[:10]:
            denom = detected_total or 1
            lines.append(f"  {lang}: {count} ({count/denom*100:.1f}% of detected, "
                         f"{count/total*100:.1f}% of total)")

        lines.append("=" * 60)
        return "\n".join(lines)

