#!/usr/bin/env python3
"""Load APTNER / DNRTI / CyNER CoNLL files with ORIGINAL splits, harmonise labels, write JSONL.

Output: experiments/data/gold_ner/<dataset>_<split>.jsonl, one sentence per line:
  {"id", "dataset", "split", "tokens": [...], "fine": [BIO fine tags], "coarse": [BIO coarse tags], "text", "offsets": [[s,e],...]}
`text` is tokens joined by single spaces; `offsets` are char spans of each token in `text`.
Also writes label_map.json (fine -> coarse) and stats.json. Deterministic.

Coarse schema (what the thesis dictionary/regex NER can in principle emit):
  THREAT_ACTOR, MALWARE, TOOL, MALWARE_TOOL(DNRTI only: label mixes both), VULNERABILITY, IP, HASH, DOMAIN, URL,
  EMAIL, FILE, LOCATION, INDICATOR(CyNER only: IP/hash/domain/url/email/file mixed), UNCOVERED (gold types the thesis
  schema has no counterpart for: time, organisation, industry, security team, OS, protocol, encryption, action, purpose, ...).
"""
import json, pathlib, collections, re
EXP = pathlib.Path(__file__).resolve().parent.parent.parent; ROOT = EXP; CACHE = EXP / 'data/external/cache'; OUT = EXP / 'data/gold_ner'
FILES = {
 'aptner': {'train': CACHE / 'aptner/APTNERtrain.txt', 'dev': CACHE / 'aptner/APTNERdev.txt', 'test': CACHE / 'aptner/APTNERtest.txt'},
 'dnrti':  {'train': CACHE / 'dnrti/DNRTI/train.txt', 'dev': CACHE / 'dnrti/DNRTI/valid.txt', 'test': CACHE / 'dnrti/DNRTI/test.txt'},
 'cyner':  {'train': CACHE / 'cyner/dataset/mitre/train.txt', 'dev': CACHE / 'cyner/dataset/mitre/valid.txt', 'test': CACHE / 'cyner/dataset/mitre/test.txt'},
}
FINE2COARSE = {
 # APTNER (Wang et al. 2022): APT SECTEAM IDTY OS EMAIL LOC TIME IP DOM URL PROT FILE TOOL MD5 SHA1 SHA2 MAL ENCR VULNAME VULID ACT
 'aptner': {'APT': 'THREAT_ACTOR', 'MAL': 'MALWARE', 'TOOL': 'TOOL', 'VULID': 'VULNERABILITY', 'VULNAME': 'VULNERABILITY', 'IP': 'IP',
            'MD5': 'HASH', 'SHA1': 'HASH', 'SHA2': 'HASH', 'DOM': 'DOMAIN', 'URL': 'URL', 'EMAIL': 'EMAIL', 'FILE': 'FILE', 'LOC': 'LOCATION',
            'SECTEAM': 'UNCOVERED', 'IDTY': 'UNCOVERED', 'OS': 'UNCOVERED', 'TIME': 'UNCOVERED', 'PROT': 'UNCOVERED', 'ENCR': 'UNCOVERED', 'ACT': 'UNCOVERED'},
 # DNRTI (Wang et al. 2020): HackOrg OffAct SamFile SecTeam Tool Time Purp Area Idus Org Way Exp Features
 'dnrti':  {'HackOrg': 'THREAT_ACTOR', 'Tool': 'MALWARE_TOOL', 'Exp': 'VULNERABILITY', 'SamFile': 'FILE', 'Area': 'LOCATION',
            'OffAct': 'UNCOVERED', 'SecTeam': 'UNCOVERED', 'Time': 'UNCOVERED', 'Purp': 'UNCOVERED', 'Idus': 'UNCOVERED', 'Org': 'UNCOVERED',
            'Way': 'UNCOVERED', 'Features': 'UNCOVERED'},
 # CyNER (Alam et al. 2022): Malware Indicator System Organization Vulnerability
 'cyner':  {'Malware': 'MALWARE', 'Indicator': 'INDICATOR', 'Vulnerability': 'VULNERABILITY', 'System': 'UNCOVERED', 'Organization': 'UNCOVERED'},
 # AnnoCTR (Lange et al. 2024), `all_tags` layer: MALWARE GROUP TOOL LOC ORG SECTOR DATE CON TECHNIQUE TACTIC CLICommand/CodeSnippet
 'annoctr': {'MALWARE': 'MALWARE', 'GROUP': 'THREAT_ACTOR', 'TOOL': 'TOOL', 'LOC': 'LOCATION', 'ORG': 'UNCOVERED', 'SECTOR': 'UNCOVERED',
             'DATE': 'UNCOVERED', 'CON': 'UNCOVERED', 'TECHNIQUE': 'UNCOVERED', 'TACTIC': 'UNCOVERED', 'CLICommand/CodeSnippet': 'UNCOVERED'},
 # AttackER (Deka et al. 2024), 18 STIX-flavoured types
 'attacker': {'MALWARE': 'MALWARE', 'THREAT_ACTOR': 'THREAT_ACTOR', 'INTRUSION_SET': 'THREAT_ACTOR', 'ATTACK_TOOL': 'TOOL', 'GENERAL_TOOL': 'TOOL',
              'VULNERABILITY': 'VULNERABILITY', 'INDICATOR': 'INDICATOR', 'LOCATION': 'LOCATION', 'ATTACK_PATTERN': 'UNCOVERED', 'GENERAL_IDENTITY': 'UNCOVERED',
              'CAMPAIGN': 'UNCOVERED', 'COURSE_OF_ACTION': 'UNCOVERED', 'VICTIM_IDENTITY': 'UNCOVERED', 'INFRASTRUCTURE': 'UNCOVERED', 'MALWARE_ANALYSIS': 'UNCOVERED',
              'IMPACT': 'UNCOVERED', 'ATTACK_MOTIVATION': 'UNCOVERED', 'OBSERVED_DATA': 'UNCOVERED'},
}
EXT = EXP / 'data/external'
def read_json_sents(ds, split):
    if ds == 'annoctr':
        for line in open(EXT / f'annoctr/AnnoCTR/ner_json/{split}.json'):
            o = json.loads(line); yield o['tokens'], o['all_tags']
    elif ds == 'attacker':
        for line in open(EXT / f'attacker/{split}.json'):
            o = json.loads(line); yield o['tokens'], o['tags']


def read_conll(path):
    toks, tags = [], []
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            line = line.rstrip('\r\n')
            if not line.strip():
                if toks: yield toks, tags; toks, tags = [], []
                continue
            parts = line.split()
            parts = [p for p in parts if p != '']
            if len(parts) < 2: continue
            toks.append(parts[0]); tags.append(parts[-1])
    if toks: yield toks, tags

def norm_tag(tag, ds):
    """BIOES/BIO -> BIO with fine type; unknown/malformed tags -> O."""
    if tag == 'O' or '-' not in tag: return 'O', None
    pre, typ = tag.split('-', 1)
    if typ not in FINE2COARSE[ds]: return 'O', None
    pre = {'B': 'B', 'I': 'I', 'E': 'I', 'S': 'B'}.get(pre)
    if pre is None: return 'O', None
    return f'{pre}-{typ}', typ

def fix_bio(tags):
    """Ensure I- never follows O or different type without a B-."""
    out = []; prev = 'O'
    for t in tags:
        if t.startswith('I-') and (prev == 'O' or prev[2:] != t[2:]): t = 'B-' + t[2:]
        out.append(t); prev = t
    return out

def main():
    OUT.mkdir(parents=True, exist_ok=True); stats = {}; bad = collections.Counter()
    all_files = dict(FILES); all_files['annoctr'] = {'train': 'json', 'dev': 'json', 'test': 'json'}; all_files['attacker'] = {'train': 'json', 'dev': 'json', 'test': 'json'}
    for ds, splits in all_files.items():
        for split, path in splits.items():
            n = 0; ent = collections.Counter(); cent = collections.Counter(); ntok = 0
            with open(OUT / f'{ds}_{split}.jsonl', 'w') as fo:
                for i, (toks, tags) in enumerate(read_conll(path) if path != 'json' else read_json_sents(ds, split)):
                    fine = []; 
                    for t in tags:
                        nt, typ = norm_tag(t, ds); fine.append(nt)
                        if nt == 'O' and t != 'O': bad[(ds, t)] += 1
                    fine = fix_bio(fine)
                    coarse = fix_bio([('O' if f == 'O' else f[:2] + FINE2COARSE[ds][f[2:]]) for f in fine])
                    text = ' '.join(toks); offs = []; pos = 0
                    for tk in toks: offs.append([pos, pos + len(tk)]); pos += len(tk) + 1
                    for f in fine:
                        if f.startswith('B-'): ent[f[2:]] += 1
                    for c in coarse:
                        if c.startswith('B-'): cent[c[2:]] += 1
                    ntok += len(toks); n += 1
                    fo.write(json.dumps({'id': f'{ds}_{split}_{i}', 'dataset': ds, 'split': split, 'tokens': toks, 'fine': fine,
                                         'coarse': coarse, 'text': text, 'offsets': offs}, ensure_ascii=False) + '\n')
            stats[f'{ds}_{split}'] = {'sentences': n, 'tokens': ntok, 'fine_entities': dict(ent.most_common()), 'coarse_entities': dict(cent.most_common())}
            print(ds, split, n, 'sents', ntok, 'toks', dict(cent.most_common()))
    json.dump(FINE2COARSE, open(OUT / 'label_map.json', 'w'), indent=1)
    stats['dropped_malformed_tags'] = {f'{k[0]}:{k[1]}': v for k, v in bad.items()}
    json.dump(stats, open(OUT / 'stats.json', 'w'), indent=1); print('malformed tags dropped:', dict(bad))

if __name__ == '__main__': main()
