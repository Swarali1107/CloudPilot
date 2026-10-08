"""Forecast every minute of the calibration and test segments and save the raw forecast store.

Usage (Colab, GPU):
  python -m cloudpilot.forecast.precompute --context 512 --step 3 --out results/store_chronos_c512.parquet

Store columns (one row per forecast): function, scenario, seed, segment, t, h, y0, y, p10, p50, p90, forecaster, context
  t  = ORIGIN minute (the forecast only used demand up to and including minute t)
  h  = minutes ahead, so the target is minute t+h and y is its actual demand
  y0 = demand at the origin (so "same as last minute" can be computed from the store itself)
L, U and q (calibrated interval) are added later by the calibration step in a separate file.
"""
import argparse, time
import numpy as np, pandas as pd
from pathlib import Path

DAY = 1440
SEGMENTS = {"calibration": (8 * DAY, 10 * DAY), "test": (10 * DAY, 14 * DAY)}


def build_store(fc, keys, series, segments, step, H, chunk=512, scenario="normal", seed=0, context=None, log=print):
    frames = []
    for key, y in zip(keys, series):
        y = np.asarray(y, dtype=np.float32)
        for seg in segments:
            lo, hi = SEGMENTS[seg]
            ts = np.arange(lo, hi - H, step)
            for c in range(0, len(ts), chunk):
                tt = ts[c:c + chunk]
                P = fc.predict_batch([y[: t + 1] for t in tt], H)          # (n, H, 3), uses only y[:t+1]
                n = len(tt)
                hh = np.tile(np.arange(1, H + 1), n)
                tr = np.repeat(tt, H)
                frames.append(pd.DataFrame({
                    "function": key, "scenario": scenario, "seed": seed, "segment": seg,
                    "t": tr, "h": hh, "y0": y[tr], "y": y[tr + hh],
                    "p10": P[:, :, 0].reshape(-1), "p50": P[:, :, 1].reshape(-1), "p90": P[:, :, 2].reshape(-1),
                    "forecaster": fc.name, "context": context}))
            log(f"  {key[:8]}..{key[-4:]} {seg}: {len(ts)} origins")
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/processed/cohort.npz")
    ap.add_argument("--context", type=int, default=512)
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--step", type=int, default=3, help="forecast every STEP-th minute (1 = every minute)")
    ap.add_argument("--segments", default="calibration,test")
    ap.add_argument("--functions", default="", help="comma list of key prefixes (default: all 8)")
    ap.add_argument("--device", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    d = np.load(a.data)
    keys, series = list(d["keys"]), d["series"]
    if a.functions:
        pref = a.functions.split(",")
        sel = [i for i, k in enumerate(keys) if any(k.startswith(p) for p in pref)]
        keys, series = [keys[i] for i in sel], series[sel]

    import torch
    from .chronos_fc import ChronosForecaster
    device = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    print("device:", device, "| functions:", len(keys), "| context:", a.context, "| step:", a.step)
    fc = ChronosForecaster(device=device, context=a.context)
    t0 = time.time()
    df = build_store(fc, keys, series, a.segments.split(","), a.step, a.horizon, context=a.context)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(a.out)
    print(f"saved {len(df)} rows -> {a.out}  ({time.time() - t0:.0f} s)")
