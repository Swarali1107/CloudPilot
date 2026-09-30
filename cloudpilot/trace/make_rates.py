"""Turn one Azure function into rates.json for the k6 replay.

Usage:
  python -m cloudpilot.trace.make_rates <function_key> <day 1-14> <C_rps> [peak_pods=8] [minutes=120] [start_minute=auto]

Output: k8s/k6/rates.json = requests PER SECOND, one number per trace-minute
(k6 holds each number for STAGE_SECONDS, default 12 s).
"""
import sys, json, numpy as np, pandas as pd
from pathlib import Path

PROC = Path("data/processed")
OUT = Path("k8s/k6/rates.json")

key, day, C = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
pods = float(sys.argv[4]) if len(sys.argv) > 4 else 8
L = int(sys.argv[5]) if len(sys.argv) > 5 else 120
X = np.load(PROC / "series.npy").astype(float)
meta = pd.read_csv(PROC / "meta.csv")
i = meta.index[meta["key"] == key][0]
x = X[i, (day - 1) * 1440: day * 1440]
if len(sys.argv) > 6:
    s = int(sys.argv[6])
else:  # auto: the window with the biggest swing (a real ramp)
    sm = pd.Series(x).rolling(5, center=True, min_periods=1).mean().to_numpy()
    s = int(np.argmax([sm[a:a + L].max() - sm[a:a + L].min() for a in range(0, 1440 - L)]))
seg = x[s:s + L]
scale = (pods * C * 0.7) / seg.max()  # busiest minute needs about `pods` pods at 70% load
rates = [round(float(v * scale), 2) for v in seg]
OUT.parent.mkdir(parents=True, exist_ok=True)
json.dump(rates, open(OUT, "w"))
print(f"function {key} ({meta.Trigger[i]}), day {day}, minutes {s}-{s+L}, scale={scale:.4f}")
print(f"raw counts/min: min={seg.min():.0f} max={seg.max():.0f}  ->  req/s: min={min(rates)} max={max(rates)}")
print(f"saved {OUT} with {len(rates)} values")
