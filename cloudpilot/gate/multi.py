import sys, numpy as np, pandas as pd
H = 3
PATH = sys.argv[1] if len(sys.argv) > 1 else "results/store_chronos_c512_cal.parquet"
df = pd.read_parquet(PATH)
df = df[(df.forecaster == "chronos2") & (df.h == H)].drop_duplicates(["function", "t"]).copy()
c = np.load("data/processed/cohort.npz", allow_pickle=True)
keys = [str(k) for k in c["keys"]]; S = c["series"]

def row(fn):
    for i, k in enumerate(keys):
        if k == fn or k.startswith(fn) or fn.startswith(k) or fn in k:
            return i
    raise KeyError(fn)

CANDS = ["last_minute", "seasonal", "ma5", "chronos2"]
parts = []
print("alignment check (origin match rate, target match rate):")
for fn, g in df.groupby("function"):
    s = S[row(fn)].astype(float); t = g.t.values; y0 = g.y0.values; y = g.y.values
    off = max(range(-2, 3), key=lambda k: np.mean(s[np.clip(t + k, 0, len(s) - 1)] == y0))
    o = t + off
    ok = (o + H < len(s)) & (o - 4 >= 0) & (o + H - 1440 >= 0)
    g = g[ok].copy(); o = o[ok]
    print(f"  {fn[:8]} off={off} origin={np.mean(s[o] == g.y0.values):.3f} target={np.mean(s[o + H] == g.y.values):.3f}")
    g["last_minute"] = s[o]
    g["seasonal"] = s[o + H - 1440]
    g["ma5"] = np.mean([s[o - k] for k in range(5)], axis=0)
    g["chronos2"] = g.p50.values
    g["risk"] = (g.p90 - g.p10) / (g.p50.abs() + 1)
    g["fn"] = fn[:8]
    parts.append(g)
D = pd.concat(parts)
for m in CANDS:
    D["e_" + m] = (D[m] - D.y).abs()

def nmae(sub, err):  # MAE / mean actual
    return err.mean() / sub.y.mean()

cal = {f: g for f, g in D[D.segment == "calibration"].groupby("fn")}
tst = {f: g for f, g in D[D.segment == "test"].groupby("fn")}
fns = sorted(tst)

# 1) headroom
rows = []
for f in fns:
    gc, gt = cal[f], tst[f]
    best_single = min(CANDS, key=lambda m: gc["e_" + m].mean())
    orc = gt[["e_" + m for m in CANDS]].min(axis=1)
    rows.append(dict(fn=f, best_single_cal=best_single,
                     **{m: nmae(gt, gt["e_" + m]) for m in CANDS},
                     oracle=nmae(gt, orc)))
H1 = pd.DataFrame(rows).set_index("fn")
H1["best_single"] = [H1.loc[f, H1.loc[f, "best_single_cal"]] for f in fns]
H1["headroom_%"] = 100 * (H1.best_single - H1.oracle) / H1.best_single
print("\nTEST, h=3, MAE / mean actual (lower is better)")
print(H1.round(3).to_string()); print("MEAN headroom %:", round(H1["headroom_%"].mean(), 1))

# 2) gate as router: fallback = best non-chronos candidate on calibration
fb = {f: min(["last_minute", "seasonal", "ma5"], key=lambda m: cal[f]["e_" + m].mean()) for f in fns}
print("\nfallback model per function:", fb)

def score(groups, frac, rng=None, random_route=False):
    vals = []
    for f in fns:
        g = groups[f]; gc = cal[f]
        if frac <= 0:
            route = np.zeros(len(g), bool)
        elif random_route:
            route = rng.random(len(g)) < frac
        else:
            tau = np.quantile(gc.risk, 1 - frac)
            route = (g.risk > tau).values
        e = np.where(route, g["e_" + fb[f]].values, g.e_chronos2.values)
        vals.append(e.mean() / g.y.mean())
    return float(np.mean(vals))

fracs = np.round(np.linspace(0, 1, 21), 2)
rng = np.random.default_rng(0)
tab = []
for fr in fracs:
    tab.append(dict(frac_routed=fr, cal=score(cal, fr), test_gate=score(tst, fr),
                    test_random=np.mean([score(tst, fr, rng, True) for _ in range(20)])))
T = pd.DataFrame(tab).set_index("frac_routed")
best = T.cal.idxmin()
print("\nSweep (macro-mean error; 'cal' is what tau is chosen on)")
print(T.round(4).to_string())
print(f"\nfraction chosen on calibration: {best}")
print(f"TEST  chronos only: {T.loc[0.0,'test_gate']:.4f} | gate: {T.loc[best,'test_gate']:.4f} | random same rate: {T.loc[best,'test_random']:.4f}")
print(f"TEST  best single (cal-chosen) mean: {H1.best_single.mean():.4f} | oracle: {H1.oracle.mean():.4f}")
T.to_csv("results/multi_sweep.csv"); H1.to_csv("results/multi_headroom.csv")
