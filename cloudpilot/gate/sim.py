import os
import argparse, itertools, os
import numpy as np, pandas as pd
from scipy.stats import ks_2samp
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ap = argparse.ArgumentParser()
ap.add_argument("store")
ap.add_argument("--h", type=int, default=3)
ap.add_argument("--action", default="p50", choices=["p50", "U"], help="pods sized from this when TRUST")
ap.add_argument("--slack", type=float, default=1.2, help="violation if load > slack * C * pods")
ap.add_argument("--enter_q", type=float, default=0.5)
ap.add_argument("--exit_q", type=float, default=0.8)
ap.add_argument("--s_enter", type=int, default=3)
ap.add_argument("--s_exit", type=int, default=1)
a = ap.parse_args()
C, H, N, TRAIN_END = 16.0, a.h, 20, 11520
pods = lambda x: np.maximum(np.ceil(np.maximum(x, 0) / C), 1)

d = pd.read_parquet(a.store)
d = d[d.h == H].drop_duplicates(["function", "t"]).sort_values(["function", "t"]).reset_index(drop=True)
d["L"] = d.L.fillna(d.L_static).fillna(d.p10)
d["U"] = d.U.fillna(d.U_static).fillna(d.p90)

cz = np.load(os.environ.get("COHORT", "data/processed/cohort.npz"), allow_pickle=True)
keys = [str(k) for k in cz["keys"]]; S = cz["series"].astype(float)
def row(fn):
    for i, k in enumerate(keys):
        if k == fn or k.startswith(fn) or fn.startswith(k) or fn in k: return i
    raise KeyError(fn)

lvl = np.maximum(d.p50.abs(), 1.0)
d["f_width"] = (d.U - d.L) / lvl
d["miss"] = ((d.y < d.L) | (d.y > d.U)).astype(float)
d["relerr"] = (d.y - d.p50).abs() / lvl

parts = []
for f, g in d.groupby("function"):
    g = g.copy(); t = g.t.values
    k = np.searchsorted(t + H, t, side="right")          # forecasts already resolved at time t
    lo = np.maximum(k - N, 0); n = np.maximum(k - lo, 1)
    for col, name in [("miss", "f_miss"), ("relerr", "f_err")]:
        cs = np.concatenate([[0], np.cumsum(g[col].values)])
        g[name] = np.where(k > 0, (cs[k] - cs[lo]) / n, np.nan)
    l = np.log1p(S[row(f)]); k0 = np.arange(120); dr = []
    for tt in t:
        m = tt % 1440
        ref = np.concatenate([day * 1440 + ((m - k0) % 1440) for day in range(8)])   # training days only
        dr.append(ks_2samp(l[tt - k0], l[ref]).statistic)
    g["f_drift"] = dr
    parts.append(g)
SIG = ["f_width", "f_err", "f_miss", "f_drift"]; NS = ["n_" + s for s in SIG]
d = pd.concat(parts).dropna(subset=SIG)

for s in SIG: d["n_" + s] = 0.0
for f, g in d.groupby("function"):               # normalise each signal to [0,1] vs that function's calibration days
    cal_ = g[g.segment == "calibration"]
    for s in SIG:
        ref = np.sort(cal_[s].values)
        d.loc[g.index, "n_" + s] = np.searchsorted(ref, g[s].values, side="right") / len(ref)

plan = d.p50 if a.action == "p50" else d.U
d["pods_pred"] = pods(plan); d["pods_react"] = pods(d.y0)          # reactive = size to last observed load
d["v_pred"] = (d.y > a.slack * C * d.pods_pred).astype(int)
d["v_react"] = (d.y > a.slack * C * d.pods_react).astype(int)

cal = d[d.segment == "calibration"]; test = d[d.segment == "test"].copy()
print(f"store={os.path.basename(a.store)} action={a.action} | violation rate if always predictive: cal {cal.v_pred.mean():.3f} test {test.v_pred.mean():.3f}")

# ---- weights: logistic regression vs grid search, chosen on a held-out slice of calibration, then frozen
cut = cal.t.quantile(0.7); fit, val = cal[cal.t <= cut], cal[cal.t > cut]
lr = LogisticRegression(C=1.0, max_iter=1000).fit(fit[NS], fit.v_pred)
w_lr = np.clip(lr.coef_[0], 0, None); w_lr = w_lr / w_lr.sum() if w_lr.sum() > 0 else np.full(4, 0.25)
best = None
for ws in itertools.product([0, 1, 2, 3], repeat=4):
    if sum(ws) == 0: continue
    w = np.array(ws) / sum(ws); sc = roc_auc_score(fit.v_pred, fit[NS].values @ w)
    if best is None or sc > best[0]: best = (sc, w)
w_grid = best[1]; w_uni = np.full(4, 0.25)
auc = lambda w: roc_auc_score(val.v_pred, val[NS].values @ w)
cands = {"logistic": w_lr, "grid": w_grid}
pick = max(cands, key=lambda k: auc(cands[k])); W = cands[pick]
print("weights [width, error, coverage-miss, drift]")
for nme, w in [("uniform", w_uni), ("logistic", w_lr), ("grid", w_grid)]:
    print(f"  {nme:9s}", w.round(2), f"held-out AUROC {auc(w):.3f}")
print("  frozen:", pick)

d["risk"] = d[NS].values @ W; cal = d[d.segment == "calibration"]; test = d[d.segment == "test"].copy()
def within(w):
    r = [roc_auc_score(g.v_pred, g[NS].values @ w) for _, g in test.groupby("function") if g.v_pred.nunique() > 1]
    return np.mean(r)
print(f"TEST within-function AUROC for violations: uniform {within(w_uni):.3f} | frozen {within(W):.3f}  (0.5 = useless)")

te, tx = cal.risk.quantile(a.enter_q), cal.risk.quantile(a.exit_q); th = (te + tx) / 2
print(f"thresholds from calibration days: tau_enter={te:.3f} tau_exit={tx:.3f} naive={th:.3f} | smoothing enter={a.s_enter} exit={a.s_exit}")

def gate(risk):
    mode = np.zeros(len(risk), bool); cur = False; cin = cout = 0
    for i, r in enumerate(risk):
        if not cur:
            cin = cin + 1 if r < te else 0
            if cin >= a.s_enter: cur, cin, cout = True, 0, 0
        else:
            cout = cout + 1 if r > tx else 0
            if cout >= a.s_exit: cur, cin, cout = False, 0, 0
        mode[i] = cur
    return mode

def slo_fallback(t, vp, hold=30):
    mode = np.ones(len(t), bool); until = -1; ptr = 0
    for i in range(len(t)):
        while ptr < i and t[ptr] + H <= t[i]:
            if mode[ptr] and vp[ptr]: until = t[i] + hold
            ptr += 1
        mode[i] = t[i] >= until
    return mode

rows = []
for f, g in test.groupby("function"):
    t, r = g.t.values, g.risk.values
    modes = {"reactive only": np.zeros(len(g), bool), "always predictive": np.ones(len(g), bool),
             "SLO-triggered fallback": slo_fallback(t, g.v_pred.values),
             "CloudPilot naive threshold": r < th, "CloudPilot hysteresis": gate(r)}
    for nme, m in modes.items():
        rows.append(dict(policy=nme, violations=np.where(m, g.v_pred, g.v_react).mean(),
                         mean_pods=np.where(m, g.pods_pred, g.pods_react).mean(),
                         switches_per_100=(np.diff(m.astype(int)) != 0).mean() * 100, pct_predictive=m.mean() * 100))
R = pd.DataFrame(rows).groupby("policy", sort=False).mean()
R["pods_vs_reactive"] = R.mean_pods / R.loc["reactive only", "mean_pods"]
pd.options.display.float_format = "{:.3f}".format
print("\nTEST days, mean over 8 functions (reactive = pods sized to last observed load, ready after h minutes):\n")
print(R.to_string())
tag = os.path.basename(a.store).replace(".parquet", "")
R.to_csv(f"results/sim_{tag}_{a.action}.csv"); print(f"\nsaved results/sim_{tag}_{a.action}.csv")

# ---- diagnostic: how much could ANY gate gain? decision-relevant label = predictive violates but reactive does not
t = test.copy()
both = ((t.v_pred == 1) & (t.v_react == 1)).mean(); only_p = ((t.v_pred == 1) & (t.v_react == 0)).mean()
only_r = ((t.v_pred == 0) & (t.v_react == 1)).mean()
t["regret"] = ((t.v_pred == 1) & (t.v_react == 0)).astype(int)
ar = [roc_auc_score(g.regret, g.risk) for _, g in t.groupby("function") if g.regret.nunique() > 1]
print(f"HEADROOM always-pred {both + only_p:.3f} | oracle gate {both:.3f} | only-pred-violates {only_p:.3f} | only-reactive-violates {only_r:.3f} | risk AUROC for regret {np.mean(ar):.3f}")

# ---- selective gate: only the riskiest q of minutes go to reactive; threshold from calibration days only
from sklearn.linear_model import Ridge
d["net"] = d.v_pred - d.v_react
cal = d[d.segment == "calibration"]; test = d[d.segment == "test"]
rg = Ridge(alpha=1.0).fit(cal[cal.t <= cut][NS], cal[cal.t <= cut].net)
d["risk_net"] = rg.predict(d[NS]); cal = d[d.segment == "calibration"]; test = d[d.segment == "test"]
for name, col in [("frozen risk", "risk"), ("net-benefit risk", "risk_net")]:
    for q in [0, 0.02, 0.05, 0.1, 0.2, 0.4]:
        thr = cal[col].quantile(1 - q) if q > 0 else np.inf
        res = []
        for df in (cal, test):
            trust = df[col].values <= thr
            res.append((np.where(trust, df.v_pred, df.v_react).mean(),
                        np.where(trust, df.pods_pred, df.pods_react).mean() / df.pods_react.mean(), 1 - trust.mean()))
        print(f"SWEEP {name:16s} q={q:.2f} | cal viol {res[0][0]:.3f} | test viol {res[1][0]:.3f}  pods x{res[1][1]:.3f}  routed {res[1][2]:.1%}")

# ---- paired check on function-days: net-benefit gate vs always predictive (q fixed in advance, not picked on test)
cal = d[d.segment == "calibration"]; tst = d[d.segment == "test"].copy(); tst["day"] = tst.t // 1440
for q in [0.05, 0.10, 0.20]:
    thr = cal.risk_net.quantile(1 - q)
    tst["v_gate"] = np.where(tst.risk_net.values <= thr, tst.v_pred, tst.v_react)
    g = tst.groupby(["function", "day"]).agg(gate=("v_gate", "mean"), pred=("v_pred", "mean"))
    df_ = g.gate - g.pred
    print(f"PAIRED q={q:.2f} mean diff {df_.mean():+.4f} +/- {df_.std() / np.sqrt(len(df_)):.4f} (n={len(df_)}) | improved {np.mean(df_ < 0):.0%} worse {np.mean(df_ > 0):.0%}")
