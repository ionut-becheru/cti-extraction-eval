"""Export the relevance-filter positives (3,000 corpus records, reservoir sample with seed 42, as in the thesis)
to data/relevance/positives.jsonl. Text is included only for sources whose licence allows redistribution
(NVD and CISA KEV: public domain; MITRE ATT&CK: ATT&CK terms of use; Security StackExchange: CC BY-SA 4.0, url kept;
CyNER: MIT). For APTNER and DNRTI records only the index and source are kept; rebuild the corpus with
baseline/scripts/ingest and pass --with-text to restore them locally.
Usage: python scripts/relevance/export_positives.py --corpus <public_cyber_corpus.json> [--with-text]"""
import argparse, json, pathlib, random, ijson
EXP = pathlib.Path(__file__).resolve().parent.parent.parent
LICENSED = {'nvd', 'cisa_kev', 'mitre_attack', 'stackexchange_security', 'cyner'}
def positives(path, n=3000, seed=42):
    rng = random.Random(seed); out = []; i = 0
    with open(path, 'rb') as f:
        for rec in ijson.items(f, 'item'):
            i += 1; t = rec.get('raw_text') or ''
            if not t: continue
            item = {'idx': i - 1, 'src': rec.get('source_forum', '?'), 'url': rec.get('url'), 'text': t}
            if len(out) < n: out.append(item)
            else:
                j = rng.randrange(i)
                if j < n: out[j] = item
    return out
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--corpus', required=True); ap.add_argument('--with-text', action='store_true')
    ap.add_argument('--out', default=str(EXP / 'data/relevance/positives.jsonl')); a = ap.parse_args()
    P = positives(a.corpus)
    with open(a.out, 'w') as fo:
        for r in P:
            if not a.with_text and r['src'] not in LICENSED: r['text'] = None
            fo.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('wrote', len(P), 'positives to', a.out, '| with text:', sum(1 for r in P if r['text']))
