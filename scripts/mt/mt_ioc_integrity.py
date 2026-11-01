#!/usr/bin/env python3
"""E8: Do open NMT models preserve indicators of compromise? Multi-model, per-pass, with and without IOC masking.

Input: sentences from the APTNER, CyNER and AnnoCTR test splits that contain at least one regex IOC (hash / IPv4 / CVE / e-mail / URL / domain).
For each MT system and target language X we translate EN->X and X->EN and measure, per IOC type:
  after EN->X : share of original IOC strings present verbatim in the X text ("survive_fwd"), and regex hits in the X text not in the original ("corrupt_fwd")
  after X->EN : same on the round-tripped English ("survive_rt", "corrupt_rt")
Systems: MarianMT opus-mt (the thesis pipeline's primary), NLLB-200 distilled-600M (the thesis fallback), NLLB-200 1.3B, NLLB-200 3.3B, M2M100-418M;
decoding greedy (num_beams=1, as deployed) and beam 4 for Marian and NLLB-600M.
Mitigation: mask IOCs with placeholders (IOC0, IOC1, ...) before EN->X, translate, restore after X->EN; measure recovery.
Also records the character edit distance between each corrupted hash and its nearest original hash (to show they are near-misses).

Usage: python mt_ioc_integrity.py --langs ru,de --out runs/E8_mt_ioc [--max-sents 400]
"""
import argparse, json, pathlib, re, time, collections, sys
import torch
EXP = pathlib.Path(__file__).resolve().parent.parent.parent; GOLD = EXP / 'data/gold_ner'
PAT = {'HASH': re.compile(r'\b[a-fA-F0-9]{32}\b|\b[a-fA-F0-9]{40}\b|\b[a-fA-F0-9]{64}\b'), 'IP': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), 'CVE': re.compile(r'\bCVE-\d{4}-\d{4,}\b', re.I),
       'EMAIL': re.compile(r'\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b'), 'URL': re.compile(r'\bhttps?://[^\s<>"\)]+', re.I),
       'DOMAIN': re.compile(r'\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|ru|cn|info|biz|onion|top|xyz|co|uk|de|su|edu|gov)\b', re.I)}
NLLB_CODE = {'ru': 'rus_Cyrl', 'de': 'deu_Latn', 'zh': 'zho_Hans', 'es': 'spa_Latn'}
M2M_CODE = {'ru': 'ru', 'de': 'de', 'zh': 'zh', 'es': 'es'}

def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1): cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

class Marian:
    name = 'opus-mt'
    def __init__(self, lang):
        from transformers import MarianMTModel, MarianTokenizer
        self.t1 = MarianTokenizer.from_pretrained(f'Helsinki-NLP/opus-mt-en-{lang}'); self.m1 = MarianMTModel.from_pretrained(f'Helsinki-NLP/opus-mt-en-{lang}').cuda().eval()
        self.t2 = MarianTokenizer.from_pretrained(f'Helsinki-NLP/opus-mt-{lang}-en'); self.m2 = MarianMTModel.from_pretrained(f'Helsinki-NLP/opus-mt-{lang}-en').cuda().eval()
    def _tr(self, tok, model, texts, beams, bs=32):
        out = []
        for i in range(0, len(texts), bs):
            enc = tok(texts[i:i + bs], return_tensors='pt', padding=True, truncation=True, max_length=512).to('cuda')
            with torch.no_grad(): gen = model.generate(**enc, num_beams=beams, max_new_tokens=512)
            out.extend(tok.batch_decode(gen, skip_special_tokens=True))
        return out
    def fwd(self, texts, beams): return self._tr(self.t1, self.m1, texts, beams)
    def back(self, texts, beams): return self._tr(self.t2, self.m2, texts, beams)

class Seq2SeqMultilingual:
    def __init__(self, model_id, lang, kind):
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        self.name = model_id.split('/')[-1]; self.kind = kind; self.lang = lang
        self.tok = AutoTokenizer.from_pretrained(model_id); self.model = AutoModelForSeq2SeqLM.from_pretrained(model_id, dtype=torch.bfloat16).cuda().eval()
    def _tr(self, texts, src, tgt, beams, bs=16):
        out = []
        if self.kind == 'nllb': self.tok.src_lang = src; forced = self.tok.convert_tokens_to_ids(tgt)
        else: self.tok.src_lang = src; forced = self.tok.get_lang_id(tgt)
        for i in range(0, len(texts), bs):
            enc = self.tok(texts[i:i + bs], return_tensors='pt', padding=True, truncation=True, max_length=512).to('cuda')
            with torch.no_grad(): gen = self.model.generate(**enc, forced_bos_token_id=forced, num_beams=beams, max_new_tokens=512)
            out.extend(self.tok.batch_decode(gen, skip_special_tokens=True))
        return out
    def fwd(self, texts, beams):
        return self._tr(texts, 'eng_Latn' if self.kind == 'nllb' else 'en', NLLB_CODE[self.lang] if self.kind == 'nllb' else M2M_CODE[self.lang], beams)
    def back(self, texts, beams):
        return self._tr(texts, NLLB_CODE[self.lang] if self.kind == 'nllb' else M2M_CODE[self.lang], 'eng_Latn' if self.kind == 'nllb' else 'en', beams)

def iocs(text):
    found = {}
    for t, p in PAT.items():
        hits = [m.group() for m in p.finditer(text)]
        if t == 'DOMAIN':  # do not double count domains inside URLs/emails
            urls = ' '.join(found.get('URL', []) + found.get('EMAIL', [])).lower(); hits = [h for h in hits if h.lower() not in urls]
        found[t] = hits
    return found

def mask(text):
    """replace every IOC with a placeholder token; returns masked text and mapping"""
    spans = []
    for t, p in PAT.items():
        for m in p.finditer(text): spans.append((m.start(), m.end(), m.group()))
    spans.sort(); merged = []
    for s in spans:
        if merged and s[0] < merged[-1][1]: continue
        merged.append(s)
    out = []; last = 0; mapping = {}
    for i, (a, b, v) in enumerate(merged):
        ph = f'IOC{i}'; mapping[ph] = v; out.append(text[last:a]); out.append(ph); last = b
    out.append(text[last:]); return ''.join(out), mapping

def unmask(text, mapping):
    n_found = 0
    for ph, v in mapping.items():
        if re.search(re.escape(ph) + r'(?![0-9])', text, re.I): n_found += 1; text = re.sub(re.escape(ph) + r'(?![0-9])', lambda m: v, text, flags=re.I)
    return text, n_found

def measure(originals, outputs):
    c = collections.defaultdict(lambda: [0, 0, 0, 0]); ed = []
    for o, x in zip(originals, outputs):
        oi = iocs(o); xi = iocs(x); xl = x.lower()
        for t in PAT:
            oset = {v.lower() for v in oi[t]}; c[t][0] += len(oset); c[t][1] += sum(1 for v in oset if v in xl)
            xs = [v.lower() for v in xi[t]]; c[t][2] += len(xs); bad = [v for v in xs if v not in oset]; c[t][3] += len(bad)
            if t == 'HASH':
                for v in bad:
                    if oset: ed.append(min(edit_distance(v, u) for u in oset))
    res = {t: {'orig': a, 'survive': b, 'survive_pct': round(100 * b / a, 1) if a else None, 'hits_out': h, 'hits_not_in_orig': x, 'corrupt_share_pct': round(100 * x / h, 1) if h else None} for t, (a, b, h, x) in c.items()}
    if ed: res['HASH']['edit_distance_of_corrupted'] = {'n': len(ed), 'median': sorted(ed)[len(ed) // 2], 'le3_share': round(sum(1 for e in ed if e <= 3) / len(ed), 3)}
    return res

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--langs', default='ru,de'); ap.add_argument('--out', required=True); ap.add_argument('--max-sents', type=int, default=None)
    ap.add_argument('--systems', default='opus-mt,nllb-600M,nllb-1.3B,nllb-3.3B,m2m100'); a = ap.parse_args(); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    sents = []
    for ds in ['aptner', 'cyner', 'annoctr']:
        for l in open(GOLD / f'{ds}_test.jsonl'):
            r = json.loads(l); f = iocs(r['text'])
            if any(f[t] for t in f) and len(r['text']) < 1500: sents.append(r['text'])
    if a.max_sents: sents = sents[:a.max_sents]
    orig_counts = {t: sum(len({v.lower() for v in iocs(s)[t]}) for s in sents) for t in PAT}
    results = {'n_sentences': len(sents), 'orig_ioc_counts': orig_counts, 'runs': []}; print('sentences with IOCs:', len(sents), orig_counts, flush=True)
    SYS = {'opus-mt': lambda lg: Marian(lg), 'nllb-600M': lambda lg: Seq2SeqMultilingual('facebook/nllb-200-distilled-600M', lg, 'nllb'), 'nllb-1.3B': lambda lg: Seq2SeqMultilingual('facebook/nllb-200-1.3B', lg, 'nllb'),
           'nllb-3.3B': lambda lg: Seq2SeqMultilingual('facebook/nllb-200-3.3B', lg, 'nllb'), 'm2m100': lambda lg: Seq2SeqMultilingual('facebook/m2m100_418M', lg, 'm2m')}
    for sysname in a.systems.split(','):
        for lg in a.langs.split(','):
            t0 = time.time(); mt = SYS[sysname](lg)
            for beams in ([1, 4] if sysname in ('opus-mt', 'nllb-600M') else [1]):
                fwd = mt.fwd(sents, beams); rt = mt.back(fwd, beams)
                r = {'system': sysname, 'lang': lg, 'beams': beams, 'masked': False, 'after_en_to_x': measure(sents, fwd), 'after_round_trip': measure(sents, rt), 'seconds': round(time.time() - t0, 1)}
                results['runs'].append(r); h = r['after_round_trip']['HASH']; hf = r['after_en_to_x']['HASH']
                print(f"{sysname:10s} {lg} beams={beams}  HASH survive fwd {hf['survive_pct']}% rt {h['survive_pct']}% | corrupt share rt {h['corrupt_share_pct']}% | IP rt {r['after_round_trip']['IP']['survive_pct']}% | URL rt {r['after_round_trip']['URL']['survive_pct']}%", flush=True)
                if beams == 1:  # mitigation: mask -> translate -> unmask
                    masked = [mask(s) for s in sents]; fwd_m = mt.fwd([m for m, _ in masked], 1); rt_m = mt.back(fwd_m, 1)
                    restored = []; ph_total = ph_found = 0
                    for (m, mp), x in zip(masked, rt_m):
                        y, nf = unmask(x, mp); restored.append(y); ph_total += len(mp); ph_found += nf
                    rm = {'system': sysname, 'lang': lg, 'beams': 1, 'masked': True, 'placeholders': ph_total, 'placeholders_recovered': ph_found,
                          'placeholder_recovery_pct': round(100 * ph_found / max(ph_total, 1), 1), 'after_round_trip': measure(sents, restored), 'seconds': round(time.time() - t0, 1)}
                    results['runs'].append(rm); print(f"{sysname:10s} {lg} MASKED  placeholders recovered {rm['placeholder_recovery_pct']}% | HASH survive rt {rm['after_round_trip']['HASH']['survive_pct']}% corrupt {rm['after_round_trip']['HASH']['corrupt_share_pct']}%", flush=True)
                    with open(out / f'samples_{sysname}_{lg}.jsonl', 'w') as f:
                        for s, x, y, z in list(zip(sents, fwd, rt, restored))[:40]: f.write(json.dumps({'orig': s, 'fwd': x, 'rt': y, 'rt_masked': z}, ensure_ascii=False) + '\n')
            del mt; torch.cuda.empty_cache()
            json.dump(results, open(out / 'mt_ioc_integrity.json', 'w'), indent=1)
    json.dump(results, open(out / 'mt_ioc_integrity.json', 'w'), indent=1); print('done')

if __name__ == '__main__': main()
