#!/usr/bin/env python3
"""Which placeholder style survives NMT? Mask IOCs with different placeholder patterns, round-trip through opus-mt (greedy), measure recovery."""
import json, pathlib, re, sys, collections, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from mt_ioc_integrity import Marian, Seq2SeqMultilingual, PAT, iocs, GOLD
STYLES = {'IOC{i}': lambda i: f'IOC{i}', 'XQZ{i}': lambda i: f'XQZ{i}', 'bracket[IOC{i}]': lambda i: f'[IOC{i}]', 'angle<ioc{i}>': lambda i: f'<ioc{i}>', 'hex-like': lambda i: f'0x{i:04d}', 'digits{i}': lambda i: f'{7000+i}', 'word ZORKA{i}': lambda i: f'ZORKA{i}', 'placeholder_{i}': lambda i: f'PLACEHOLDER_{i}'}

def mask(text, fn):
    spans = []
    for t, p in PAT.items():
        for m in p.finditer(text): spans.append((m.start(), m.end(), m.group()))
    spans.sort(); merged = []
    for s in spans:
        if merged and s[0] < merged[-1][1]: continue
        merged.append(s)
    out = []; last = 0; mapping = {}
    for i, (a, b, v) in enumerate(merged):
        ph = fn(i); mapping[ph] = v; out.append(text[last:a]); out.append(ph); last = b
    out.append(text[last:]); return ''.join(out), mapping

def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else 'ru'; system = sys.argv[2] if len(sys.argv) > 2 else 'opus-mt'
    sents = []
    for ds in ['aptner', 'cyner', 'annoctr']:
        for l in open(GOLD / f'{ds}_test.jsonl'):
            r = json.loads(l); f = iocs(r['text'])
            if any(f[t] for t in f) and len(r['text']) < 1500: sents.append(r['text'])
    mt = Marian(lang) if system == 'opus-mt' else Seq2SeqMultilingual('facebook/nllb-200-distilled-600M', lang, 'nllb')
    res = {}
    for name, fn in STYLES.items():
        masked = [mask(s, fn) for s in sents]; rt = mt.back(mt.fwd([m for m, _ in masked], 1), 1); tot = rec = 0
        for (m, mp), x in zip(masked, rt):
            for ph in mp: tot += 1; rec += bool(re.search(re.escape(ph) + r'(?![0-9])', x, re.I))
        res[name] = {'placeholders': tot, 'recovered': rec, 'pct': round(100 * rec / tot, 1)}; print(f'{system} {lang} {name:18s} recovered {rec}/{tot} = {100*rec/tot:.1f}%', flush=True)
    out = pathlib.Path(f'runs/E8_mt_ioc/placeholder_styles_{system}_{lang}.json'); json.dump(res, open(out, 'w'), indent=1)

if __name__ == '__main__': main()
