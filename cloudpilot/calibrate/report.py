"""Coverage table (raw vs static vs rolling) and a coverage-over-time plot.

Usage: python -m cloudpilot.calibrate.report results/store_chronos_c512_cal.parquet [--h 3] [--win 60]
Test segment only. Coverage = share of actuals inside the band. Target 0.90 for the calibrated bands.
"""
import argparse
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument("store")
ap.add_argument("--h", type=int, default=3)
ap.add_argument("--win", type=int, default=60, help="origins per rolling-coverage point in the plot")
a = ap.parse_args()

df = pd.read_parquet(a.store)
df = df[(df.h == a.h) & (df.segment == "test") & df.q.notna()].sort_values(["function", "t"])
inside = lambda lo, hi: (df.y >= lo) & (df.y <= hi)
df["in_raw"] = inside(df.p10, df.p90)
df["in_static"] = inside(df.L_static, df.U_static)
df["in_roll"] = inside(df.L, df.U)
w = lambda lo, hi: ((hi - lo) / np.maximum(df.p50, 1))
df["w_raw"], df["w_static"], df["w_roll"] = w(df.p10, df.p90), w(df.L_static, df.U_static), w(df.L, df.U)

r = df.groupby("function").agg(cov_raw=("in_raw", "mean"), cov_static=("in_static", "mean"), cov_roll=("in_roll", "mean"),
                               width_raw=("w_raw", "median"), width_roll=("w_roll", "median"))
pd.set_option("display.width", 200)
print(f"h = {a.h}, test segment, target coverage 0.90")
print(r.round(3).to_string())
print("\nmean coverage: raw %.3f | static %.3f | rolling %.3f" % (r.cov_raw.mean(), r.cov_static.mean(), r.cov_roll.mean()))

fns = list(r.index)
fig, axes = plt.subplots(2, 4, figsize=(18, 7), sharey=True)
for ax, fn in zip(axes.ravel(), fns):
    g = df[df.function == fn]
    x = (g.t.to_numpy() - 10 * 1440) / 1440 + 11          # day number (test starts on day 11)
    for col, lab, c in [("in_raw", "raw (80% band)", "tab:gray"), ("in_roll", "rolling CQR (90%)", "tab:blue")]:
        ax.plot(x, g[col].rolling(a.win, min_periods=a.win).mean(), label=lab, color=c, lw=1.2)
    ax.axhline(0.9, color="tab:red", ls="--", lw=0.8)
    ax.set_title(fn, fontsize=9); ax.set_ylim(0.3, 1.02); ax.set_xlabel("day")
axes[0, 0].legend(fontsize=7); axes[0, 0].set_ylabel(f"coverage ({a.win} origins)")
plt.tight_layout()
out = f"results/coverage_h{a.h}.png"
plt.savefig(out, dpi=110)
print("plot saved:", out)
