#!/usr/bin/env python3
"""Score the thesis dictionary/regex/spaCy NER (experiments/baseline/src/cybersec_ner.py, unmodified) against gold NER.

Entity-level strict (exact span + type) and relaxed (any token overlap, same type) P/R/F1 per coarse type, per dataset,
with bootstrap 95% CIs over sentences. Also reports "coverage": share of gold entity mentions whose type the thesis
schema cannot represent (UNCOVERED).

Prediction label mapping (thesis label -> coarse):
  CVE->VULNERABILITY, MALWARE->MALWARE, THREAT_ACTOR->THREAT_ACTOR, TOOL->TOOL, IP->IP, HASH->HASH, DOMAIN->DOMAIN,
  URL->URL, EMAIL->EMAIL, FILEPATH->FILE, TARGET_LOCATION->LOCATION; CWE/MITRE_TECHNIQUE/CRYPTO_WALLET/PORT/RANSOM_AMOUNT/CAMPAIGN
  have no gold counterpart and are ignored (counted separately as 'unscorable predictions').
  For DNRTI, MALWARE and TOOL predictions are both mapped to MALWARE_TOOL. For CyNER, IP/HASH/DOMAIN/URL/EMAIL/FILE -> INDICATOR.

Usage: python eval_dictionary_ner.py --out runs/N0_dictionary_ner [--splits test] [--boot 1000]
"""
import argparse, json, sys, pathlib, collections, time, logging
import numpy as np, yaml
HERE = pathlib.Path(__file__).resolve().parent; EXP = HERE.parent.parent
sys.path.insert(0, str(EXP / 'baseline'))
logging.disable(logging.WARNING)
from src.cybersec_ner import CybersecNER
GOLD = EXP / 'data/gold_ner'
PRED2COARSE = {'CVE': 'VULNERABILITY', 'MALWARE': 'MALWARE', 'THREAT_ACTOR': 'THREAT_ACTOR', 'TOOL': 'TOOL', 'IP': 'IP', 'HASH': 'HASH',
               'DOMAIN': 'DOMAIN', 'URL': 'URL', 'EMAIL': 'EMAIL', 'FILEPATH': 'FILE', 'TARGET_LOCATION': 'LOCATION'}
_IND = {'IP': 'INDICATOR', 'HASH': 'INDICATOR', 'DOMAIN': 'INDICATOR', 'URL': 'INDICATOR', 'EMAIL': 'INDICATOR', 'FILE': 'INDICATOR'}
DS_ADJUST = {'dnrti': {'MALWARE': 'MALWARE_TOOL', 'TOOL': 'MALWARE_TOOL'}, 'cyner': _IND, 'attacker': _IND}

def spans_from_bio(tags):
    out = []; start = None; typ = None
    for i, t in enumerate(tags + ['O']):
        if t.startswith('B-') or t == 'O' or (t.startswith('I-') and t[2:] != typ):
            if start is not None: out.append((start, i, typ)); start = None; typ = None
            if t.startswith('B-'): start, typ = i, t[2:]
            elif t.startswith('I-'): start, typ = i, t[2:]
    return out

def char_to_tok(offsets, s, e):
    """token index range [ts, te) covering char span [s,e)."""
    ts = te = None
    for i, (a, b) in enumerate(offsets):
        if b > s and a < e:
            if ts is None: ts = i
            te = i + 1
    return ts, te

def load_ner():
    cfg = yaml.safe_load(open(EXP / 'runs/B0_asrun/config.yaml'))
    cfg['nlp']['malware_dict_path'] = str(EXP / 'baseline/data/dictionaries/malware_families.yaml')
    return CybersecNER(cfg)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--splits', default='test')
    ap.add_argument('--boot', type=int, default=1000); ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--datasets', default='aptner,dnrti,cyner,annoctr,attacker')
    a = ap.parse_args(); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ner = load_ner(); t0 = time.time(); results = {}; rng = np.random.default_rng(a.seed)
    for ds in a.datasets.split(','):
        for split in a.splits.split(','):
            sents = [json.loads(l) for l in open(GOLD / f'{ds}_{split}.jsonl')]
            per_sent = []  # per sentence: dict type -> [tp_strict, tp_relaxed, n_pred, n_gold]
            unscorable = collections.Counter(); gold_uncovered = 0; gold_total = 0; pred_dump = []; full_bio = []
            for s in sents:
                gold = spans_from_bio(s['coarse']); gold_total += len(gold)
                gold_uncovered += sum(1 for g in gold if g[2] == 'UNCOVERED')
                gold = [g for g in gold if g[2] != 'UNCOVERED']
                preds = []
                for e in ner.extract(s['text']):
                    c = PRED2COARSE.get(e.label)
                    if c is None: unscorable[e.label] += 1; continue
                    c = DS_ADJUST.get(ds.split('__')[0], {}).get(c, c)
                    ts, te = char_to_tok(s['offsets'], e.start, e.end)
                    if ts is None: continue
                    preds.append((ts, te, c))
                preds = list(set(preds))
                bio = ['O'] * len(s['tokens'])
                for ts, te, c in sorted(preds, key=lambda x: -(x[1] - x[0])):
                    if any(bio[i] != 'O' for i in range(ts, te)): continue
                    bio[ts] = 'B-' + c
                    for i in range(ts + 1, te): bio[i] = 'I-' + c
                full_bio.append({'id': s['id'], 'pred': bio})
                d = collections.defaultdict(lambda: [0, 0, 0, 0])
                gset = set(gold)
                for p in preds:
                    d[p[2]][2] += 1
                    if p in gset: d[p[2]][0] += 1
                    if any(g[2] == p[2] and g[0] < p[1] and p[0] < g[1] for g in gold): d[p[2]][1] += 1
                for g in gold: d[g[2]][3] += 1
                per_sent.append(dict(d))
                if len(pred_dump) < 300:
                    pred_dump.append({'id': s['id'], 'text': s['text'][:300], 'gold': [(s['tokens'][g[0]:g[1]], g[2]) for g in gold],
                                      'pred': [(s['tokens'][p[0]:p[1]], p[2]) for p in preds]})
            types = sorted({t for d in per_sent for t in d})
            def agg(idx):
                tot = collections.defaultdict(lambda: [0, 0, 0, 0])
                for i in idx:
                    for t, v in per_sent[i].items():
                        for k in range(4): tot[t][k] += v[k]
                res = {}
                allv = [0, 0, 0, 0]
                for t in types:
                    v = tot[t]; 
                    for k in range(4): allv[k] += v[k]
                    res[t] = prf(v)
                res['MICRO_ALL'] = prf(allv); return res
            def prf(v):
                tp_s, tp_r, npred, ngold = v
                ps = tp_s / npred if npred else 0.0; rs = tp_s / ngold if ngold else 0.0; fs = 2 * ps * rs / (ps + rs) if ps + rs else 0.0
                pr = tp_r / npred if npred else 0.0; rr = tp_r / ngold if ngold else 0.0; fr = 2 * pr * rr / (pr + rr) if pr + rr else 0.0
                return {'P': ps, 'R': rs, 'F1': fs, 'P_relaxed': pr, 'R_relaxed': rr, 'F1_relaxed': fr, 'n_pred': npred, 'n_gold': ngold}
            point = agg(range(len(per_sent)))
            boots = collections.defaultdict(lambda: collections.defaultdict(list))
            for _ in range(a.boot):
                idx = rng.integers(0, len(per_sent), len(per_sent)); r = agg(idx)
                for t, m in r.items():
                    for k in ('P', 'R', 'F1', 'F1_relaxed'): boots[t][k].append(m[k])
            for t in point:
                point[t]['ci95'] = {k: [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)] for k, v in boots[t].items()}
                for k in ('P', 'R', 'F1', 'P_relaxed', 'R_relaxed', 'F1_relaxed'): point[t][k] = round(point[t][k], 4)
            results[f'{ds}_{split}'] = {'n_sentences': len(sents), 'gold_mentions_total': gold_total, 'gold_uncovered': gold_uncovered,
                                        'gold_uncovered_pct': round(100 * gold_uncovered / max(gold_total, 1), 1),
                                        'unscorable_predictions': dict(unscorable), 'metrics': point}
            json.dump(pred_dump, open(out / f'preds_{ds}_{split}.json', 'w'), indent=1, ensure_ascii=False)
            with open(out / f'preds_full_{ds}_{split}.jsonl', 'w') as fb:
                for x in full_bio: fb.write(json.dumps(x) + '\n')
            print(f"\n== {ds}/{split}: {len(sents)} sents, gold {gold_total} ({gold_uncovered} uncovered = {100*gold_uncovered/max(gold_total,1):.1f}%)")
            for t, m in point.items():
                print(f"  {t:14s} P={m['P']:.3f} R={m['R']:.3f} F1={m['F1']:.3f} {m['ci95']['F1']}  relaxedF1={m['F1_relaxed']:.3f}  pred={m['n_pred']} gold={m['n_gold']}")
    results['_meta'] = {'seconds': round(time.time() - t0, 1), 'boot': a.boot, 'seed': a.seed, 'ner': 'experiments/baseline/src/cybersec_ner.py (thesis copy)',
                        'config': 'runs/B0_asrun/config.yaml nlp section'}
    json.dump(results, open(out / 'dictionary_ner_eval.json', 'w'), indent=1)

if __name__ == '__main__': main()
