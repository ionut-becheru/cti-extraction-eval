#!/usr/bin/env python3
"""Render paper_numbers.json (from aggregate_tables.py) plus fixed reproduction numbers into paper_numbers.md."""
import json, pathlib
EXP = pathlib.Path(__file__).resolve().parent.parent; ROOT = EXP
N = json.load(open(EXP / 'paper_numbers.json'))
L = ['# Paper numbers', '', 'Every number recommended for the paper, with the script and run that produced it. Regenerate with `scripts/aggregate_tables.py` then `scripts/write_paper_numbers.py`.', '',
     '| key | value | run | script |', '|---|---|---|---|']
SCRIPT = {'T1': 'scripts/gold_ner/eval_dictionary_ner.py', 'T2': 'scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py', 'T3': 'scripts/gold_ner/finetune_ner.py', 'T4': 'scripts/noise/make_noisy_sets.py + run_E5_eval.sh',
          'T5': 'scripts/relevance/relevance_eval_hard.py', 'KEV': 'runs/THESIS_artifacts/kev_overlap.json (thesis pipeline run)'}
for k, v in N.items():
    val = {kk: vv for kk, vv in v.items() if kk != 'run'}; L.append(f"| {k} | {json.dumps(val)} | {v.get('run')} | {SCRIPT.get(k.split('.')[0], '')} |")
L += ['', '## KEV snapshot', '', '- CISA KEV catalogVersion 2026.05.15 (1,592 entries, 1,611 unique CVE strings), retrieved 2026-05-16; overlap figures in runs/THESIS_artifacts/kev_overlap.json']
ns = EXP / 'data/gold_ner/noise_stats.json'
if ns.exists():
    L += ['', '## Gold mentions surviving back-translation verbatim (scripts/noise/make_noisy_sets.py, run E5_noise/make_sets)', '', '| set | gold | dropped | dropped % |', '|---|---|---|---|']
    for k, v in json.load(open(ns)).items(): L.append(f"| {k} | {v['gold_mentions']} | {v['dropped_gold']} | {v['dropped_pct']} |")
(ROOT / 'paper_numbers.md').write_text('\n'.join(L)); print('paper_numbers.md written', len(N), 'entries')
