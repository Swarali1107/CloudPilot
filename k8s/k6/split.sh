#!/usr/bin/env bash
# Per-pod request split during the last run (needs /tmp/split.log from a run.sh run).
S=$(grep -o 'START=[0-9]*' /tmp/split.log | cut -d= -f2)
E=$(grep -o 'END=[0-9]*' /tmp/split.log | cut -d= -f2)
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090 >/dev/null &
PF=$!; sleep 2
S=$S E=$E python3 - <<'PY'
import os, requests
r = requests.get("http://localhost:9090/api/v1/query_range", params=dict(
    query='sum by (pod)(rate(app_requests_total[30s]))',
    start=os.environ["S"], end=os.environ["E"], step=12)).json()
for s in r["data"]["result"]:
    v = [float(x[1]) for x in s["values"][-6:]]
    print(s["metric"]["pod"], f"mean req/s over last minute: {sum(v)/len(v):.1f}")
PY
kill $PF
