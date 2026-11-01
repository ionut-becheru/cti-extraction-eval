"""Shared entity-level scorer: strict (exact span+type) and relaxed (token-overlap+type) P/R/F1, per type + micro, bootstrap CIs over sentences."""
import collections, numpy as np

def spans(tags):
    out = []; start = None; typ = None
    for i, t in enumerate(list(tags) + ['O']):
        if t.startswith('B-') or t == 'O' or (t.startswith('I-') and t[2:] != typ):
            if start is not None: out.append((start, i, typ)); start = None; typ = None
            if t.startswith('B-') or t.startswith('I-'): start, typ = i, t[2:]
    return out

def _prf(v):
    tp_s, tp_r, npred, ngold = v
    ps = tp_s / npred if npred else 0.0; rs = tp_s / ngold if ngold else 0.0; fs = 2 * ps * rs / (ps + rs) if ps + rs else 0.0
    pr = tp_r / npred if npred else 0.0; rr = tp_r / ngold if ngold else 0.0; fr = 2 * pr * rr / (pr + rr) if pr + rr else 0.0
    return {'P': round(ps, 4), 'R': round(rs, 4), 'F1': round(fs, 4), 'P_relaxed': round(pr, 4), 'R_relaxed': round(rr, 4), 'F1_relaxed': round(fr, 4), 'n_pred': npred, 'n_gold': ngold}

def per_sentence_counts(gold_tags, pred_tags, ignore=('UNCOVERED',)):
    """returns list of dict type -> [tp_strict, tp_relaxed, n_pred, n_gold]"""
    out = []
    for g, p in zip(gold_tags, pred_tags):
        gs = [s for s in spans(g) if s[2] not in ignore]; ps = [s for s in spans(p) if s[2] not in ignore]
        d = collections.defaultdict(lambda: [0, 0, 0, 0]); gset = set(gs)
        for s in ps:
            d[s[2]][2] += 1
            if s in gset: d[s[2]][0] += 1
            if any(x[2] == s[2] and x[0] < s[1] and s[0] < x[1] for x in gs): d[s[2]][1] += 1
        for s in gs: d[s[2]][3] += 1
        out.append(dict(d))
    return out

def aggregate(per_sent, idx, types):
    tot = collections.defaultdict(lambda: [0, 0, 0, 0])
    for i in idx:
        for t, v in per_sent[i].items():
            for k in range(4): tot[t][k] += v[k]
    res = {t: _prf(tot[t]) for t in types}; allv = [0, 0, 0, 0]
    for t in types:
        for k in range(4): allv[k] += tot[t][k]
    res['MICRO'] = _prf(allv); return res

def score_bio(gold_tags, pred_tags, boot=1000, seed=0, ignore=('UNCOVERED',), restrict_types=None):
    per = per_sentence_counts(gold_tags, pred_tags, ignore)
    types = sorted({t for d in per for t in d}) if restrict_types is None else sorted(restrict_types)
    if restrict_types is not None:
        per = [{t: v for t, v in d.items() if t in restrict_types} for d in per]
    point = aggregate(per, range(len(per)), types)
    if boot:
        rng = np.random.default_rng(seed); B = collections.defaultdict(lambda: collections.defaultdict(list))
        for _ in range(boot):
            idx = rng.integers(0, len(per), len(per)); r = aggregate(per, idx, types)
            for t, m in r.items():
                for k in ('P', 'R', 'F1', 'F1_relaxed'): B[t][k].append(m[k])
        for t in point: point[t]['ci95'] = {k: [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)] for k, v in B[t].items()}
    return point
