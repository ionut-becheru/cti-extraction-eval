#!/usr/bin/env python3
"""Fine-tune a token-classification encoder on one gold corpus (fine or coarse schema) and evaluate on its test split
(and optionally on other corpora's test splits in the coarse schema).

Usage: python finetune_ner.py --model microsoft/deberta-v3-base --dataset aptner --schema coarse --seed 13 \
         --out runs/E2_ft/deberta_aptner_coarse_s13 [--eval-on aptner,dnrti,cyner,annoctr,attacker] [--epochs 5]
Writes: metrics.json (strict/relaxed P/R/F1 per type + micro, bootstrap CIs), preds_<ds>.jsonl (token-level predicted BIO),
run_meta.json (wall time, peak VRAM). Deterministic given seed (cudnn deterministic on).
"""
import argparse, json, pathlib, time, random, collections, os, sys
import numpy as np, torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer, AutoModelForTokenClassification, get_linear_schedule_with_warmup
HERE = pathlib.Path(__file__).resolve().parent; EXP = HERE.parent.parent; GOLD = EXP / 'data/gold_ner'
AMP = True  # set False for DeBERTa-v3 (NaN loss under bf16 autocast)
sys.path.insert(0, str(HERE)); from ner_metrics import score_bio  # shared scorer

def load(ds, split, schema):
    rows = [json.loads(l) for l in open(GOLD / f'{ds}_{split}.jsonl')]
    for r in rows:
        r['tags'] = r[schema]
        if schema == 'coarse': r['tags'] = ['O' if t.endswith('UNCOVERED') else t for t in r['tags']]
    return rows

def encode(rows, tok, label2id, max_len):
    out = []
    for r in rows:
        enc = tok(r['tokens'], is_split_into_words=True, truncation=True, max_length=max_len)
        wids = enc.word_ids(); labels = []; prev = None
        for w in wids:
            if w is None: labels.append(-100)
            elif w != prev: labels.append(label2id.get(r['tags'][w], label2id['O']))
            else: labels.append(-100)
            prev = w
        enc['labels'] = labels; enc['n_words'] = len(r['tokens']); out.append(dict(enc))
    return out

def collate(batch, pad_id):
    m = max(len(b['input_ids']) for b in batch)
    ids = torch.full((len(batch), m), pad_id); att = torch.zeros((len(batch), m), dtype=torch.long); lab = torch.full((len(batch), m), -100)
    for i, b in enumerate(batch):
        n = len(b['input_ids']); ids[i, :n] = torch.tensor(b['input_ids']); att[i, :n] = 1; lab[i, :n] = torch.tensor(b['labels'])
    return ids, att, lab

@torch.no_grad()
def predict(model, tok, rows, id2label, max_len, device, bs=32):
    model.eval(); preds = []
    for i in range(0, len(rows), bs):
        chunk = rows[i:i + bs]
        enc = tok([r['tokens'] for r in chunk], is_split_into_words=True, truncation=True, max_length=max_len, padding=True, return_tensors='pt')
        with torch.autocast('cuda', dtype=torch.bfloat16, enabled=AMP):
            logits = model(input_ids=enc['input_ids'].to(device), attention_mask=enc['attention_mask'].to(device)).logits
        am = logits.argmax(-1).cpu().numpy()
        for j, r in enumerate(chunk):
            wids = enc.word_ids(j); tags = ['O'] * len(r['tokens']); prev = None
            for k, w in enumerate(wids):
                if w is not None and w != prev: tags[w] = id2label[int(am[j, k])]
                prev = w
            # repair: I-X after O -> B-X
            fixed = []; p = 'O'
            for t in tags:
                if t.startswith('I-') and (p == 'O' or p[2:] != t[2:]): t = 'B-' + t[2:]
                fixed.append(t); p = t
            preds.append(fixed)
    return preds

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True); ap.add_argument('--dataset', required=True); ap.add_argument('--schema', default='coarse', choices=['fine', 'coarse'])
    ap.add_argument('--seed', type=int, default=13); ap.add_argument('--out', required=True); ap.add_argument('--epochs', type=int, default=5)
    ap.add_argument('--lr', type=float, default=3e-5); ap.add_argument('--bs', type=int, default=16); ap.add_argument('--max-len', type=int, default=256)
    ap.add_argument('--eval-on', default=None, help='comma list of datasets to also evaluate on (coarse schema only)')
    ap.add_argument('--boot', type=int, default=1000)
    a = ap.parse_args(); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    global AMP; AMP = 'deberta' not in a.model.lower(); print('autocast bf16:', AMP, flush=True)
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed); torch.cuda.manual_seed_all(a.seed)
    torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False
    device = 'cuda'; t0 = time.time(); torch.cuda.reset_peak_memory_stats()
    train = load(a.dataset, 'train', a.schema); dev = load(a.dataset, 'dev', a.schema); test = load(a.dataset, 'test', a.schema)
    labels = sorted({t for r in train + dev for t in r['tags']}, key=lambda x: (x != 'O', x)); label2id = {l: i for i, l in enumerate(labels)}; id2label = {i: l for l, i in label2id.items()}
    tok = AutoTokenizer.from_pretrained(a.model, add_prefix_space=True) if 'roberta' in a.model.lower() else AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForTokenClassification.from_pretrained(a.model, num_labels=len(labels), id2label=id2label, label2id=label2id, dtype=torch.float32).to(device)  # transformers 5 otherwise keeps the checkpoint dtype (fp16 for deberta-v3) -> NaN training
    tr = encode(train, tok, label2id, a.max_len); pad = tok.pad_token_id
    dl = DataLoader(tr, batch_size=a.bs, shuffle=True, collate_fn=lambda b: collate(b, pad), generator=torch.Generator().manual_seed(a.seed))
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01); steps = len(dl) * a.epochs
    sch = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    best = -1; best_state = None; hist = []
    for ep in range(a.epochs):
        model.train(); tot = 0
        for ids, att, lab in dl:
            with torch.autocast('cuda', dtype=torch.bfloat16, enabled=AMP):
                loss = model(input_ids=ids.to(device), attention_mask=att.to(device), labels=lab.to(device)).loss
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sch.step(); opt.zero_grad(); tot += loss.item()
        dp = predict(model, tok, dev, id2label, a.max_len, device); dm = score_bio([r['tags'] for r in dev], dp, boot=0)
        f1 = dm['MICRO']['F1']; hist.append({'epoch': ep + 1, 'train_loss': tot / len(dl), 'dev_micro_f1': f1}); print(f'epoch {ep+1} loss {tot/len(dl):.4f} dev F1 {f1:.4f}', flush=True)
        if f1 > best: best = f1; best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    results = {'model': a.model, 'dataset': a.dataset, 'schema': a.schema, 'seed': a.seed, 'labels': labels, 'history': hist, 'best_dev_micro_f1': best, 'eval': {}}
    evals = [a.dataset] + [d for d in (a.eval_on.split(',') if a.eval_on else []) if d != a.dataset]
    for ds in evals:
        if ds != a.dataset and a.schema != 'coarse': continue
        te = load(ds, 'test', a.schema); tp = predict(model, tok, te, id2label, a.max_len, device)
        # cross-corpus: score only on types the source corpus can emit AND the target annotates; handled inside score_bio via 'restrict'
        m = score_bio([r['tags'] for r in te], tp, boot=a.boot, seed=0); results['eval'][ds] = m
        if ds != a.dataset:
            src_types = {l[2:] for l in labels if l != 'O'}; tgt_types = {t[2:] for r in te for t in r['tags'] if t != 'O'}
            shared = sorted(src_types & tgt_types)
            results.setdefault('eval_shared_types', {})[ds] = {'shared_types': shared,
                'metrics': score_bio([r['tags'] for r in te], tp, boot=a.boot, seed=0, restrict_types=shared) if shared else None}
        with open(out / f'preds_{ds}.jsonl', 'w') as f:
            for r, p in zip(te, tp): f.write(json.dumps({'id': r['id'], 'pred': p}) + '\n')
        print(f'[{a.dataset}->{ds}] strict micro F1 {m["MICRO"]["F1"]:.4f} {m["MICRO"].get("ci95",{}).get("F1")} relaxed {m["MICRO"]["F1_relaxed"]:.4f}', flush=True)
    results['wall_seconds'] = round(time.time() - t0, 1); results['peak_vram_mib'] = int(torch.cuda.max_memory_allocated() / 2**20)
    results['n_train'] = len(train); results['n_dev'] = len(dev); results['n_test'] = len(test)
    json.dump(results, open(out / 'metrics.json', 'w'), indent=1)
    if os.environ.get('SAVE_MODEL'): model.save_pretrained(out / 'model'); tok.save_pretrained(out / 'model')

if __name__ == '__main__': main()
