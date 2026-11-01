"""
Batch Processor for DarkWeb Translation Pipeline
Orchestrates reading, language detection, translation, and writing.
"""

import json
import logging
import os
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict
from decimal import Decimal
import ijson
from tqdm import tqdm

from .language_detector import LanguageDetector
from .translator import Translator
from .checkpoint_manager import CheckpointManager
from .content_cleaner import ContentCleaner
from .relevance_filter import RelevanceFilter
from .sentence_processor import SentenceProcessor
from .slang_refiner import SlangRefiner

# Analysis-layer modules — instantiated only when `analysis.enabled` is true so a
# pure-translation run with the modules unavailable doesn't break.
try:
    from .cybersec_ner import CybersecNER
    from .threat_classifier import ThreatClassifier
    from .signal_aggregator import SignalAggregator
    from .correlation_engine import CorrelationEngine
    from .alerting import AlertingSystem
    from .threat_intel_feeds import ThreatIntelFeeds
    from .database import ThreatDatabase
    from .graph_db import FalkorGraph
    _ANALYSIS_AVAILABLE = True
except ImportError as _imp_err:  # pragma: no cover
    logging.getLogger(__name__).warning(
        "Analysis modules unavailable; pipeline will run translation-only: %s", _imp_err
    )
    _ANALYSIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class BatchProcessor:
    """Main processor that orchestrates the translation pipeline."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize batch processor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Paths
        self.input_path = Path(config['paths']['input_dataset'])
        self.output_path = Path(config['paths']['output_file'])
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Processing options
        self.read_batch_size = config['translation']['read_batch_size']
        self.skip_english = config['processing']['skip_english']
        self.validate_translations = config['processing']['validate_translations']
        self.min_text_length = config['processing']['min_text_length']
        # max_text_length is used for truncation only, not for skipping (long forum conversations are important)
        self.max_text_length = config['processing'].get('max_text_length', 50000)  # Increased default
        self.checkpoint_frequency = config['checkpoint']['frequency']
        
        # New processing options
        self.enable_content_cleaning = config['processing'].get('enable_content_cleaning', True)
        self.enable_relevance_filter = config['processing'].get('enable_relevance_filter', True)
        self.enable_pre_translation_filter = config['processing'].get(
            'enable_pre_translation_filter', True)
        self.pre_translation_min_length = config['processing'].get(
            'pre_translation_min_length', 200)
        self.enable_sentence_processing = config['processing'].get('enable_sentence_processing', True)
        
        # Initialize components
        self.language_detector = LanguageDetector(
            model_path=config['language_detection']['model_path'],
            confidence_threshold=config['language_detection']['confidence_threshold'],
            backend=config['language_detection'].get('backend', 'auto'),
        )
        
        self.translator = Translator(config)
        
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir=config['paths']['checkpoint_dir'],
            keep_last_n=config['checkpoint']['keep_last_n']
        )
        
        # Initialize new components
        self.content_cleaner = ContentCleaner(
            remove_html=config['processing'].get('remove_html_tags', True),
            remove_urls=config['processing'].get('remove_urls', False),
            min_word_count=config['processing'].get('min_word_count', 3)
        ) if self.enable_content_cleaning else None
        
        relevance_cfg = config.get('relevance', {}) or {}
        self.relevance_filter = RelevanceFilter(
            min_length=config['processing']['min_text_length'],
            max_length=config['processing']['max_text_length'],
            enable_spam_filter=config['processing'].get('enable_spam_filter', True),
            enable_cybersecurity_filter=config['processing'].get('enable_cybersecurity_filter', True),
            min_cybersecurity_keywords=config['processing'].get('min_cybersecurity_keywords', 1),
            classifier_dir=relevance_cfg.get('classifier_dir'),
            zero_shot_enabled=relevance_cfg.get('zero_shot_enabled', False),
            zero_shot_model=relevance_cfg.get('zero_shot_model',
                                              'MoritzLaurer/deberta-v3-large-zeroshot-v2.0'),
            classifier_threshold=relevance_cfg.get('classifier_threshold', 0.7),
            multilingual_lexicon_path=relevance_cfg.get('multilingual_lexicon_path'),
            pre_translation_min_length=self.pre_translation_min_length,
        ) if self.enable_relevance_filter else None
        
        self.sentence_processor = SentenceProcessor(
            min_sentence_length=config['processing'].get('min_sentence_length', 15),
            max_sentence_length=config['processing'].get('max_sentence_length', 500),
            merge_short_sentences=config['processing'].get('merge_short_sentences', True),
            max_sentences_per_record=config['processing'].get('max_sentences_per_record', 200)
        ) if self.enable_sentence_processing else None
        
        # Slang refiner (Algorithm 2: Post-edit refinement)
        self.enable_slang_refinement = config.get('refinement', {}).get('enabled', False)
        self.slang_refiner = SlangRefiner(config) if self.enable_slang_refinement else None

        # Analysis layer (NER + classifier + aggregator + correlator + alerter + DB).
        # Wires the post-translation chain into the live pipeline so the dashboard
        # reads fresh data instead of stale demo records. Each component is
        # individually gated so a missing key (MISP/OTX) doesn't block the rest.
        self.analysis_enabled = (
            config.get('analysis', {}).get('enabled', False) and _ANALYSIS_AVAILABLE
        )
        self.cybersec_ner = None
        self.threat_classifier = None
        self.signal_aggregator = None
        self.correlation_engine = None
        self.threat_intel_feeds = None
        self.alerting_system = None
        self.threat_db = None
        self.graph_db = None

        if self.analysis_enabled:
            nlp_cfg = config.get('nlp', {}) or {}
            try:
                if nlp_cfg.get('enable_cybersec_ner', True):
                    self.cybersec_ner = CybersecNER(config)
                if nlp_cfg.get('enable_threat_classifier', True):
                    self.threat_classifier = ThreatClassifier(config)
                if nlp_cfg.get('enable_signal_aggregator', True):
                    self.signal_aggregator = SignalAggregator(config)
                if config.get('correlation', {}).get('enable_correlation', True):
                    self.correlation_engine = CorrelationEngine(config)
                if config.get('correlation', {}).get('enable_threat_feeds', False):
                    self.threat_intel_feeds = ThreatIntelFeeds(config)
                if config.get('alerting', {}).get('enable_alerting', True):
                    self.alerting_system = AlertingSystem(config)
                if config.get('analysis', {}).get('write_to_db', True):
                    self.threat_db = ThreatDatabase(config)
                # Optional graph-DB mirror — non-fatal when unreachable; the
                # SQLite path stays the source of truth.
                graph_cfg = config.get('graph_db', {}) or {}
                if graph_cfg.get('enabled', False):
                    self.graph_db = FalkorGraph(
                        host=graph_cfg.get('host', '127.0.0.1'),
                        port=int(graph_cfg.get('port', 6379)),
                        password=graph_cfg.get('password', ''),
                        graph_name=graph_cfg.get('graph_name', 'darkweb_threat_intel'),
                    )
                    if self.graph_db.enabled:
                        self.graph_db.ensure_indexes()
                logger.info(
                    "Analysis layer enabled: ner=%s classifier=%s aggregator=%s "
                    "correlator=%s feeds=%s alerter=%s db=%s graph=%s",
                    bool(self.cybersec_ner), bool(self.threat_classifier),
                    bool(self.signal_aggregator), bool(self.correlation_engine),
                    bool(self.threat_intel_feeds), bool(self.alerting_system),
                    bool(self.threat_db),
                    bool(self.graph_db and self.graph_db.enabled),
                )
            except Exception as e:
                logger.error(
                    "Failed to initialize analysis layer: %s; pipeline will run "
                    "translation-only and post-processing scripts can re-run analysis.",
                    e
                )
                self.analysis_enabled = False

        # State
        self.state = None
        self.output_file = None
        self._analysis_failures = 0  # diagnostics for end-of-run summary

        logger.info("BatchProcessor initialized")
    
    def _count_total_records(self) -> Optional[int]:
        """
        Count total records in the dataset (for progress bar).
        WARNING: This is slow for large datasets - disabled by default.
        
        Returns:
            Total number of records or None if counting disabled/fails
        """
        # Skip counting - it's too slow for large datasets
        # Progress bar will work fine without total count
        return None
    
    def _stream_records(self, start_index: int = 0):
        """
        Stream records from the input JSON file.
        
        Args:
            start_index: Index to start reading from
            
        Yields:
            Tuples of (index, record)
        """
        logger.info(f"Streaming records from index {start_index}")
        
        with open(self.input_path, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            for idx, record in enumerate(parser):
                if idx < start_index:
                    continue
                yield idx, record
    
    def _should_skip_record(self, record: Dict, detected_language: str) -> Optional[str]:
        """
        Check if a record should be skipped.
        
        Args:
            record: Record dictionary
            detected_language: Detected language code
            
        Returns:
            Skip reason string or None if should not skip
        """
        text = record.get('raw_text', '')
        
        # Check if English and skip_english is enabled
        if self.skip_english and detected_language == 'en':
            return 'english'
        
        # Check minimum text length only
        # NOTE: Removed max_length check - long forum conversations are important
        # Long texts will be processed (may be split/truncated by translation models if needed)
        if len(text) < self.min_text_length:
            return 'too_short'
        
        return None
    
    def _build_output_records(self, indices, records, cleaned_texts, detections,
                              skip_info, translation_results, sentence_mapping):
        """Build output records from preprocessed data and translation results."""
        output_records = []
        for i, record in enumerate(records):
            output_record = record.copy()
            lang_code, confidence = detections[i] if i < len(detections) else ('unknown', 0.0)
            output_record['detected_language'] = lang_code
            output_record['language_confidence'] = confidence
            output_record['cleaned_text'] = cleaned_texts[i] if i < len(cleaned_texts) else ''

            if i in skip_info:
                skip_lang, skip_conf, skip_reason = skip_info[i]
                if skip_lang != 'unknown':
                    output_record['detected_language'] = skip_lang
                    output_record['language_confidence'] = skip_conf
                output_record['translated_text'] = cleaned_texts[i] if cleaned_texts[i] else record.get('raw_text', '')
                output_record['translation_model'] = None
                output_record['translation_skipped'] = skip_reason
                self.checkpoint_manager.update_state(
                    self.state, indices[i], output_record['detected_language'],
                    translation_successful=True, skip_reason=skip_reason)
            else:
                if i in sentence_mapping:
                    translated_sentences = []
                    all_success = True
                    model_used = None
                    for sent_idx in range(len(sentence_mapping[i])):
                        key = (i, sent_idx)
                        if key in translation_results:
                            translation, success, model_name = translation_results[key]
                            translated_sentences.append(translation if success else sentence_mapping[i][sent_idx])
                            if not success:
                                all_success = False
                            if model_name and not model_used:
                                model_used = model_name
                        else:
                            translated_sentences.append(sentence_mapping[i][sent_idx])
                            all_success = False
                    final_translation = self.sentence_processor.reconstruct_text(translated_sentences)
                    output_record['translated_text'] = final_translation
                    output_record['translation_model'] = model_used
                    output_record['translation_success'] = all_success
                    output_record['sentence_count'] = len(translated_sentences)
                else:
                    translation, success, model_name = translation_results.get(i, ('', False, 'unknown'))
                    output_record['translated_text'] = translation if success else cleaned_texts[i]
                    output_record['translation_model'] = model_name if success else None
                    output_record['translation_success'] = success

                if self.enable_relevance_filter and self.relevance_filter:
                    if lang_code != 'en' and output_record.get('translation_success'):
                        translated_text = output_record.get('translated_text', '')
                        if translated_text:
                            is_relevant, skip_reason = self.relevance_filter.is_relevant(translated_text)
                            output_record['post_translation_filtered'] = not is_relevant
                            if not is_relevant:
                                output_record['filter_reason'] = skip_reason

                if self.enable_slang_refinement and self.slang_refiner and output_record.get('translation_success'):
                    refined_text, was_refined = self.slang_refiner.refine(output_record['translated_text'])
                    if was_refined:
                        output_record['translated_text'] = refined_text
                        output_record['slang_refined'] = True
                    else:
                        output_record['slang_refined'] = False

                self.checkpoint_manager.update_state(
                    self.state, indices[i], lang_code,
                    translation_successful=output_record.get('translation_success', False))

            output_records.append(output_record)
        return output_records

    def _analyze_record(self, output_record: Dict) -> Dict:
        """
        Run the full analysis chain on a single translated record.

        NER → classifier → signal aggregation → correlation → alerts → DB write.
        Mutates output_record in-place to add 'analysis' and 'correlation' fields,
        and writes to the live SQLite DB so the dashboard sees fresh data instead
        of stale demo content. Failures are logged per-record but never raised —
        a single bad record cannot kill a 31k-record run.

        Returns the same dict for chaining.
        """
        if not self.analysis_enabled:
            return output_record

        # Skip records that did not pass the upstream filter pipeline. Running
        # NER / classifier / correlation on cleaner-rejected, spam, pre-filter,
        # or unknown-language records produces noise — spaCy promotes generic
        # nouns to TOOL / PRODUCT (Child, Preteen, ...) and inflates the entity
        # tables. The two stages that survive are:
        #   - English cyber kept (translation_skipped == 'english')
        #   - Non-English translated and not post-filtered.
        skipped = output_record.get('translation_skipped', False)
        if skipped is False or skipped is None:
            if output_record.get('post_translation_filtered'):
                return output_record
        elif str(skipped) != 'english':
            return output_record

        text = (
            output_record.get('translated_text')
            or output_record.get('cleaned_text')
            or output_record.get('raw_text')
            or ''
        )
        if not text or len(text) < 20:
            return output_record

        # Cap text length so a single 50KB record can't dominate analysis time.
        if len(text) > 5000:
            text = text[:5000]

        try:
            # 1) Entity extraction
            entities = []
            if self.cybersec_ner is not None:
                ent_objs = self.cybersec_ner.extract(text)
                entities = [
                    {'label': e.label, 'text': e.text,
                     'start': e.start, 'end': e.end,
                     'metadata': e.metadata}
                    for e in ent_objs
                ]

            # 2) Threat classification
            classifier_data = {}
            if self.threat_classifier is not None:
                classifier_data = self.threat_classifier.classify(text) or {}

            # 3) Keyword signal — reuse existing relevance filter if available so
            #    we don't run a second keyword pass.
            keyword_data = {}
            if self.relevance_filter is not None:
                is_rel, reason = self.relevance_filter.is_relevant(text)
                # crude keyword count: re-uses the cached patterns inside the filter
                kw_count = 5 if is_rel else 0
                keyword_data = {
                    'is_relevant': is_rel,
                    'keyword_count': kw_count,
                    'reason': reason,
                }

            # 4) Signal aggregation
            agg_signal = None
            if self.signal_aggregator is not None:
                agg_signal = self.signal_aggregator.aggregate(
                    keyword_data=keyword_data,
                    classifier_data=classifier_data,
                    entities=entities,
                )

            # Build the analysis dict that goes into both JSONL and DB.
            analysis_dict = {
                'entities': entities,
                'iocs': agg_signal.iocs if agg_signal else {},
                'risk_score': agg_signal.risk_score if agg_signal else 0.0,
                'risk_level': (
                    agg_signal.risk_level.value if agg_signal else 'INFO'
                ),
                'threat_topic': (
                    agg_signal.threat_topic if agg_signal else 'unknown'
                ),
                'classifier': classifier_data,
            }
            output_record['analysis'] = analysis_dict

            # 5) Stable record id. The DB layer normally hashes raw_text via
            #    sha1; we compute the same hash here so correlation, alerting,
            #    and the graph mirror all reference the same id even when
            #    write_to_db is off (e.g. graph-only backfill from JSONL).
            import hashlib
            raw_text = output_record.get('raw_text', '') or ''
            record_id = hashlib.sha1(
                raw_text.encode('utf-8', errors='replace')
            ).hexdigest()
            output_record['record_id'] = record_id

            # 5a) Optional SQLite write
            if self.threat_db is not None:
                # ThreatDatabase.insert_record returns its own hash but the
                # logic is identical, so the result matches what we computed.
                self.threat_db.insert_record(
                    output_record, analysis=analysis_dict, correlation=None
                )

            # 6) Correlation. Pass the full CorrelationResult fields through so
            # the alerting layer can match its rules (matched_cves, matched_threat_actors,
            # matched_campaigns, threat_summary, recommendations).
            correlation_dict = {'record_id': record_id or ''}
            if self.correlation_engine is not None and record_id:
                corr = self.correlation_engine.correlate(
                    record_id=record_id,
                    text=text,
                    entities=entities,
                    iocs=analysis_dict['iocs'],
                )
                correlation_dict = {
                    'record_id': record_id,
                    'matched_cves': getattr(corr, 'matched_cves', []),
                    'matched_iocs': getattr(corr, 'matched_iocs', []),
                    'matched_threat_actors': getattr(corr, 'matched_threat_actors', []),
                    'matched_campaigns': getattr(corr, 'matched_campaigns', []),
                    'temporal_matches': getattr(corr, 'temporal_matches', []),
                    'related_records': getattr(corr, 'related_records', []),
                    'threat_summary': getattr(corr, 'threat_summary', ''),
                    'recommendations': getattr(corr, 'recommendations', []),
                    'correlation_score': getattr(corr, 'correlation_score', 0.0),
                }
                output_record['correlation'] = correlation_dict

            # 7) Alerts. Include `iocs` in the signal dict so the multiple_iocs
            # rule can fire, and pass the rich correlation dict so CVSS/critical
            # CVE escalation reaches the rules.
            if self.alerting_system is not None and record_id and agg_signal is not None:
                signal_for_alert = {
                    'risk_score': agg_signal.risk_score,
                    'risk_level': agg_signal.risk_level.value,
                    'threat_topic': agg_signal.threat_topic,
                    'iocs': analysis_dict['iocs'],
                }
                alerts = self.alerting_system.generate_alert(
                    record_id=record_id,
                    signal=signal_for_alert,
                    entities=entities,
                    correlation=correlation_dict,
                )
                if alerts and self.threat_db is not None:
                    for alert in alerts:
                        self.threat_db.insert_alert(
                            record_id=record_id,
                            alert_type=getattr(alert, 'alert_type', 'unknown'),
                            severity=(
                                alert.severity.value
                                if hasattr(alert.severity, 'value')
                                else str(alert.severity)
                            ),
                            title=alert.title,
                            desc=alert.description,
                        )

            # 8) Optional graph-DB mirror. SQLite is the source of truth;
            # the graph is a derived view. Wrap in its own try/except so a
            # FalkorDB hiccup never poisons the SQLite write that already
            # succeeded above.
            if (self.graph_db is not None and self.graph_db.enabled
                    and record_id is not None):
                try:
                    record_props = {
                        'detected_language': output_record.get('detected_language'),
                        'risk_score': analysis_dict.get('risk_score'),
                        'risk_level': analysis_dict.get('risk_level'),
                        'threat_topic': analysis_dict.get('threat_topic'),
                        'source_forum': output_record.get('source_forum'),
                        'translated_text': output_record.get('translated_text'),
                        'cleaned_text': output_record.get('cleaned_text'),
                        'raw_text': output_record.get('raw_text'),
                    }
                    self.graph_db.bulk_upsert_record(
                        record_id=record_id,
                        record_props=record_props,
                        entities=entities,
                        matched_actors=correlation_dict.get('matched_threat_actors', []),
                        matched_campaigns=correlation_dict.get('matched_campaigns', []),
                        matched_cves=correlation_dict.get('matched_cves', []),
                        source_forum=output_record.get('source_forum'),
                    )
                except Exception as ge:
                    logger.debug(
                        "Graph mirror failed for record %s: %s",
                        record_id[:12] if record_id else '<no-id>', ge
                    )

        except Exception as e:
            self._analysis_failures += 1
            logger.warning(
                "Analysis failed for record (will write translation-only output): "
                "%s: %s", type(e).__name__, e
            )
            # Make sure we never raise — translation output must still land in JSONL.
            output_record.setdefault('analysis', {'error': type(e).__name__})

        return output_record

    def _write_records(self, records: List[Dict]) -> None:
        """
        Write records to output JSONL file.

        Args:
            records: List of records to write
        """
        if self.analysis_enabled:
            for record in records:
                self._analyze_record(record)
        for record in records:
            json_line = json.dumps(record, ensure_ascii=False, cls=DecimalEncoder)
            self.output_file.write(json_line + '\n')
    
    def _preprocess_worker(self, batch: List[tuple]) -> dict:
        """
        CPU-bound preprocessing: clean text, detect language, filter.
        Returns a dict with cleaned_texts, detections, skip_info, and grouped_for_translation.
        This runs on a background thread while the GPU translates the previous batch.
        """
        if not batch:
            return None

        indices = [idx for idx, _ in batch]
        records = [record for _, record in batch]

        cleaned_texts = []
        skip_info = {}

        for i, record in enumerate(records):
            raw_text = record.get('raw_text', '')
            if self.enable_content_cleaning and self.content_cleaner:
                cleaned = self.content_cleaner.clean(raw_text)
                if cleaned is None:
                    # Cleaner rejected the record (HTML / JS / under min word
                    # count). Flag with a 'noise' language so paper-time stats
                    # don't conflate this with LID model failures.
                    skip_info[i] = ('noise', 0.0, 'html_noise')
                    cleaned_texts.append('')
                    continue
                cleaned_texts.append(cleaned)
            else:
                cleaned_texts.append(raw_text)

        detections = self.language_detector.detect_batch(cleaned_texts)

        if self.enable_relevance_filter and self.relevance_filter:
            for i, text in enumerate(cleaned_texts):
                if i in skip_info or not text:
                    continue
                lang_code, confidence = detections[i]
                if lang_code == 'en':
                    is_relevant, skip_reason = self.relevance_filter.is_relevant(text)
                    if not is_relevant:
                        skip_info[i] = (lang_code, confidence, skip_reason)

        for i, (lang_code, confidence) in enumerate(detections):
            if i in skip_info:
                continue
            if self.skip_english and lang_code == 'en':
                skip_info[i] = (lang_code, confidence, 'english')

        # Pre-translation multilingual relevance filter. Runs on the ORIGINAL
        # cleaned text (no translation yet) and skips non-English records that
        # show no cyber signal at all — language-agnostic patterns, English
        # loanwords ("ransomware", "RDP"), or per-language native vocabulary.
        # This is the dominant cost saver: a 30 KB Russian/Catalan/German news
        # post about politics will skip the GPU entirely instead of being
        # translated then dropped post-hoc.
        if (self.enable_pre_translation_filter and self.relevance_filter
                and hasattr(self.relevance_filter, 'is_relevant_multilingual')):
            for i, text in enumerate(cleaned_texts):
                if i in skip_info or not text:
                    continue
                lang_code, confidence = detections[i]
                if lang_code in ('en', 'unknown', 'too_short', 'noise'):
                    continue  # already handled or English (filtered earlier)
                is_relevant, reason = self.relevance_filter.is_relevant_multilingual(
                    text, lang_code)
                if not is_relevant:
                    skip_info[i] = (lang_code, confidence,
                                    f'pre_translation_filter:{reason}')

        grouped_for_translation = defaultdict(list)
        sentence_mapping = {}

        for i, text in enumerate(cleaned_texts):
            if i in skip_info or not text:
                continue
            lang_code, confidence = detections[i]
            # 'unknown' = LID confidence too low; 'too_short' = cleaned text
            # below 10 chars; 'noise' = cleaner rejected (set earlier). All
            # three skip translation but stay distinct for stats purposes.
            if lang_code in ('unknown', 'too_short'):
                skip_info[i] = (lang_code, confidence, lang_code)
                continue
            if self.enable_sentence_processing and self.sentence_processor:
                sentences = self.sentence_processor.split_sentences(text)
                if sentences:
                    sentence_mapping[i] = sentences
                    for sent_idx, sentence in enumerate(sentences):
                        grouped_for_translation[lang_code].append(((i, sent_idx), sentence))
                else:
                    grouped_for_translation[lang_code].append((i, text))
            else:
                grouped_for_translation[lang_code].append((i, text))

        return {
            'batch': batch,
            'indices': indices,
            'records': records,
            'cleaned_texts': cleaned_texts,
            'detections': detections,
            'skip_info': skip_info,
            'grouped_for_translation': grouped_for_translation,
            'sentence_mapping': sentence_mapping,
        }

    def process(self, max_records: Optional[int] = None) -> None:
        """
        Process the entire dataset with checkpointing.
        Uses a pipelined approach: CPU preprocessing of batch N+1 overlaps
        with GPU translation of batch N.
        
        Args:
            max_records: Maximum number of records to process (None for all)
        """
        logger.info("Starting translation pipeline")
        
        # Load or create checkpoint
        checkpoint = self.checkpoint_manager.load_checkpoint()
        if checkpoint:
            self.state = checkpoint
            self.state.setdefault('output_byte_offset', 0)
            self.state.setdefault('output_records_written', 0)
            start_index = checkpoint['last_processed_index'] + 1
            self.checkpoint_manager.truncate_output_to_checkpoint(self.output_path, self.state)
            mode = 'a'  # Append mode
        else:
            self.state = self.checkpoint_manager.create_initial_state()
            start_index = 0
            mode = 'w'  # Write mode

        # Open output file
        self.output_file = open(self.output_path, mode, encoding='utf-8')
        
        try:
            # Setup progress bar
            if max_records:
                pbar = tqdm(total=max_records, initial=0, desc="Processing records", unit="rec")
            else:
                pbar = tqdm(initial=start_index, desc="Processing records", unit="rec")
            
            # Collect batches from the stream. Check max_records *per record*,
            # not just at batch boundaries — otherwise --max-records 15 with
            # read_batch_size=128 still loads 128 records before the break.
            batches = []
            current_batch = []
            records_counted = 0
            for idx, record in self._stream_records(start_index):
                current_batch.append((idx, record))
                records_counted += 1
                if max_records and records_counted >= max_records:
                    batches.append(current_batch)
                    current_batch = []
                    break
                if len(current_batch) >= self.read_batch_size:
                    batches.append(current_batch)
                    current_batch = []
            if current_batch:
                batches.append(current_batch)
            
            logger.info(f"Loaded {len(batches)} batches ({sum(len(b) for b in batches)} records) into RAM")
            
            # Pipelined processing: preprocess next batch on CPU while GPU translates current
            records_processed = 0
            preprocess_result = None
            preprocess_thread = None
            # next_result holds [result, exception]. The worker writes either the result
            # or the exception it caught; the main thread re-raises so a hung or crashing
            # preprocessor cannot silently drop records.
            next_result = [None, None]
            preprocess_join_timeout_s = float(
                self.config.get('processing', {}).get('preprocess_join_timeout_s', 600)
            )

            def _preprocess_async(batch, result_holder):
                try:
                    result_holder[0] = self._preprocess_worker(batch)
                except BaseException as e:
                    result_holder[1] = e

            def _join_or_raise(thread):
                thread.join(timeout=preprocess_join_timeout_s)
                if thread.is_alive():
                    raise TimeoutError(
                        f"Preprocess worker exceeded {preprocess_join_timeout_s}s; "
                        f"the pipeline cannot proceed safely. Aborting so the checkpoint is preserved."
                    )
                if next_result[1] is not None:
                    err = next_result[1]
                    next_result[1] = None
                    raise err

            for batch_idx, batch in enumerate(batches):
                # If we have a prefetched preprocess result, use it
                if preprocess_thread is not None:
                    _join_or_raise(preprocess_thread)
                    preprocess_result = next_result[0]
                    next_result[0] = None
                else:
                    # First batch: preprocess synchronously
                    preprocess_result = self._preprocess_worker(batch)

                # Start preprocessing next batch on CPU (overlaps with GPU translation below)
                if batch_idx + 1 < len(batches):
                    next_result[0] = None
                    next_result[1] = None
                    preprocess_thread = threading.Thread(
                        target=_preprocess_async, args=(batches[batch_idx + 1], next_result))
                    preprocess_thread.daemon = True
                    preprocess_thread.start()
                else:
                    preprocess_thread = None
                
                if preprocess_result is None:
                    continue
                
                # GPU translation (this is the slow part)
                pp = preprocess_result
                translation_results = {}
                if pp['grouped_for_translation']:
                    translation_results = self.translator.translate_grouped_texts(
                        pp['grouped_for_translation'])
                
                # Build output records (reuse original _process_batch logic for post-processing)
                output_records = self._build_output_records(
                    pp['indices'], pp['records'], pp['cleaned_texts'],
                    pp['detections'], pp['skip_info'], translation_results,
                    pp['sentence_mapping'])
                
                self._write_records(output_records)
                self.output_file.flush()
                os.fsync(self.output_file.fileno())
                self.state['output_byte_offset'] = self.output_file.tell()
                self.state['output_records_written'] = (
                    self.state.get('output_records_written', 0) + len(output_records)
                )

                records_processed += len(batch)
                pbar.update(len(batch))

                if records_processed % self.checkpoint_frequency == 0:
                    self.checkpoint_manager.save_checkpoint(self.state)
                    logger.info(f"Processed {records_processed} records")

            # Wait for any remaining preprocess thread (no need to use its result)
            if preprocess_thread is not None:
                preprocess_thread.join(timeout=preprocess_join_timeout_s)
                if preprocess_thread.is_alive():
                    logger.warning(
                        "Trailing preprocess thread did not finish within timeout; "
                        "checkpoint already saved, proceeding to shutdown."
                    )

            pbar.close()
            if self.output_file and not self.output_file.closed:
                self.output_file.flush()
                os.fsync(self.output_file.fileno())
                self.state['output_byte_offset'] = self.output_file.tell()
            self.checkpoint_manager.save_checkpoint(self.state)
            
            stats_summary = self.checkpoint_manager.get_statistics_summary(self.state)
            logger.info(stats_summary)
            print(stats_summary)
            
        finally:
            if self.output_file:
                self.output_file.close()
            self.translator.cleanup()
            if self.slang_refiner:
                self.slang_refiner.cleanup()
            
            logger.info("Translation pipeline completed")

