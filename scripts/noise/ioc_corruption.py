#!/usr/bin/env python3
"""Silent IOC corruption after MarianMT round trips: regex-extractable strings in the back-translated text that do not occur in the
original text (i.e. a downstream regex extractor would emit a wrong indicator). Per IOC type and language, over the three test sets.
Writes experiments/data/gold_ner/ioc_corruption.json.
"""
import json, re, pathlib, collections
G = pathlib.Path(__file__).resolve().parent.parent.parent / 'data/gold_ner'
PAT = {'HASH': re.compile(r'\b[a-fA-F0-9]{32,64}\b'), 'IP': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), 'CVE': re.compile(r'\bCVE-\d{4}-\d{4,}\b', re.I),
       'EMAIL': re.compile(r'\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b'), 'URL': re.compile(r'\bhttps?://[^\s<>"]+', re.I), 'DOMAIN': re.compile(r'\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|ru|cn|info|biz|onion|top|xyz|co|uk|de|su)\b', re.I)}
out = {}
for ds in ['aptner', 'cyner', 'annoctr']:
    orig = {json.loads(l)['id']: json.loads(l)['text'] for l in open(G / f'{ds}_test.jsonl')}
    for v in ['bt-ru', 'bt-de', 'bt-zh', 'bt-es']:
        c = collections.defaultdict(lambda: [0, 0, 0])  # orig hits, bt hits, bt hits not in orig (corrupted/hallucinated)
        for l in open(G / f'{ds}__{v}_test.jsonl'):
            r = json.loads(l); o = orig[r['orig_id']]
            for t, p in PAT.items():
                oh = {m.lower() for m in p.findall(o)}; bh = [m.lower() for m in p.findall(r['text'])]
                c[t][0] += len(oh); c[t][1] += len(bh); c[t][2] += sum(1 for m in bh if m not in oh)
        out[f'{ds}__{v}'] = {t: {'orig_hits': a, 'bt_hits': b, 'bt_hits_not_in_orig': x, 'corrupted_share_of_bt_hits': round(x / b, 3) if b else None} for t, (a, b, x) in c.items()}
json.dump(out, open(G / 'ioc_corruption.json', 'w'), indent=1)
for k, v in out.items():
    print(k, ' '.join(f"{t}:{d['bt_hits_not_in_orig']}/{d['bt_hits']}(orig {d['orig_hits']})" for t, d in v.items() if d['orig_hits']))
