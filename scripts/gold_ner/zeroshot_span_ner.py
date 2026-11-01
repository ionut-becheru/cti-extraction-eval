#!/usr/bin/env python3
"""Zero-shot span NER (GLiNER / NuNER-Zero) on gold test sets in the coarse schema.

Label descriptions are fixed (below); the decision threshold is chosen on the dev split of each corpus (grid 0.2..0.7)
and then applied to test. Predictions are mapped back to token BIO for the shared scorer.

Usage: python zeroshot_span_ner.py --model urchade/gliner_large-v2.1 --datasets aptner,dnrti,cyner,annoctr,attacker --out runs/E3_zs/gliner_large
"""
import argparse, json, pathlib, time, sys, collections
import numpy as np, torch
HERE = pathlib.Path(__file__).resolve().parent; EXP = HERE.parent.parent; GOLD = EXP / 'data/gold_ner'
sys.path.insert(0, str(HERE)); from ner_metrics import score_bio
# natural-language labels given to the zero-shot model -> coarse type
LABELS = {'threat actor or APT group': 'THREAT_ACTOR', 'malware family or malicious software': 'MALWARE', 'software tool or utility': 'TOOL',
          'vulnerability or CVE identifier': 'VULNERABILITY', 'IP address': 'IP', 'file hash': 'HASH', 'domain name': 'DOMAIN', 'URL': 'URL',
          'email address': 'EMAIL', 'file name or file path': 'FILE', 'location or country': 'LOCATION'}
# per-corpus adjustments (same as gazetteer audit): DNRTI merges malware+tool; CyNER/AttackER merge IOC types into INDICATOR
_IND = {'IP': 'INDICATOR', 'HASH': 'INDICATOR', 'DOMAIN': 'INDICATOR', 'URL': 'INDICATOR', 'EMAIL': 'INDICATOR', 'FILE': 'INDICATOR'}
DS_ADJUST = {'dnrti': {'MALWARE': 'MALWARE_TOOL', 'TOOL': 'MALWARE_TOOL'}, 'cyner': _IND, 'attacker': _IND}

def to_bio(rows, ents_list, ds):
    out = []
    for r, ents in zip(rows, ents_list):
        tags = ['O'] * len(r['tokens']); offs = r['offsets']
        for e in sorted(ents, key=lambda x: -(x['end'] - x['start'])):
            typ = DS_ADJUST.get(base(ds), {}).get(LABELS[e['label']], LABELS[e['label']])
            idx = [i for i, (a, b) in enumerate(offs) if b > e['start'] and a < e['end']]
            if not idx or any(tags[i] != 'O' for i in idx): continue
            tags[idx[0]] = 'B-' + typ
            for i in idx[1:]: tags[i] = 'I-' + typ
        out.append(tags)
    return out

def base(ds): return ds.split('__')[0]

def labels_for(ds):
    ds = base(ds)
    """Only ask for label descriptions whose coarse type the corpus annotates (a practitioner would not ask CyNER for actors)."""
    train = [json.loads(l) for l in open(GOLD / f'{ds}_train.jsonl')]
    present = {t[2:] for r in train for t in r['coarse'] if t != 'O' and not t.endswith('UNCOVERED')}
    adj = DS_ADJUST.get(ds, {})
    return [d for d, c in LABELS.items() if adj.get(c, c) in present]

def run_model(model, rows, thr, labs, bs=4):
    """length-sorted batches; on CUDA OOM fall back to one text at a time (AnnoCTR has very long 'sentences')."""
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]['text'])); ents = [None] * len(rows)
    for i in range(0, len(order), bs):
        idx = order[i:i + bs]; texts = [rows[j]['text'] for j in idx]
        try: out = model.batch_predict_entities(texts, labs, threshold=thr)
        except torch.OutOfMemoryError:
            torch.cuda.empty_cache(); out = [model.batch_predict_entities([t], labs, threshold=thr)[0] for t in texts]
        for j, e in zip(idx, out): ents[j] = e
    return ents

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--model', required=True); ap.add_argument('--datasets', default='aptner,dnrti,cyner,annoctr,attacker')
    ap.add_argument('--out', required=True); ap.add_argument('--boot', type=int, default=1000); ap.add_argument('--dev-max', type=int, default=500); ap.add_argument('--bs', type=int, default=4)
    a = ap.parse_args(); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    from gliner import GLiNER
    t0 = time.time(); torch.cuda.reset_peak_memory_stats()
    model = GLiNER.from_pretrained(a.model).to('cuda'); model.eval()
    results = {'model': a.model, 'labels': LABELS, 'eval': {}}
    for ds in a.datasets.split(','):
        dev = [json.loads(l) for l in open(GOLD / f'{base(ds)}_dev.jsonl')][:a.dev_max]; test = [json.loads(l) for l in open(GOLD / f'{ds}_test.jsonl')]
        gold_dev = [['O' if t.endswith('UNCOVERED') else t for t in r['coarse']] for r in dev]
        # threshold search on dev: run once at low threshold, filter by score
        labs = labels_for(ds); raw = run_model(model, dev, 0.1, labs, a.bs); best = (-1, 0.5)
        for thr in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
            filt = [[e for e in es if e['score'] >= thr] for es in raw]
            f1 = score_bio(gold_dev, to_bio(dev, filt, ds), boot=0)['MICRO']['F1']
            if f1 > best[0]: best = (f1, thr)
        thr = best[1]; t1 = time.time()
        ents = run_model(model, test, thr, labs, a.bs); sec = time.time() - t1
        pred = to_bio(test, ents, ds); gold = [['O' if t.endswith('UNCOVERED') else t for t in r['coarse']] for r in test]
        m = score_bio(gold, pred, boot=a.boot, seed=0)
        results['eval'][ds] = {'labels_used': labs, 'threshold': thr, 'dev_f1_at_threshold': best[0], 'metrics': m, 'test_seconds': round(sec, 1), 'n_test': len(test)}
        with open(out / f'preds_{ds}.jsonl', 'w') as f:
            for r, p in zip(test, pred): f.write(json.dumps({'id': r['id'], 'pred': p}) + '\n')
        print(f"{ds}: thr={thr} strict micro F1 {m['MICRO']['F1']:.4f} {m['MICRO']['ci95']['F1']} relaxed {m['MICRO']['F1_relaxed']:.4f} ({sec:.0f}s)", flush=True)
        for t, v in m.items():
            if t != 'MICRO': print(f"   {t:14s} P={v['P']:.3f} R={v['R']:.3f} F1={v['F1']:.3f}")
    results['wall_seconds'] = round(time.time() - t0, 1); results['peak_vram_mib'] = int(torch.cuda.max_memory_allocated() / 2**20)
    json.dump(results, open(out / 'metrics.json', 'w'), indent=1)

if __name__ == '__main__': main()
