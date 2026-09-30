"""Save the key series of one run from Prometheus into a parquet file.

Needs Prometheus reachable, e.g.:
  kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090

Usage:
  python -m cloudpilot.live.recorder --start <unix> --end <unix> --out results/run1.parquet
  python -m cloudpilot.live.recorder --last-minutes 10 --out results/run1.parquet
"""
import argparse, time, requests, pandas as pd

QUERIES = {
    "rps": 'sum(rate(app_requests_total[30s]))',
    "p95": 'histogram_quantile(0.95, sum(rate(app_request_duration_seconds_bucket[30s])) by (le))',
    "replicas": 'kube_deployment_status_replicas{deployment="demo-app"}',
    "ready_replicas": 'kube_deployment_status_replicas_ready{deployment="demo-app"}',
    # Added in Phase 3 when the exporter exists:
    "cp_mode": 'cloudpilot_mode',
    "cp_risk": 'cloudpilot_risk',
    "cp_desired": 'cloudpilot_desired_replicas',
}

def grab(prom, start, end, step):
    cols = {}
    for name, q in QUERIES.items():
        r = requests.get(f"{prom}/api/v1/query_range",
                         params=dict(query=q, start=start, end=end, step=step), timeout=30).json()
        res = r.get("data", {}).get("result", [])
        if res:
            cols[name] = pd.Series({float(t): float(v) for t, v in res[0]["values"]})
    df = pd.DataFrame(cols)
    df.index.name = "unix_time"
    return df

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prom", default="http://localhost:9090")
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--last-minutes", type=float)
    ap.add_argument("--step", type=int, default=12, help="seconds (12 = one trace-minute)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.last_minutes:
        a.end = time.time(); a.start = a.end - a.last_minutes * 60
    df = grab(a.prom, a.start, a.end, a.step)
    df.to_parquet(a.out)
    print(f"saved {len(df)} rows, columns {list(df.columns)} -> {a.out}")
