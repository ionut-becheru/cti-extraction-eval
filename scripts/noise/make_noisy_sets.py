#!/usr/bin/env python3
"""Create noisy variants of gold test sets (coarse schema) and project gold spans onto them.

Variants (each written as experiments/data/gold_ner/<ds>__<variant>_test.jsonl):
  bt-<lang>   : EN -> <lang> -> EN round trip with MarianMT (Helsinki-NLP/opus-mt-en-<l>, opus-mt-<l>-en), greedy decoding
                (num_beams=1 as in the thesis config). Gold spans are projected by exact case-insensitive string match of the
                mention in the back-translated text; mentions that do not survive verbatim are recorded in `dropped_gold`.
  defang      : IOC defanging as seen in CTI reports/forums: http->hxxp, '.'->'[.]' in IPs/domains, '@'->'[at]' in emails.
  boiler      : forum/UI boilerplate injected before and after the sentence (thesis SPAM/UI list strings + typical forum chrome).
  lower       : lower-cased text.
  typo        : 5% of alphabetic tokens (len>=4, outside gold spans) get one adjacent-character swap (seed 0).
Gold projection for non-BT variants is exact, so `dropped_gold` is empty there (defang changes mention strings: projection uses the
defanged mention, so nothing is dropped either).

Usage: python make_noisy_sets.py --datasets aptner,cyner,annoctr --variants bt-ru,bt-de,bt-zh,bt-es,defang,boiler,lower,typo
"""
import argparse, json, pathlib, random, re, sys, time
HERE = pathlib.Path(__file__).resolve().parent; EXP = HERE.parent.parent; GOLD = EXP / 'data/gold_ner'
sys.path.insert(0, str(EXP / 'scripts/gold_ner')); from ner_metrics import spans
BOILER_PRE = ['Home > Forums > Exploits & Vulnerabilities > Thread', 'Reply #3 by user0x1f | Joined: Mar 2021 | Posts: 412', '[quote] Originally posted by root_kit:',
              'Click to expand... Show more', 'Previous page | Next page', 'Sponsored: buy now, limited offer, free trial']
BOILER_POST = ['-- Sent from my Tor browser. All rights reserved.', 'Reply | Quote | Report | Load more comments', 'Terms of service | Privacy policy | Cookie policy',
               'Go back to thread list. Home page.', '[/quote] +1 rep, thanks bro', 'Views: 1,337 | Likes: 42 | Share']

def tokenize(text):
    toks = []; offs = []
    for m in re.finditer(r'\S+', text): toks.append(m.group()); offs.append([m.start(), m.end()])
    return toks, offs

def project(row, new_text, transform=lambda s: s):
    toks, offs = tokenize(new_text); tags = ['O'] * len(toks); low = new_text.lower(); dropped = []; used = [False] * len(new_text)
    for s, e, t in sorted(spans(row['coarse']), key=lambda x: -(x[1] - x[0])):
        if t == 'UNCOVERED': continue
        mention = transform(' '.join(row['tokens'][s:e])).lower(); hit = None
        for m in re.finditer(re.escape(mention), low):
            if not any(used[m.start():m.end()]): hit = m; break
        if hit is None: dropped.append({'text': mention, 'type': t}); continue
        for i in range(hit.start(), hit.end()): used[i] = True
        idx = [i for i, (a, b) in enumerate(offs) if b > hit.start() and a < hit.end()]
        if not idx or any(tags[i] != 'O' for i in idx): dropped.append({'text': mention, 'type': t}); continue
        tags[idx[0]] = 'B-' + t
        for i in idx[1:]: tags[i] = 'I-' + t
    return toks, offs, tags, dropped

def defang(text):
    text = re.sub(r'\bhttps?://', lambda m: m.group().replace('http', 'hxxp').replace('HTTP', 'HXXP'), text)
    text = re.sub(r'\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b', r'\1[.]\2[.]\3[.]\4', text)
    text = re.sub(r'\b([a-z0-9-]+)\.(com|net|org|io|ru|cn|info|biz|onion|top|xyz|co|uk|de|su)\b', r'\1[.]\2', text, flags=re.I)
    text = re.sub(r'([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})', r'\1[at]\2', text)
    return text

def typo(row, rng, rate=0.05):
    inside = set()
    for s, e, t in spans(row['coarse']):
        if t != 'UNCOVERED': inside.update(range(s, e))
    toks = list(row['tokens'])
    for i, tk in enumerate(toks):
        if i in inside or len(tk) < 4 or not tk.isalpha() or rng.random() > rate: continue
        j = rng.randrange(len(tk) - 1); toks[i] = tk[:j] + tk[j + 1] + tk[j] + tk[j + 2:]
    return ' '.join(toks)

class BT:
    def __init__(self, lang):
        import torch; from transformers import MarianMTModel, MarianTokenizer
        self.torch = torch
        self.t1 = MarianTokenizer.from_pretrained(f'Helsinki-NLP/opus-mt-en-{lang}'); self.m1 = MarianMTModel.from_pretrained(f'Helsinki-NLP/opus-mt-en-{lang}').cuda().eval()
        self.t2 = MarianTokenizer.from_pretrained(f'Helsinki-NLP/opus-mt-{lang}-en'); self.m2 = MarianMTModel.from_pretrained(f'Helsinki-NLP/opus-mt-{lang}-en').cuda().eval()
    def _tr(self, tok, model, texts, bs=32):
        out = []
        for i in range(0, len(texts), bs):
            enc = tok(texts[i:i + bs], return_tensors='pt', padding=True, truncation=True, max_length=512).to('cuda')
            with self.torch.no_grad():
                gen = model.generate(**enc, num_beams=1, max_new_tokens=512)
            out.extend(tok.batch_decode(gen, skip_special_tokens=True))
        return out
    def __call__(self, texts): return self._tr(self.t2, self.m2, self._tr(self.t1, self.m1, texts))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--datasets', default='aptner,cyner,annoctr'); ap.add_argument('--variants', default='bt-ru,bt-de,bt-zh,bt-es,defang,boiler,lower,typo')
    ap.add_argument('--max-sents', type=int, default=None); a = ap.parse_args(); rng = random.Random(0); stats = {}
    for var in a.variants.split(','):
        bt = BT(var.split('-')[1]) if var.startswith('bt-') else None
        for ds in a.datasets.split(','):
            rows = [json.loads(l) for l in open(GOLD / f'{ds}_test.jsonl')]
            if a.max_sents: rows = rows[:a.max_sents]
            t0 = time.time(); tf = (lambda s: s)
            if bt: new_texts = bt([r['text'] for r in rows])
            elif var == 'defang': new_texts = [defang(r['text']) for r in rows]; tf = defang
            elif var == 'boiler': new_texts = [f"{rng.choice(BOILER_PRE)} {r['text']} {rng.choice(BOILER_POST)}" for r in rows]
            elif var == 'lower': new_texts = [r['text'].lower() for r in rows]
            elif var == 'typo': new_texts = [typo(r, rng) for r in rows]
            else: raise SystemExit(var)
            n_gold = n_drop = 0; out = GOLD / f'{ds}__{var}_test.jsonl'
            with open(out, 'w') as f:
                for r, nt in zip(rows, new_texts):
                    toks, offs, tags, dropped = project(r, nt, tf)
                    n_gold += sum(1 for t in r['coarse'] if t.startswith('B-') and not t.endswith('UNCOVERED')); n_drop += len(dropped)
                    f.write(json.dumps({'id': r['id'] + f'__{var}', 'dataset': ds, 'split': 'test', 'variant': var, 'tokens': toks, 'offsets': offs, 'text': nt,
                                        'coarse': tags, 'fine': tags, 'dropped_gold': dropped, 'orig_id': r['id']}, ensure_ascii=False) + '\n')
            stats[f'{ds}__{var}'] = {'sentences': len(rows), 'gold_mentions': n_gold, 'dropped_gold': n_drop, 'dropped_pct': round(100 * n_drop / max(n_gold, 1), 1), 'seconds': round(time.time() - t0, 1)}
            print(ds, var, stats[f'{ds}__{var}'], flush=True)
        del bt
    prev = json.load(open(GOLD / 'noise_stats.json')) if (GOLD / 'noise_stats.json').exists() else {}
    prev.update(stats); json.dump(prev, open(GOLD / 'noise_stats.json', 'w'), indent=1)

if __name__ == '__main__': main()
