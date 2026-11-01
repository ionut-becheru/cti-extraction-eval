#!/usr/bin/env bash
export HF_HUB_ENABLE_HF_TRANSFER=0
PY=.venv/bin/python
for m in cisco-ai/SecureBERT2.0-base microsoft/deberta-v3-base FacebookAI/roberta-base markusbayer/CySecBERT urchade/gliner_large-v2.1 numind/NuNER_Zero MoritzLaurer/deberta-v3-large-zeroshot-v2.0 Qwen/Qwen3-8B fdtn-ai/Foundation-Sec-8B-Instruct; do
  echo "=== $m $(date)"; $PY -c "from huggingface_hub import snapshot_download; p=snapshot_download('$m', allow_patterns=['*.json','*.safetensors','*.txt','*.model','*.py','*.md','*.jinja','tokenizer*','*.tiktoken','*.spm']); print(p)"
done
echo "ALL DONE $(date)"
