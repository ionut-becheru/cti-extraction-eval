#!/usr/bin/env bash
# E2: fine-tune encoders on each corpus. Sequential (one GPU). Skips runs whose metrics.json exists.
cd "$(dirname "$0")/../.."
ALL=aptner,dnrti,cyner,annoctr,attacker
for SCHEMA in coarse fine; do
for MODEL in microsoft/deberta-v3-base FacebookAI/roberta-base cisco-ai/SecureBERT2.0-base; do
  TAG=$(basename $MODEL | tr '[:upper:]' '[:lower:]' | sed 's/-base//; s/\.//g')
  for DS in aptner dnrti cyner annoctr attacker; do
    for SEED in 13; do
      OUT=runs/E2_ft/${TAG}_${DS}_${SCHEMA}_s${SEED}
      [ -f $OUT/metrics.json ] && continue
      EVAL=$DS; [ $SCHEMA = coarse ] && EVAL=$ALL
      echo "=== $OUT $(date)"
      SM=""; [ $SCHEMA = coarse ] && SM=1; SAVE_MODEL=$SM common/run_with_metrics.sh $OUT .venv/bin/python scripts/gold_ner/finetune_ner.py --model $MODEL --dataset $DS --schema $SCHEMA --seed $SEED --out $OUT --eval-on $EVAL --epochs 5
    done
  done
done; done
echo "E2 SWEEP DONE $(date)"
