import sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

C, H, N = 16.0, 3, 20
store = sys.argv[1] if len(sys.argv) > 1 else "results/store_chronos_c512_cal.parquet"

d = pd.read_parquet(store)
d = d[d.h == H].sort_values(["function", "t"]).copy()
d["L"] = d.L.fillna(d.L_static); d["U"] = d.U.fillna(d.U_static)
lvl = np.maximum(d.p50.abs(), 1.0)
d["bad"] = (d.y > C * np.ceil(np.maximum(d.p50, 0) / C)).astype(int)   # under-provisioned
d["f_width"] = (d.U - d.L) / lvl
d["f_disagree"] = (d.p50 - d.y0).abs() / np.maximum(d.y0.abs(), 1.0)
d["miss"] = ((d.y < d.L) | (d.y > d.U)).astype(float)
d["relerr"] = (d.y - d.p50).abs() / lvl

out = []
for f, g in d.groupby("function"):
    g = g.copy(); t = g.t.values
    k = np.searchsorted(t + H, t, side="right")   # forecasts resolved by time t only
    cm = np.concatenate([[0], np.cumsum(g.miss.values)])
    ce = np.concatenate([[0], np.cumsum(g.relerr.values)])
    lo = np.maximum(k - N, 0); n = np.maximum(k - lo, 1)
    g["f_miss"] = np.where(k > 0, (cm[k] - cm[lo]) / n, np.nan)
    g["f_err"] = np.where(k > 0, (ce[k] - ce[lo]) / n, np.nan)
    y0 = g.y0.astype(float)
    g["f_vol"] = (y0.rolling(10).std() / np.maximum(y0.rolling(10).mean(), 1.0)).values
    out.append(g)
d = pd.concat(out)

FEATS = ["f_width", "f_miss", "f_err", "f_disagree", "f_vol"]
d = d.dropna(subset=FEATS)
cal, test = d[d.segment == "calibration"], d[d.segment == "test"]
print(f"bad rate: calibration {cal.bad.mean():.3f} | test {test.bad.mean():.3f}")

sc = StandardScaler().fit(cal[FEATS])
lr = LogisticRegression(max_iter=1000).fit(sc.transform(cal[FEATS]), cal.bad)
test = test.copy()
test["risk"] = lr.predict_proba(sc.transform(test[FEATS]))[:, 1]
print("coefficients:", dict(zip(FEATS, lr.coef_[0].round(2))))

def within(col):
    a = [roc_auc_score(g.bad, g[col]) for _, g in test.groupby("function") if g.bad.nunique() > 1]
    return np.mean(a)

print("\nAUROC on TEST (0.5 = useless):")
print(f"  band width only : pooled {roc_auc_score(test.bad, test.f_width):.3f} | within-function {within('f_width'):.3f}")
print(f"  full risk score : pooled {roc_auc_score(test.bad, test.risk):.3f} | within-function {within('risk'):.3f}")

print("\nrisk-coverage on TEST (bad-rate among the lowest-risk X% of predictions):")
fr = [0.5, 0.7, 0.8, 0.9, 1.0]
plt.figure(figsize=(5, 4))
for col, name in [("f_width", "width only"), ("risk", "full risk score")]:
    s = test.sort_values(col); rates = []
    for x in np.linspace(0.1, 1, 19):
        rates.append(s.bad.iloc[: int(len(s) * x)].mean())
    plt.plot(np.linspace(0.1, 1, 19), rates, label=name)
    print(f"  {name:16s}", {x: round(s.bad.iloc[: int(len(s) * x)].mean(), 3) for x in fr})
plt.xlabel("fraction of predictions trusted (lowest risk first)"); plt.ylabel("under-provision rate")
plt.legend(); plt.tight_layout(); plt.savefig("results/risk_coverage.png", dpi=150)
print("\nsaved results/risk_coverage.png")
