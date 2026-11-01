#!/usr/bin/env bash
# E5: evaluate every extractor on the noisy variants of aptner / cyner / annoctr test sets.
cd "$(dirname "$0")/../.."
V=bt-ru,bt-de,bt-zh,bt-es,defang,boiler,lower,typo
for DS in aptner cyner annoctr; do
  SETS=$DS; for v in ${V//,/ }; do SETS=$SETS,${DS}__$v; done
  # gazetteer
  [ -f runs/E5_noise/gazetteer_$DS/dictionary_ner_eval.json ] || common/run_with_metrics.sh runs/E5_noise/gazetteer_$DS .venv/bin/python scripts/gold_ner/eval_dictionary_ner.py --out runs/E5_noise/gazetteer_$DS --datasets $SETS --splits test
  # fine-tuned encoders (saved coarse models)
  for TAG in roberta deberta-v3 securebert20; do
    M=runs/E2_ft/${TAG}_${DS}_coarse_s13/model
    [ -d $M ] || continue
    [ -f runs/E5_noise/${TAG}_$DS/metrics.json ] || common/run_with_metrics.sh runs/E5_noise/${TAG}_$DS .venv/bin/python scripts/gold_ner/eval_saved_ner.py --model-dir $M --datasets $SETS --out runs/E5_noise/${TAG}_$DS
  done
  # zero-shot span models
  [ -f runs/E5_noise/gliner_$DS/metrics.json ] || common/run_with_metrics.sh runs/E5_noise/gliner_$DS .venv/bin/python scripts/gold_ner/zeroshot_span_ner.py --model urchade/gliner_large-v2.1 --datasets $SETS --out runs/E5_noise/gliner_$DS
done
echo "E5 EVAL DONE $(date)"
