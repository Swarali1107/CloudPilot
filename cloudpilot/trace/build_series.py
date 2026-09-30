"""Stitch the 14 daily Azure files into one 20,160-minute series per function.
Usage: python -m cloudpilot.trace.build_series data/raw data/processed [min_mean]
"""
import sys, numpy as np, pandas as pd
from pathlib import Path

RAW, OUT = Path(sys.argv[1]), Path(sys.argv[2])
MIN_MEAN = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0   # requests/minute
DAYS = range(1, 15)
OUT.mkdir(parents=True, exist_ok=True)
fn = lambda d: RAW / f"invocations_per_function_md.anon.d{d:02d}.csv"

def read_day(d):
    cols = pd.read_csv(fn(d), nrows=0).columns
    dt = {c: "int32" for c in cols[4:]}
    df = pd.read_csv(fn(d), dtype=dt)
    df.index = pd.Index(df.HashOwner.str[:8] + "_" + df.HashApp.str[:8] + "_" + df.HashFunction.str[:12], name="key")
    return df[~df.index.duplicated()]

# Pass 1: which functions exist on ALL 14 days and are busy enough?
means, present = [], None
for d in DAYS:
    df = read_day(d)
    m = df.drop(columns=["HashOwner", "HashApp", "HashFunction", "Trigger"]).mean(axis=1)
    means.append(m)
    present = set(df.index) if present is None else present & set(df.index)
    print(f"day {d:2d}: {len(df):6d} functions, in all days so far: {len(present)}")
avg = pd.concat(means, axis=1).loc[sorted(present)].mean(axis=1)
keep = avg[avg >= MIN_MEAN].index.tolist()
print(f"keeping {len(keep)} functions with mean >= {MIN_MEAN}/min on average")

# Pass 2: extract those rows and stitch days together
mat = np.zeros((len(keep), 14 * 1440), dtype=np.int32)
meta = None
for i, d in enumerate(DAYS):
    df = read_day(d).loc[keep]
    mat[:, i * 1440:(i + 1) * 1440] = df.drop(columns=["HashOwner", "HashApp", "HashFunction", "Trigger"]).to_numpy()
    if meta is None:
        meta = df[["HashOwner", "HashApp", "HashFunction", "Trigger"]].copy()
np.save(OUT / "series.npy", mat)
meta.reset_index().to_csv(OUT / "meta.csv", index=False)
print("saved", mat.shape, "->", OUT)
