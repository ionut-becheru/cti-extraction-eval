#!/usr/bin/env bash
cd "$(dirname "$0")/../.."
for cfg in "de opus-mt" "ru nllb-600M" "de nllb-600M"; do set -- $cfg; [ -f runs/E8_mt_ioc/placeholder_styles_$2_$1.json ] || .venv/bin/python scripts/mt/placeholder_styles.py $1 $2 > logs/placeholder_$2_$1.log 2>&1; done
echo "PLACEHOLDERS DONE $(date)"
