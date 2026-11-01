#!/usr/bin/env python3
"""
DarkWeb Translation Pipeline - Main Entry Point

This script runs the translation pipeline for processing dark web forum data.
It supports checkpointing and resuming for large-scale processing.
"""

import argparse
import logging
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

try:
    import coloredlogs
except ImportError:
    coloredlogs = None

from src.batch_processor import BatchProcessor


def setup_logging(config: dict) -> None:
    """
    Setup logging configuration.
    
    Args:
        config: Configuration dictionary
    """
    log_dir = Path(config['paths']['log_dir'])
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_level = config['logging']['level']
    log_format = config['logging']['format']
    log_file_prefix = config['logging']['file_prefix']
    
    # Create log file with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f"{log_file_prefix}_{timestamp}.log"
    
    # Setup root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    if coloredlogs is not None:
        coloredlogs.install(level=log_level, fmt=log_format, logger=logging.getLogger())
    logging.info(f"Logging initialized. Log file: {log_file}")


def _load_config_fallback(config_path: str) -> dict:
    """Minimal YAML-like parser when PyYAML is not installed."""
    path = Path(config_path)
    root = path.parent.parent  # project root
    with open(config_path, 'r') as f:
        lines = f.readlines()
    config = {}
    section = None
    for line in lines:
        line = line.rstrip()
        if not line or line.strip().startswith('#'):
            continue
        m = re.match(r'^(\w+):\s*$', line)
        if m:
            section = m.group(1)
            config.setdefault(section, {})
            continue
        m = re.match(r'^  (\w+):\s*(.*)$', line)
        if m and section:
            key, val = m.group(1), m.group(2).strip().split('#')[0].strip()
            if not val:
                continue
            if val in ('true', 'yes'):
                config[section][key] = True
            elif val in ('false', 'no'):
                config[section][key] = False
            elif val.isdigit():
                config[section][key] = int(val)
            elif re.match(r'^\d+\.\d+$', val):
                config[section][key] = float(val)
            else:
                config[section][key] = val.strip('"\'')
    defaults = {
        'paths': {'checkpoint_dir': str(root / 'data' / 'checkpoints'), 'log_dir': str(root / 'logs'),
                  'models_cache': str(root / 'models')},
        'translation': {'read_batch_size': 16, 'translation_batch_size': 8},
        'processing': {'skip_english': True, 'validate_translations': True, 'min_text_length': 50,
                       'max_text_length': 50000, 'enable_content_cleaning': True, 'enable_relevance_filter': True,
                       'enable_sentence_processing': True, 'remove_html_tags': True, 'remove_urls': False,
                       'min_word_count': 3, 'enable_spam_filter': True, 'enable_cybersecurity_filter': True,
                       'min_cybersecurity_keywords': 1, 'min_sentence_length': 15, 'max_sentence_length': 500,
                       'merge_short_sentences': True},
        'checkpoint': {'frequency': 1000, 'keep_last_n': 3},
        'logging': {'level': 'INFO', 'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s', 'file_prefix': 'translation_pipeline'},
    }
    for sec, kv in defaults.items():
        config.setdefault(sec, {})
        for k, v in kv.items():
            config[sec].setdefault(k, v)
    return config


def load_config(config_path: str) -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    if yaml is not None:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    return _load_config_fallback(str(config_file))


def validate_config(config: dict) -> None:
    """
    Validate configuration.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Check required paths
    input_path = Path(config['paths']['input_dataset'])
    if not input_path.exists():
        raise FileNotFoundError(f"Input dataset not found: {input_path}")
    
    model_path = Path(config['language_detection']['model_path'])
    if not model_path.exists():
        raise FileNotFoundError(f"Language detection model not found: {model_path}")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='DarkWeb Translation Pipeline - Translate multilingual dark web forum data to English',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default config
  python main.py
  
  # Run with custom config
  python main.py --config /path/to/config.yaml
  
  # Process first N records (e.g. 600 for ~1 hour at ~11 records/min)
  python main.py --max-records 600
  
  # Resume from checkpoint
  python main.py --resume
  
  # Override input/output paths
  python main.py --input /path/to/input.json --output /path/to/output.jsonl
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Override input dataset path from config'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Override output file path from config'
    )
    
    parser.add_argument(
        '--max-records', '-n',
        type=int,
        help='Maximum number of records to process (for testing)'
    )
    
    parser.add_argument(
        '--resume', '-r',
        action='store_true',
        help='Resume from last checkpoint (default behavior)'
    )
    
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset and start from beginning (ignore checkpoints)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Override config with command line arguments
    if args.input:
        config['paths']['input_dataset'] = args.input
    
    if args.output:
        config['paths']['output_file'] = args.output
    
    if args.verbose:
        config['logging']['level'] = 'DEBUG'
    
    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("DarkWeb Translation Pipeline")
    logger.info("="*60)
    
    # Validate configuration
    try:
        validate_config(config)
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)
    
    # Handle reset flag
    if args.reset:
        logger.warning("Resetting pipeline - removing checkpoints")
        checkpoint_dir = Path(config['paths']['checkpoint_dir'])
        if checkpoint_dir.exists():
            import shutil
            shutil.rmtree(checkpoint_dir)
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Remove output file if exists
        output_file = Path(config['paths']['output_file'])
        if output_file.exists():
            output_file.unlink()
    
    # Initialize and run processor
    try:
        logger.info("Initializing batch processor...")
        processor = BatchProcessor(config)
        
        logger.info("Starting processing...")
        logger.info(f"Input: {config['paths']['input_dataset']}")
        logger.info(f"Output: {config['paths']['output_file']}")
        
        if args.max_records:
            logger.info(f"Max records: {args.max_records}")
        
        processor.process(max_records=args.max_records)
        
        logger.info("="*60)
        logger.info("Pipeline completed successfully!")
        logger.info("="*60)
        
    except KeyboardInterrupt:
        logger.warning("\nProcessing interrupted by user")
        logger.info("Progress has been saved. You can resume by running the script again.")
        sys.exit(130)
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

