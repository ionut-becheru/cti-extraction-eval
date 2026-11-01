#!/usr/bin/env bash
# Sequential GPU queue for everything after the E2 sweep. Idempotent: each step skips if its metrics.json exists.
cd "$(dirname "$0")/.."
ALL=aptner,dnrti,cyner,annoctr,attacker
echo "queue start $(date)"
while ! grep -q "E2 SWEEP DONE" logs/E2_sweep.log; do sleep 30; done
# re-run DeBERTa runs that trained with fp16 weights (NaN): detect by train_loss NaN in metrics.json
for d in runs/E2_ft/deberta-v3_*; do
  [ -f $d/metrics.json ] && .venv/bin/python -c "import json,math,sys; h=json.load(open('$d/metrics.json'))['history']; sys.exit(0 if any(math.isnan(x['train_loss']) for x in h) else 1)" && { echo "removing NaN run $d"; rm -rf $d; }
done
scripts/gold_ner/run_E2_sweep.sh >> logs/E2_sweep.log 2>&1
# extra seeds for the transfer backbone (RoBERTa; cheapest and no dtype caveats)
for DS in aptner dnrti cyner annoctr attacker; do for SEED in 17 19; do
  OUT=runs/E2_ft/roberta_${DS}_coarse_s${SEED}; [ -f $OUT/metrics.json ] && continue
  common/run_with_metrics.sh $OUT .venv/bin/python scripts/gold_ner/finetune_ner.py --model FacebookAI/roberta-base --dataset $DS --schema coarse --seed $SEED --out $OUT --eval-on $ALL --epochs 5
done; done
# E3 zero-shot span models
[ -f runs/E3_zs/gliner_large/metrics.json ] || common/run_with_metrics.sh runs/E3_zs/gliner_large .venv/bin/python scripts/gold_ner/zeroshot_span_ner.py --model urchade/gliner_large-v2.1 --datasets $ALL --out runs/E3_zs/gliner_large
[ -f runs/E3_zs/nuner_zero/metrics.json ] || common/run_with_metrics.sh runs/E3_zs/nuner_zero .venv/bin/python scripts/gold_ner/zeroshot_span_ner.py --model numind/NuNER_Zero --datasets $ALL --out runs/E3_zs/nuner_zero
# E4 local LLMs (full test sets)
for CFG in "qwen3_8b_0shot Qwen/Qwen3-8B 0" "qwen3_8b_5shot Qwen/Qwen3-8B 5" "fsec8b_0shot fdtn-ai/Foundation-Sec-8B-Instruct 0" "fsec8b_5shot fdtn-ai/Foundation-Sec-8B-Instruct 5"; do
  set -- $CFG; OUT=runs/E4_llm/$1; [ -f $OUT/metrics.json ] && continue
  common/run_with_metrics.sh $OUT .venv/bin/python scripts/gold_ner/llm_ner.py --model $2 --datasets $ALL --shots $3 --bs 16 --out $OUT
done
# E5 noise evaluation (waits for the noisy sets)
while ! grep -q "run finished" runs/E5_noise/make_sets/stdout.log; do sleep 30; done
scripts/noise/run_E5_eval.sh > logs/E5_eval.log 2>&1
# LLM on noisy sets (Qwen3 0-shot only, budget)
for DS in aptner cyner annoctr; do SETS=$DS; for v in bt-ru bt-de bt-zh bt-es defang boiler lower typo; do SETS=$SETS,${DS}__$v; done
  OUT=runs/E5_noise/qwen3_0shot_$DS; [ -f $OUT/metrics.json ] || common/run_with_metrics.sh $OUT .venv/bin/python scripts/gold_ner/llm_ner.py --model Qwen/Qwen3-8B --datasets $SETS --shots 0 --bs 16 --out $OUT
done
.venv/bin/python scripts/aggregate_tables.py > logs/aggregate.log 2>&1
echo "QUEUE DONE $(date)"
