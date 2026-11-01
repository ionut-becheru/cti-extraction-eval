#!/usr/bin/env bash
# Re-run everything behind the paper. Idempotent: finished steps are skipped when their outputs exist.
# Prerequisites: .venv built from env/requirements.txt (python 3.11), one GPU with >= 24 GB, `unrar` for DNRTI,
# network access for model and data downloads. Total GPU time for the full sweep is roughly 4-6 hours on an RTX 5090.
set -e; cd "$(dirname "$0")"; PY=.venv/bin/python; mkdir -p logs data/external/cache
echo "[1] gold NER corpora (downloaded from their original sources on first run; APTNER and DNRTI are not redistributed here)"
[ -d data/external/cache/aptner ] || git clone -q --depth 1 https://github.com/wangxuren/APTNER data/external/cache/aptner
[ -f data/external/cache/dnrti/DNRTI/train.txt ] || { mkdir -p data/external/cache/dnrti; curl -sL "https://raw.githubusercontent.com/SCreaMxp/DNRTI-A-Large-scale-Dataset-for-Named-Entity-Recognition-in-Threat-Intelligence/master/DNRTI.rar" -o data/external/cache/dnrti/DNRTI.rar; (cd data/external/cache/dnrti && { command -v unrar >/dev/null && unrar x -o+ DNRTI.rar >/dev/null; } || { command -v 7z >/dev/null && 7z x -y DNRTI.rar >/dev/null; } || { command -v bsdtar >/dev/null && bsdtar -xf DNRTI.rar; } || { echo "DNRTI.rar needs unrar, 7z or bsdtar (libarchive)"; exit 1; }); }
[ -d data/external/cache/cyner ] || git clone -q --depth 1 https://github.com/aiforsec/CyNER data/external/cache/cyner
[ -d data/external/annoctr ] || git clone -q --depth 1 https://github.com/boschresearch/anno-ctr-lrec-coling-2024 data/external/annoctr
mkdir -p data/external/attacker; for f in train dev test; do [ -f data/external/attacker/$f.json ] || curl -sL "https://zenodo.org/api/records/10276922/files/$f.json/content" -o data/external/attacker/$f.json; done
$PY scripts/gold_ner/load_gold.py
echo "[2] models"; scripts/download_models.sh > logs/download_models.log 2>&1 || true
echo "[3] gazetteer audit"; [ -f runs/N0_dictionary_ner/dictionary_ner_eval.json ] || $PY scripts/gold_ner/eval_dictionary_ner.py --out runs/N0_dictionary_ner
echo "[4] relevance filtering (hard negatives and positives are shipped in data/relevance; see scripts/relevance/export_positives.py)"
for s in superuser serverfault; do [ -f data/relevance/hard_neg_$s.jsonl ] || { [ -f data/external/$s.com.7z ] || curl -sL "https://archive.org/download/stackexchange/$s.com.7z" -o data/external/$s.com.7z; $PY scripts/relevance/build_hard_negatives.py --site $s.com --n 3000 --out data/relevance/hard_neg_$s.jsonl; }; done
[ -f data/relevance/positives.jsonl ] || echo "data/relevance/positives.jsonl is missing: rebuild the corpus (baseline/scripts/ingest) and run scripts/relevance/export_positives.py --with-text; see README"
[ -f runs/E6_relevance/relevance_hard.json ] || common/run_with_metrics.sh runs/E6_relevance $PY scripts/relevance/relevance_eval_hard.py --out runs/E6_relevance
echo "[5] noisy sets"; [ -f runs/E5_noise/make_sets/run_meta.json ] || common/run_with_metrics.sh runs/E5_noise/make_sets $PY scripts/noise/make_noisy_sets.py
echo "[6] encoder sweep + queue (E2..E5)"; scripts/gold_ner/run_E2_sweep.sh > logs/E2_sweep.log 2>&1; scripts/run_queue.sh > logs/queue.log 2>&1
echo "[6b] multi-system MT IOC integrity + placeholder styles"; [ -f runs/E8_mt_ioc/run_meta.json ] || common/run_with_metrics.sh runs/E8_mt_ioc $PY scripts/mt/mt_ioc_integrity.py --langs ru,de --out runs/E8_mt_ioc; scripts/mt/run_placeholders.sh > logs/placeholders_all.log 2>&1
echo "[7] tables -> paper_tables/*.tex, tables.md, paper_numbers.json, paper_numbers.md"; $PY scripts/aggregate_tables.py; $PY scripts/write_paper_numbers.py
