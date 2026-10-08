"""Score a forecast store: p50 error vs 'same as last minute', and how often the p10-p90 band holds the actual.

Usage: python -m cloudpilot.forecast.compare_store results/store_chronos_c512.parquet [--h 3]
Raw p10-p90 is an 80% band, so coverage near 80% means well calibrated; the calibration step widens it to 90%.
"""
import argparse
import numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("store")
ap.add_argument("--h", type=int, default=3)
a = ap.parse_args()

df = pd.read_parquet(a.store)
df = df[df.h == a.h]
rows = []
for (fn, seg), g in df.groupby(["function", "segment"]):
    s = max(g.y.sum(), 1)
    rows.append(dict(
        function=fn[:8] + ".." + fn[-4:], segment=seg,
        wmape_model=(g.p50 - g.y).abs().sum() / s,
        wmape_last_minute=(g.y0 - g.y).abs().sum() / s,
        coverage_p10_p90=((g.y >= g.p10) & (g.y <= g.p90)).mean(),
        rel_width=((g.p90 - g.p10) / np.maximum(g.p50, 1)).median(),
    ))
r = pd.DataFrame(rows)
r["beats_last_minute"] = r.wmape_model < r.wmape_last_minute
pd.set_option("display.width", 200)
print(f"h = {a.h}   (forecaster: {df.forecaster.iloc[0]}, context: {df.context.iloc[0]})")
print(r.round(3).to_string(index=False))
t = r[r.segment == "test"]
print(f"\ntest: model beats last-minute on {int(t.beats_last_minute.sum())} of {len(t)} functions; "
      f"mean coverage {t.coverage_p10_p90.mean():.2f} (80% band)")
