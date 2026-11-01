#!/usr/bin/env bash
# Usage: run_with_metrics.sh <run_dir> <command...>
# Records wall time, peak GPU memory (sampled every 5s), and environment into <run_dir>/run_meta.json
set -u
RUN_DIR="$1"; shift
mkdir -p "$RUN_DIR"
START=$(date -u +%Y-%m-%dT%H:%M:%SZ); T0=$(date +%s)
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 > "$RUN_DIR/gpu_samples.csv" 2>/dev/null &
SMI=$!
"$@" > "$RUN_DIR/stdout.log" 2>&1
RC=$?
kill $SMI 2>/dev/null
END=$(date -u +%Y-%m-%dT%H:%M:%SZ); T1=$(date +%s)
PEAK=$(awk -F', ' '{gsub(/ MiB/,"",$2); if($2+0>m)m=$2+0} END{print m+0}' "$RUN_DIR/gpu_samples.csv")
MEANUTIL=$(awk -F', ' '{gsub(/ %/,"",$3); s+=$3; n++} END{if(n>0)printf "%.1f", s/n; else print 0}' "$RUN_DIR/gpu_samples.csv")
PY=$(command -v python); 
cat > "$RUN_DIR/run_meta.json" <<JSON
{"start_utc":"$START","end_utc":"$END","wall_seconds":$((T1-T0)),"exit_code":$RC,
 "peak_gpu_mem_mib":$PEAK,"mean_gpu_util_pct":$MEANUTIL,
 "gpu":"$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)",
 "driver":"$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)",
 "hostname":"$(hostname)","cpu_count":$(nproc),"ram_gb":$(free -g | awk '/Mem:/{print $2}'),
 "command":"$*"}
JSON
echo "run finished rc=$RC wall=$((T1-T0))s peak_gpu_mib=$PEAK" >> "$RUN_DIR/stdout.log"
exit $RC
