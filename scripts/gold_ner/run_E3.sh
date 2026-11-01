#!/usr/bin/env bash
cd "$(dirname "$0")/../.."; ALL=aptner,dnrti,cyner,annoctr,attacker
[ -f runs/E3_zs/gliner_large/metrics.json ] || common/run_with_metrics.sh runs/E3_zs/gliner_large .venv/bin/python scripts/gold_ner/zeroshot_span_ner.py --model urchade/gliner_large-v2.1 --datasets $ALL --out runs/E3_zs/gliner_large --bs 2
[ -f runs/E3_zs/nuner_zero/metrics.json ] || common/run_with_metrics.sh runs/E3_zs/nuner_zero .venv/bin/python scripts/gold_ner/zeroshot_span_ner.py --model numind/NuNER_Zero --datasets $ALL --out runs/E3_zs/nuner_zero --bs 2
echo "E3 DONE $(date)"
