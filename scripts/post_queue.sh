#!/usr/bin/env bash
cd "$(dirname "$0")/.."
while ! grep -q "QUEUE DONE" logs/queue.log; do sleep 30; done
scripts/gold_ner/run_E3.sh > logs/E3.log 2>&1
.venv/bin/python scripts/aggregate_tables.py > logs/aggregate.log 2>&1; .venv/bin/python scripts/write_paper_numbers.py >> logs/aggregate.log 2>&1
echo "POST QUEUE DONE $(date)"
