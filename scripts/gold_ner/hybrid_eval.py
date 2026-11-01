#!/usr/bin/env python3
"""Hybrid extractor scored from saved predictions: regex/gazetteer predictions for IOC-shaped types + a learned model's
predictions for name types. No new training. Also scores the two components alone on the same sentences for reference.

Usage: python hybrid_eval.py --gaz runs/N0_dictionary_ner --model-run runs/E2_ft/roberta_aptner_coarse_s13 --dataset aptner --out runs/E7_hybrid/roberta_aptner
       (for noisy sets: --dataset aptner__defang --gaz runs/E5_noise/gazetteer_aptner --model-run runs/E5_noise/roberta_aptner)
"""
import argparse, json, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent; EXP = HERE.parent.parent; GOLD = EXP / 'data/gold_ner'
sys.path.insert(0, str(HERE)); from ner_metrics import score_bio, spans
REGEX_TYPES = {'IP', 'HASH', 'EMAIL', 'URL', 'DOMAIN', 'VULNERABILITY', 'INDICATOR'}

def load_preds(path):
    return {json.loads(l)['id']: json.loads(l)['pred'] for l in open(path)}

def merge(gaz, mdl, n):
    """model tags for name types; regex/gazetteer tags for REGEX_TYPES; regex wins on overlap (its precision is ~1.0)."""
    out = ['O'] * n
    for s, e, t in spans(mdl):
        if t in REGEX_TYPES: continue
        out[s] = 'B-' + t
        for i in range(s + 1, e): out[i] = 'I-' + t
    for s, e, t in spans(gaz):
        if t not in REGEX_TYPES: continue
        for i in range(s, e):  # clear anything overlapping
            if out[i] != 'O':
                j = i
                while j < n and out[j] != 'O' and (j == i or out[j].startswith('I-')): out[j] = 'O'; j += 1
        out[s] = 'B-' + t
        for i in range(s + 1, e): out[i] = 'I-' + t
    return out

HIGH_PREC = {'IP', 'HASH', 'EMAIL', 'URL', 'VULNERABILITY'}

def gapfill(gaz, mdl, n, allowed):
    """model predictions kept as-is; regex predictions of high-precision types annotated in the corpus are added only where the
    model predicted nothing (no overlap)."""
    out = list(mdl)
    for s, e, t in spans(gaz):
        if t not in allowed: continue
        if any(out[i] != 'O' for i in range(s, e)): continue
        out[s] = 'B-' + t
        for i in range(s + 1, e): out[i] = 'I-' + t
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--gaz', required=True); ap.add_argument('--model-run', required=True); ap.add_argument('--dataset', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--boot', type=int, default=1000); a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True); ds = a.dataset
    rows = [json.loads(l) for l in open(GOLD / f'{ds}_test.jsonl')]; gold = [['O' if t.endswith('UNCOVERED') else t for t in r['coarse']] for r in rows]
    gp = load_preds(pathlib.Path(a.gaz) / f'preds_full_{ds}_test.jsonl'); mp = load_preds(pathlib.Path(a.model_run) / f'preds_{ds}.jsonl')
    G = [gp[r['id']] for r in rows]; M = [mp[r['id']] for r in rows]; H = [merge(g, m, len(r['tokens'])) for g, m, r in zip(G, M, rows)]
    gold_types = {t[2:] for g in gold for t in g if t != 'O'}
    allowed = (HIGH_PREC | ({'INDICATOR'} if 'INDICATOR' in gold_types else set())) & gold_types
    GF = [gapfill(g, m, len(r['tokens']), allowed) for g, m, r in zip(G, M, rows)]
    res = {'dataset': ds, 'gaz': a.gaz, 'model_run': a.model_run, 'regex_types_override': sorted(REGEX_TYPES), 'regex_types_gapfill': sorted(allowed),
           'gazetteer': score_bio(gold, G, boot=a.boot), 'model': score_bio(gold, M, boot=a.boot), 'hybrid_override': score_bio(gold, H, boot=a.boot),
           'hybrid_gapfill': score_bio(gold, GF, boot=a.boot)}
    json.dump(res, open(out / f'hybrid_{ds}.json', 'w'), indent=1)
    for k in ('gazetteer', 'model', 'hybrid_override', 'hybrid_gapfill'): print(f"{ds} {k:16s} strict F1 {res[k]['MICRO']['F1']:.4f} {res[k]['MICRO']['ci95']['F1']} relaxed {res[k]['MICRO']['F1_relaxed']:.4f}")

if __name__ == '__main__': main()
