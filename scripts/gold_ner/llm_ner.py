#!/usr/bin/env python3
"""Local instruction-LLM entity extraction on gold test sets (coarse schema), zero-shot or few-shot.

The model is asked for a JSON list of {"text": ..., "type": ...} mentions restricted to the types the corpus annotates.
Predicted strings are aligned to token spans by exact (case-insensitive) substring match on the sentence text (all
non-overlapping occurrences); unalignable predictions are counted and dropped. Scored strict + relaxed with CIs.

Usage: python llm_ner.py --model Qwen/Qwen3-8B --datasets aptner,dnrti,cyner,annoctr,attacker --shots 0 --out runs/E4_llm/qwen3_8b_0shot [--max-test 600]
"""
import argparse, json, pathlib, time, sys, re, random, collections
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
HERE = pathlib.Path(__file__).resolve().parent; EXP = HERE.parent.parent; GOLD = EXP / 'data/gold_ner'
sys.path.insert(0, str(HERE)); from ner_metrics import score_bio, spans
DESC = {'THREAT_ACTOR': 'threat actor / APT group / hacker group name', 'MALWARE': 'malware family or malicious program name', 'TOOL': 'legitimate or offensive software tool name',
        'MALWARE_TOOL': 'malware family or software tool name', 'VULNERABILITY': 'vulnerability identifier (e.g. CVE-2017-0199) or named vulnerability',
        'IP': 'IP address', 'HASH': 'file hash (MD5/SHA1/SHA256)', 'DOMAIN': 'domain name', 'URL': 'URL', 'EMAIL': 'email address', 'FILE': 'file name or file path',
        'LOCATION': 'country, region or city', 'INDICATOR': 'indicator of compromise: IP address, domain, URL, file hash, email address, file name or path'}

def base(ds): return ds.split('__')[0]

def corpus_types(ds):
    ds = base(ds); train = [json.loads(l) for l in open(GOLD / f'{ds}_train.jsonl')]
    return sorted({t[2:] for r in train for t in r['coarse'] if t != 'O' and not t.endswith('UNCOVERED')})

def examples(ds, k, seed=0):
    ds = base(ds); dev = [json.loads(l) for l in open(GOLD / f'{ds}_dev.jsonl')]
    dev = [r for r in dev if any(t.startswith('B-') and not t.endswith('UNCOVERED') for t in r['coarse'])]
    rng = random.Random(seed); rng.shuffle(dev); out = []
    for r in dev[:k]:
        ents = [{'text': ' '.join(r['tokens'][s:e]), 'type': t} for s, e, t in spans(r['coarse']) if t != 'UNCOVERED']
        out.append((r['text'], json.dumps(ents, ensure_ascii=False)))
    return out

def build_prompt(text, types, shots):
    tl = '\n'.join(f'- {t}: {DESC[t]}' for t in types)
    sys_msg = ('You are a cyber threat intelligence annotator. Extract every entity mention of the listed types from the sentence. '
               'Copy mention text exactly as it appears. Output ONLY a JSON array of objects {"text": ..., "type": ...}; output [] if none.\n'
               f'Types:\n{tl}')
    msgs = [{'role': 'system', 'content': sys_msg}]
    for x, y in shots: msgs += [{'role': 'user', 'content': f'Sentence: {x}'}, {'role': 'assistant', 'content': y}]
    msgs.append({'role': 'user', 'content': f'Sentence: {text}'}); return msgs

def parse(out):
    m = re.search(r'\[.*\]', out, re.S)
    if not m: return None
    try: arr = json.loads(m.group(0))
    except Exception:
        try: arr = json.loads(m.group(0).replace("'", '"'))
        except Exception: return None
    return [x for x in arr if isinstance(x, dict) and isinstance(x.get('text'), str) and isinstance(x.get('type'), str)]

def align(row, ents, types):
    tags = ['O'] * len(row['tokens']); text_l = row['text'].lower(); offs = row['offsets']; unal = 0; n = 0
    for e in sorted(ents, key=lambda x: -len(x['text'])):
        typ = e['type'].strip().upper()
        if typ not in types or not e['text'].strip(): continue
        n += 1; hit = False
        for m in re.finditer(re.escape(e['text'].strip().lower()), text_l):
            idx = [i for i, (a, b) in enumerate(offs) if b > m.start() and a < m.end()]
            if not idx or any(tags[i] != 'O' for i in idx): continue
            tags[idx[0]] = 'B-' + typ
            for i in idx[1:]: tags[i] = 'I-' + typ
            hit = True
        if not hit: unal += 1
    return tags, n, unal

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--model', required=True); ap.add_argument('--datasets', default='aptner,dnrti,cyner,annoctr,attacker')
    ap.add_argument('--shots', type=int, default=0); ap.add_argument('--out', required=True); ap.add_argument('--max-test', type=int, default=None)
    ap.add_argument('--bs', type=int, default=16); ap.add_argument('--max-new', type=int, default=256); ap.add_argument('--boot', type=int, default=1000)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args(); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time(); torch.cuda.reset_peak_memory_stats()
    tok = AutoTokenizer.from_pretrained(a.model); tok.padding_side = 'left'
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, device_map='cuda'); model.eval()
    results = {'model': a.model, 'shots': a.shots, 'eval': {}}
    for ds in a.datasets.split(','):
        test = [json.loads(l) for l in open(GOLD / f'{ds}_test.jsonl')]
        if a.max_test and len(test) > a.max_test:
            random.Random(a.seed).shuffle(test); test = test[:a.max_test]
        types = corpus_types(ds); shots = examples(ds, a.shots, a.seed) if a.shots else []
        preds = []; raw_out = []; n_pred = 0; n_unal = 0; n_unparsed = 0; t1 = time.time()
        for i in range(0, len(test), a.bs):
            chunk = test[i:i + a.bs]
            prompts = [tok.apply_chat_template(build_prompt(r['text'], types, shots), tokenize=False, add_generation_prompt=True, enable_thinking=False)
                       if 'qwen3' in a.model.lower() else tok.apply_chat_template(build_prompt(r['text'], types, shots), tokenize=False, add_generation_prompt=True) for r in chunk]
            enc = tok(prompts, return_tensors='pt', padding=True, truncation=True, max_length=3072).to('cuda')
            with torch.no_grad():
                gen = model.generate(**enc, max_new_tokens=a.max_new, do_sample=False, pad_token_id=tok.pad_token_id)
            outs = tok.batch_decode(gen[:, enc['input_ids'].shape[1]:], skip_special_tokens=True)
            for r, o in zip(chunk, outs):
                ents = parse(o)
                if ents is None: n_unparsed += 1; ents = []
                tags, n, unal = align(r, ents, set(types)); n_pred += n; n_unal += unal; preds.append(tags)
                raw_out.append({'id': r['id'], 'raw': o[:1000], 'pred': tags})
            if (i // a.bs) % 10 == 0: print(f'  {ds} {i+len(chunk)}/{len(test)} {time.time()-t1:.0f}s', flush=True)
        sec = time.time() - t1
        gold = [['O' if t.endswith('UNCOVERED') else t for t in r['coarse']] for r in test]
        m = score_bio(gold, preds, boot=a.boot, seed=0)
        results['eval'][ds] = {'types': types, 'n_test': len(test), 'metrics': m, 'seconds': round(sec, 1), 'sent_per_s': round(len(test) / sec, 2),
                               'n_predicted_mentions': n_pred, 'n_unalignable': n_unal, 'n_unparsed_outputs': n_unparsed}
        with open(out / f'preds_{ds}.jsonl', 'w') as f:
            for x in raw_out: f.write(json.dumps(x, ensure_ascii=False) + '\n')
        print(f"{ds}: strict micro F1 {m['MICRO']['F1']:.4f} {m['MICRO']['ci95']['F1']} relaxed {m['MICRO']['F1_relaxed']:.4f} | unalignable {n_unal}/{n_pred} unparsed {n_unparsed} | {len(test)/sec:.2f} sent/s", flush=True)
        for t, v in m.items():
            if t != 'MICRO': print(f"   {t:14s} P={v['P']:.3f} R={v['R']:.3f} F1={v['F1']:.3f}")
    results['wall_seconds'] = round(time.time() - t0, 1); results['peak_vram_mib'] = int(torch.cuda.max_memory_allocated() / 2**20)
    json.dump(results, open(out / 'metrics.json', 'w'), indent=1)

if __name__ == '__main__': main()
