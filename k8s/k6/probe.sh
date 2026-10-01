#!/usr/bin/env bash
# 1-minute capacity probe: 12 req/s on ONE pod. Fast state: p95 <= 50 ms. Slow state: p95 in the hundreds.
set -e
cd "$(dirname "$0")/../.."
kubectl delete scaledobject demo-app --ignore-not-found
kubectl scale deploy/demo-app --replicas=1
kubectl rollout status deploy/demo-app
sleep 20
python3 -c "import json; json.dump([12]*5, open('k8s/k6/rates.json','w'))"
./k8s/k6/run.sh 2>&1 | grep -v "Request Failed" | tee /tmp/probe.log | grep -E "http_req_failed|RUN START"
S=$(grep -o 'START=[0-9]*' /tmp/probe.log | cut -d= -f2)
E=$(grep -o 'END=[0-9]*' /tmp/probe.log | cut -d= -f2)
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090 >/dev/null &
PF=$!; sleep 2
python -m cloudpilot.live.recorder --start $S --end $E --out results/probe_last.parquet >/dev/null
kill $PF
S=$S python3 -c "
import os, pandas as pd
df = pd.read_parquet('results/probe_last.parquet'); df['sec'] = df.index - int(os.environ['S'])
w = df[df.sec >= 24]
print(f'PROBE 12 rps on 1 pod: rps={w.rps.mean():.1f}  p95 max={w.p95.max()*1000:.0f} ms  ready min={w.ready_replicas.min():.0f}')"
