"""Score the baselines on the calibration (days 9-10) and test (days 11-14) segments.

Usage: python -m cloudpilot.forecast.eval_baselines [function_key ...]
Metrics per horizon h (minutes ahead): MAE and wMAPE = sum|error| / sum(actual).
Run on the full cohort once, then look at the rows for h=3 (your forecast horizon).
"""
import sys
import numpy as np, pandas as pd
from pathlib import Path
from .baselines import LastValue, SameAsYesterday, YesterdayScaled

PROC = Path("data/processed")
DAY = 1440
SEGMENTS = {"calibration": (8 * DAY, 10 * DAY), "test": (10 * DAY, 14 * DAY)}
HORIZONS = [1, 2, 3, 4, 5]
STEP = 1   # evaluate every minute (use 3 to go faster)

COHORT = [   # from docs/cohort.md
    "6352f922_6d52e936_f375f0228b10", "65ae55ea_d27d1fdd_5336bda8faa5",
    "cec35dbb_076b740a_14f72e22ca86", "7656026e_9aba8d35_2aec780b74ed",
    "612a94f7_43f752c7_17b64d842f96", "f96d34ee_bf415a17_cba2d4a3cb55",
    "6e26c53b_70856110_9467f3a82699", "6aeca4ea_36bc5682_bde06c0fbc47",
]


def score(model, y, seg, horizons):
    lo, hi = SEGMENTS[seg]
    err = {h: [] for h in horizons}
    act = {h: [] for h in horizons}
    H = max(horizons)
    for t in range(lo, hi - H, STEP):          # origin t: only y[:t+1] is visible
        f = model.predict(y[: t + 1], H)
        for h in horizons:
            err[h].append(abs(f[h - 1] - y[t + h]))
            act[h].append(y[t + h])
    return {h: (float(np.mean(err[h])), float(np.sum(err[h]) / max(np.sum(act[h]), 1))) for h in horizons}


if __name__ == "__main__":
    keys = sys.argv[1:] or COHORT
    X = np.load(PROC / "series.npy").astype(float)
    meta = pd.read_csv(PROC / "meta.csv")
    models = [LastValue(), SameAsYesterday(), YesterdayScaled()]
    rows = []
    for key in keys:
        hit = meta.index[meta["key"] == key]
        if len(hit) == 0:
            print("skip (not in data):", key)
            continue
        y = X[hit[0]]
        for seg in SEGMENTS:
            for m in models:
                for h, (mae, wm) in score(m, y, seg, HORIZONS).items():
                    rows.append(dict(function=key[:8] + ".." + key[-4:], segment=seg, model=m.name, h=h, mae=mae, wmape=wm))
    df = pd.DataFrame(rows)
    out = Path("results/baseline_scores.csv")
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)
    print("saved", out)
    print("\nwMAPE at h=3 (lower is better), test segment:")
    print(df[(df.h == 3) & (df.segment == "test")].pivot(index="function", columns="model", values="wmape").round(3).to_string())
    print("\nwMAPE averaged over functions, by horizon (test):")
    print(df[df.segment == "test"].groupby(["h", "model"]).wmape.mean().unstack().round(3).to_string())
