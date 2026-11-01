#!/usr/bin/env python3
"""Evaluate a saved fine-tuned token classifier (from finetune_ner.py with SAVE_MODEL=1) on arbitrary gold test sets,
including noisy variants (<ds>__<variant>). Coarse schema. Strict + relaxed, bootstrap CIs.

Usage: python eval_saved_ner.py --model-dir runs/E2_ft/deberta-v3_aptner_coarse_s13/model --datasets aptner__bt-ru,aptner__defang --out runs/E5_noise/deberta_aptner
"""
import argparse, json, pathlib, sys, time, torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
HERE = pathlib.Path(__file__).resolve().parent; EXP = HERE.parent.parent; GOLD = EXP / 'data/gold_ner'
sys.path.insert(0, str(HERE)); from ner_metrics import score_bio
import finetune_ner
from finetune_ner import predict

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--model-dir', required=True); ap.add_argument('--datasets', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--boot', type=int, default=1000); ap.add_argument('--max-len', type=int, default=256); a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    finetune_ner.AMP = 'deberta' not in a.model_dir.lower()
    tok = AutoTokenizer.from_pretrained(a.model_dir); model = AutoModelForTokenClassification.from_pretrained(a.model_dir, dtype=torch.float32).to('cuda')
    id2label = {int(k): v for k, v in model.config.id2label.items()}; res = {'model_dir': a.model_dir, 'eval': {}}
    for ds in a.datasets.split(','):
        te = [json.loads(l) for l in open(GOLD / f'{ds}_test.jsonl')]
        gold = [['O' if t.endswith('UNCOVERED') else t for t in r['coarse']] for r in te]
        pred = predict(model, tok, te, id2label, a.max_len, 'cuda'); m = score_bio(gold, pred, boot=a.boot, seed=0)
        res['eval'][ds] = m
        with open(out / f'preds_{ds}.jsonl', 'w') as f:
            for r, p in zip(te, pred): f.write(json.dumps({'id': r['id'], 'pred': p}) + '\n')
        print(f"{ds}: strict micro F1 {m['MICRO']['F1']:.4f} {m['MICRO']['ci95']['F1']} relaxed {m['MICRO']['F1_relaxed']:.4f}", flush=True)
    res['wall_seconds'] = round(time.time() - t0, 1); json.dump(res, open(out / 'metrics.json', 'w'), indent=1)

if __name__ == '__main__': main()
