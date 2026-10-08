import sys
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

C, H, N = 16.0, 3, 20
d = pd.read_parquet(sys.argv[1] if len(sys.argv) > 1 else "results/store_chronos_c512_cal.parquet")
d = d[d.h == H].sort_values(["function", "t"]).copy()
d["L"] = d.L.fillna(d.L_static); d["U"] = d.U.fillna(d.U_static)
lvl = np.maximum(d.p50.abs(), 1.0)
cap = C * np.maximum(np.ceil(np.maximum(d.p50, 0) / C), 1)
d["bad_severe"] = ((d.y - cap) / cap > 0.2).astype(int)        # traffic > provisioned capacity by 20%+
d["bad_err"] = ((d.y - d.p50).abs() / lvl > 0.3).astype(int)    # forecast off by more than 30%
d["bad_aboveU"] = (d.y > d.U).astype(int)                       # traffic above even the safe band
d["f_width"] = (d.U - d.L) / lvl
d["f_disagree"] = (d.p50 - d.y0).abs() / np.maximum(d.y0.abs(), 1.0)
d["miss"] = ((d.y < d.L) | (d.y > d.U)).astype(float)
d["relerr"] = (d.y - d.p50).abs() / lvl
d["signed"] = (d.y - d.p50) / lvl

out = []
for f, g in d.groupby("function"):
    g = g.copy(); t = g.t.values
    k = np.searchsorted(t + H, t, side="right")      # only forecasts already resolved at time t
    lo = np.maximum(k - N, 0); n = np.maximum(k - lo, 1)
    for col, name in [("miss", "f_miss"), ("relerr", "f_err"), ("signed", "f_bias")]:
        c = np.concatenate([[0], np.cumsum(g[col].values)])
        g[name] = np.where(k > 0, (c[k] - c[lo]) / n, np.nan)
    y0 = g.y0.astype(float)
    g["f_vol"] = (y0.rolling(10).std() / np.maximum(y0.rolling(10).mean(), 1.0)).values
    g["f_trend"] = ((y0 - y0.shift(3)) / np.maximum(y0, 1.0)).values
    out.append(g)
d = pd.concat(out)

FEATS = ["f_width", "f_miss", "f_err", "f_disagree", "f_vol", "f_bias", "f_trend"]
d = d.dropna(subset=FEATS)
cal, test = d[d.segment == "calibration"], d[d.segment == "test"].copy()

def within(df, col, tgt):
    a = [roc_auc_score(g[tgt], g[col]) for _, g in df.groupby("function") if g[tgt].nunique() > 1]
    return np.mean(a), len(a)

for tgt in ["bad_severe", "bad_err", "bad_aboveU"]:
    sc = StandardScaler().fit(cal[FEATS])
    lr = LogisticRegression(max_iter=1000).fit(sc.transform(cal[FEATS]), cal[tgt])
    test["risk"] = lr.predict_proba(sc.transform(test[FEATS]))[:, 1]
    print(f"\n=== target {tgt}: bad rate cal {cal[tgt].mean():.3f} | test {test[tgt].mean():.3f} ===")
    print("coef:", {k: round(float(v), 2) for k, v in zip(FEATS, lr.coef_[0])})
    for col, name in [("f_width", "width only"), ("risk", "full score")]:
        w, nf = within(test, col, tgt)
        print(f"  {name:11s} AUROC pooled {roc_auc_score(test[tgt], test[col]):.3f} | within-function {w:.3f} ({nf} functions)")
    s = test.sort_values("risk")
    print("  bad-rate among lowest-risk X% (full score):",
          {x: round(float(s[tgt].iloc[:int(len(s) * x)].mean()), 3) for x in [0.5, 0.8, 1.0]})
