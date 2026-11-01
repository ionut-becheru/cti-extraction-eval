#!/usr/bin/env python3
"""Build hard-negative pools for the security-relevance filter from non-security StackExchange dumps (CC BY-SA 4.0).

Mirrors the thesis's StackExchange ingest (question title + body + tags + accepted answer, HTML stripped, >=200 chars,
<=5000 chars) but WITHOUT the cyber keyword gate and from sites whose topic is not security: superuser.com, serverfault.com.
Records are sampled uniformly at random (seed 0). Questions carrying any tag in the thesis security whitelist are excluded so
that the pool is "technical but not security" by construction; the residual overlap (a Super User question about passwords)
is exactly the realistic ambiguity we want to measure.

Usage: python build_hard_negatives.py --site superuser.com --n 3000 --out data/relevance/hard_neg_superuser.jsonl
"""
import argparse, json, pathlib, random, re, sys
from xml.etree.ElementTree import iterparse
EXP = pathlib.Path(__file__).resolve().parent.parent.parent; EXT = EXP / 'data/external'
sys.path.insert(0, str(EXP / 'baseline')); from scripts.ingest.stackexchange import TAG_WHITELIST, _strip_html, _parse_tags
from scripts.ingest.common import normalize_text, _truncate_at_sentence

def ensure_posts(site):
    arch = EXT / f'{site}.7z'; outdir = EXT / site; posts = outdir / 'Posts.xml'
    if posts.exists(): return posts
    import py7zr; outdir.mkdir(exist_ok=True)
    with py7zr.SevenZipFile(arch, 'r') as z: z.extract(path=outdir, targets=['Posts.xml'])
    return posts

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--site', required=True); ap.add_argument('--n', type=int, default=3000); ap.add_argument('--out', required=True)
    ap.add_argument('--seed', type=int, default=0); ap.add_argument('--reservoir', type=int, default=60000)
    a = ap.parse_args(); posts = ensure_posts(a.site); rng = random.Random(a.seed)
    questions = {}; pool = []; seen = 0; excluded_sec = 0
    for evt, el in iterparse(str(posts), events=('end',)):
        if el.tag != 'row': continue
        at = el.attrib; pt = at.get('PostTypeId')
        if pt == '1':
            tags = _parse_tags(at.get('Tags', '')); acc = int(at.get('AcceptedAnswerId', '0') or 0)
            if not acc: el.clear(); continue
            if set(tags) & TAG_WHITELIST: excluded_sec += 1; el.clear(); continue
            questions[int(at['Id'])] = (at.get('Title', ''), _strip_html(at.get('Body', '')), tags, acc, at.get('CreationDate', ''))
        elif pt == '2':
            parent = int(at.get('ParentId', '0') or 0); q = questions.get(parent)
            if q and q[3] == int(at['Id']):
                text = normalize_text(f"Question: {q[0]} Body: {q[1]} Tags: {', '.join(q[2])} Accepted Answer: {_strip_html(at.get('Body',''))}")
                del questions[parent]
                if len(text) >= 200:
                    text = _truncate_at_sentence(text, 5000); seen += 1
                    rec = {'text': text, 'site': a.site, 'url': f'https://{a.site}/q/{parent}', 'tags': q[2], 'date': q[4]}
                    if len(pool) < a.reservoir: pool.append(rec)
                    else:
                        j = rng.randrange(seen)
                        if j < a.reservoir: pool[j] = rec
        el.clear()
    rng.shuffle(pool); pool = pool[:a.n]
    out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w') as f:
        for r in pool: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(json.dumps({'site': a.site, 'eligible_qa_pairs': seen, 'excluded_security_tagged': excluded_sec, 'written': len(pool)}))

if __name__ == '__main__': main()
