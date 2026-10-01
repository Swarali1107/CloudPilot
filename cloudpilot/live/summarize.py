"""Summarize one recorded run.
Usage: python -m cloudpilot.live.summarize results/x.parquet --start <unix start> [--C 16] [--skip 60]
"""
import argparse, numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("parquet")
ap.add_argument("--start", type=int, required=True)
ap.add_argument("--C", type=float, default=16)
ap.add_argument("--skip", type=int, default=60, help="seconds of warm-up to ignore")
ap.add_argument("--threshold-ms", type=float, default=200)
a = ap.parse_args()

df = pd.read_parquet(a.parquet)
df["sec"] = (df.index - a.start).astype(int)
w = df[df.sec >= a.skip].copy()
w["need"] = np.ceil(w.rps / a.C)
w["p95_ms"] = (w.p95 * 1000).round()
bad = (w.p95 * 1000 > a.threshold_ms) | w.p95.isna()   # NaN = pod too overloaded to answer
under = w.ready_replicas < w.need
print(w[["sec", "rps", "p95_ms", "need", "replicas", "ready_replicas"]].round(1).iloc[::5].to_string(index=False))
print(f"\nviolating windows: {int(bad.sum())} of {len(w)}")
print(f"under-provisioned windows (ready < ceil(rps/C)): {int(under.sum())}")
print(f"peak replicas: {w.replicas.max():.0f}, replica-minutes: {w.replicas.sum() * 12 / 60:.1f}")
