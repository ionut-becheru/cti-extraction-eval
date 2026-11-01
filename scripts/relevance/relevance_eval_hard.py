#!/usr/bin/env python3
"""Security-relevance filtering: easy (Wikipedia) vs hard (superuser/serverfault) negatives.

Positives: the same 3,000 corpus records as the thesis (reservoir seed 42), tagged by source.
Negatives: (easy) 3,000 cached Wikipedia leads; (hard) 3,000 superuser.com + 3,000 serverfault.com Q&A (non-security tags).
Methods:
  keyword     thesis RelevanceFilter (keyword-only, as evaluated in the thesis)
  nli         zero-shot NLI (MoritzLaurer/deberta-v3-large-zeroshot-v2.0), the layer the thesis describes but never ran; threshold 0.7 as in config,
              plus the threshold that maximises F1 on a 500/500 dev split (reported separately)
  ft-easy     RoBERTa-base classifier fine-tuned on positives vs Wikipedia negatives (train 2,000+2,000, dev 500+500) -> tested on hard negatives
  ft-hard     same, trained on positives vs hard negatives -> tested on Wikipedia negatives (symmetry check)
  ft-mixed    trained on positives vs mixed negatives
Test positives are the 500 held-out positives in every setting; all F1/P/R with 2,000-sample bootstrap CIs.

Usage: python relevance_eval_hard.py --out runs/E6_relevance [--methods keyword,nli,ft]
"""
import argparse, json, pathlib, random, sys, time, collections
import numpy as np, torch
EXP = pathlib.Path(__file__).resolve().parent.parent.parent; ROOT = EXP.parent
sys.path.insert(0, str(EXP / 'baseline')); sys.path.insert(0, str(EXP / 'scripts'))
from src.relevance_filter import RelevanceFilter
HARD = EXP / 'data/relevance'; NEG_WIKI = HARD / 'wikipedia_negatives.jsonl'; POS = HARD / 'positives.jsonl'  # see export_positives.py

def prf(y, p):
    y = np.asarray(y); p = np.asarray(p); tp = int(((y == 1) & (p == 1)).sum()); fp = int(((y == 0) & (p == 1)).sum()); fn = int(((y == 1) & (p == 0)).sum()); tn = int(((y == 0) & (p == 0)).sum())
    P = tp / max(tp + fp, 1); R = tp / max(tp + fn, 1); return {'P': round(P, 4), 'R': round(R, 4), 'F1': round(2 * P * R / max(P + R, 1e-12), 4), 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn, 'FPR': round(fp / max(fp + tn, 1), 4)}

def boot(y, p, B=2000, seed=0):
    y = np.asarray(y); p = np.asarray(p); rng = np.random.default_rng(seed); pos = np.where(y == 1)[0]; neg = np.where(y == 0)[0]; F = []; FPR = []
    for _ in range(B):
        i = np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))]); m = prf(y[i], p[i]); F.append(m['F1']); FPR.append(m['FPR'])
    ci = lambda v: [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
    return {'F1': ci(F), 'FPR': ci(FPR)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--methods', default='keyword,nli,ft'); ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args(); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True); rng = random.Random(a.seed)
    pos = [{'text': r['text'], 'src': r['src']} for r in map(json.loads, open(POS)) if r.get('text')]  # APTNER/DNRTI texts absent unless re-exported
    wiki = [{'text': json.loads(l)['extract'], 'src': 'wikipedia'} for l in open(NEG_WIKI) if l.strip()][:3000]
    hard = []
    for site in ['superuser', 'serverfault']:
        f = HARD / f'hard_neg_{site}.jsonl'
        if f.exists(): hard += [{'text': json.loads(l)['text'], 'src': site} for l in open(f)]
    rng.shuffle(pos); rng.shuffle(wiki); rng.shuffle(hard)
    # fixed split: test = last 500 positives, last 500 wiki, last 500 per hard site; train/dev from the rest
    def split(lst, n_test=500, n_dev=250):
        return lst[:-(n_test + n_dev)], lst[-(n_test + n_dev):-n_test], lst[-n_test:]
    pos_tr, pos_dv, pos_te = split(pos); wiki_tr, wiki_dv, wiki_te = split(wiki)
    hard_by = collections.defaultdict(list)
    for h in hard: hard_by[h['src']].append(h)
    hard_tr, hard_dv, hard_te = [], [], []
    for s, lst in hard_by.items():
        tr, dv, te = split(lst); hard_tr += tr; hard_dv += dv; hard_te += te
    sets = {'easy(wikipedia)': wiki_te, **{f'hard({s})': [h for h in hard_te if h['src'] == s] for s in hard_by}}
    results = {'n': {'pos_test': len(pos_te), **{k: len(v) for k, v in sets.items()}, 'pos_train': len(pos_tr), 'wiki_train': len(wiki_tr), 'hard_train': len(hard_tr)}, 'methods': {}}
    def evaluate(name, scorer, extra=None):
        results['methods'][name] = {'test': {}, **(extra or {})}
        p_pos = scorer([x['text'] for x in pos_te])
        for k, neg in sets.items():
            p_neg = scorer([x['text'] for x in neg]); y = [1] * len(p_pos) + [0] * len(p_neg); p = list(p_pos) + list(p_neg)
            m = prf(y, p); m['ci95'] = boot(y, p); results['methods'][name]['test'][k] = m
            print(f"{name:28s} vs {k:20s} P={m['P']:.3f} R={m['R']:.3f} F1={m['F1']:.3f} {m['ci95']['F1']} FPR={m['FPR']:.3f}", flush=True)
        # per-source recall on positives
        srcs = [x['src'] for x in pos_te]; results['methods'][name]['recall_by_source'] = {s: round(float(np.mean([pp for pp, ss in zip(p_pos, srcs) if ss == s])), 4) for s in sorted(set(srcs))}
    if 'keyword' in a.methods:
        rf = RelevanceFilter(min_length=50, max_length=50000, enable_spam_filter=True, enable_cybersecurity_filter=True, min_cybersecurity_keywords=1, zero_shot_enabled=False)
        evaluate('keyword(thesis)', lambda T: [1 if rf.is_relevant(t)[0] else 0 for t in T])
    if 'nli' in a.methods:
        from transformers import pipeline
        zs = pipeline('zero-shot-classification', model='MoritzLaurer/deberta-v3-large-zeroshot-v2.0', device=0, dtype=torch.bfloat16)
        labels = ['cybersecurity threat discussion', 'off-topic / non-security content']
        def nli_scores(T):
            outs = zs([t[:1024] for t in T], candidate_labels=labels, multi_label=False, batch_size=16); sc = []
            for o in outs: sc.append(float(dict(zip(o['labels'], o['scores']))[labels[0]]))
            return sc
        t0 = time.time(); dev_pos = nli_scores([x['text'] for x in pos_dv]); dev_neg = nli_scores([x['text'] for x in wiki_dv + hard_dv])
        best = max(((prf([1] * len(dev_pos) + [0] * len(dev_neg), [1 if s >= th else 0 for s in dev_pos + dev_neg])['F1'], th) for th in np.arange(0.3, 0.96, 0.05)))
        cache = {}
        def nli_pred_factory(th):
            def f(T):
                key = tuple(T)
                if key not in cache: cache[key] = nli_scores(T)
                return [1 if s >= th else 0 for s in cache[key]]
            return f
        evaluate('nli(deberta-v3-zs, thr=0.7 config)', nli_pred_factory(0.7), {'seconds_dev': round(time.time() - t0, 1)})
        evaluate(f'nli(deberta-v3-zs, thr={best[1]:.2f} dev-opt)', nli_pred_factory(best[1]), {'dev_f1': best[0], 'dev_threshold': float(best[1])})
        del zs; torch.cuda.empty_cache()
    if 'ft' in a.methods:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        def train_clf(neg_tr, neg_dv, tag):
            torch.manual_seed(a.seed); tok = AutoTokenizer.from_pretrained('FacebookAI/roberta-base'); mdl = AutoModelForSequenceClassification.from_pretrained('FacebookAI/roberta-base', num_labels=2).cuda()
            data = [(x['text'], 1) for x in pos_tr] + [(x['text'], 0) for x in neg_tr]; random.Random(a.seed).shuffle(data)
            opt = torch.optim.AdamW(mdl.parameters(), lr=2e-5, weight_decay=0.01); bs = 16
            for ep in range(2):
                mdl.train()
                for i in range(0, len(data), bs):
                    b = data[i:i + bs]; enc = tok([t for t, _ in b], truncation=True, max_length=256, padding=True, return_tensors='pt').to('cuda')
                    with torch.autocast('cuda', dtype=torch.bfloat16): loss = mdl(**enc, labels=torch.tensor([y for _, y in b]).cuda()).loss
                    loss.backward(); opt.step(); opt.zero_grad()
            mdl.eval()
            def pred(T):
                out = []
                for i in range(0, len(T), 32):
                    enc = tok(T[i:i + 32], truncation=True, max_length=256, padding=True, return_tensors='pt').to('cuda')
                    with torch.no_grad(), torch.autocast('cuda', dtype=torch.bfloat16): out += mdl(**enc).logits.argmax(-1).tolist()
                return out
            return pred
        evaluate('ft-roberta(pos vs wikipedia)', train_clf(wiki_tr, wiki_dv, 'easy'))
        if hard_tr:
            evaluate('ft-roberta(pos vs hard)', train_clf(hard_tr, hard_dv, 'hard'))
            mixed = wiki_tr[:len(wiki_tr) // 2] + hard_tr[:len(hard_tr) // 2]; evaluate('ft-roberta(pos vs mixed)', train_clf(mixed, wiki_dv + hard_dv, 'mixed'))
    json.dump(results, open(out / 'relevance_hard.json', 'w'), indent=1)

if __name__ == '__main__': main()
