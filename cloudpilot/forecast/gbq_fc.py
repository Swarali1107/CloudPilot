import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor as HGB
HS, TRAIN_END, CTX = 5, 11520, 60
LAGS = [0, 1, 2, 3, 4, 5, 8, 12, 20, 30, 45, 59, 1439]

ref = pd.read_parquet("results/store_chronos_c512.parquet")
ref = ref[(ref.forecaster == "chronos2") & (ref.h == 1)][["function", "scenario", "seed", "segment", "t"]].drop_duplicates()
c = np.load("data/processed/cohort.npz", allow_pickle=True)
keys = [str(k) for k in c["keys"]]; S = c["series"].astype(float)
def row(fn):
    for i, k in enumerate(keys):
        if k == fn or k.startswith(fn) or fn.startswith(k) or fn in k: return i
    raise KeyError(fn)

fns = sorted(ref.function.unique()); Z, stats = {}, {}
for f in fns:
    l = np.log1p(S[row(f)]); mu, sd = l[:TRAIN_END].mean(), l[:TRAIN_END].std() + 1e-6
    stats[f] = (mu, sd); Z[f] = (l - mu) / sd

def feats(z, o):
    m = o % 1440
    F = [z[o - L] for L in LAGS]
    F += [z[o - 4:o + 1].mean() * np.ones(1)[0] if False else np.mean([z[o - k] for k in range(5)], 0),
          np.std([z[o - k] for k in range(15)], 0), np.sin(2*np.pi*m/1440), np.cos(2*np.pi*m/1440)]
    return np.stack(F, 1)

# training set: origins well before calibration; last day of train used for early stopping inside HGB
Xtr, Ytr = [], {h: [] for h in range(1, HS + 1)}
for f in fns:
    o = np.arange(1440, TRAIN_END - HS)[::2]   # every 2nd minute to keep it fast
    Xtr.append(feats(Z[f], o))
    for h in range(1, HS + 1): Ytr[h].append(Z[f][o + h] - Z[f][o])   # predict change vs now
Xtr = np.vstack(Xtr); Ytr = {h: np.concatenate(v) for h, v in Ytr.items()}
print("train rows", len(Xtr))

models = {}
for h in range(1, HS + 1):
    for q in (0.1, 0.5, 0.9):
        models[h, q] = HGB(loss="quantile", quantile=q, max_iter=200, learning_rate=0.08,
                           max_leaf_nodes=31, early_stopping=True, validation_fraction=0.1,
                           random_state=0).fit(Xtr, Ytr[h])
    print("trained h =", h)

out = []
for f in fns:
    r = ref[ref.function == f]; o = r.t.values.astype(int); z = Z[f]; s = S[row(f)]; mu, sd = stats[f]
    X = feats(z, o)
    for h in range(1, HS + 1):
        P = np.sort(np.stack([models[h, q].predict(X) for q in (0.1, 0.5, 0.9)], 1), axis=1)
        P = np.clip(np.expm1((z[o][:, None] + P) * sd + mu), 0, None)
        d = r.copy(); d["h"] = h; d["y0"] = s[o]; d["y"] = s[o + h]
        d["p10"], d["p50"], d["p90"] = P[:, 0], P[:, 1], P[:, 2]
        out.append(d)
D = pd.concat(out); D["forecaster"] = "gbq"; D["context"] = CTX
D.to_parquet("results/store_gbq.parquet"); print("saved results/store_gbq.parquet", D.shape)

T = D[(D.segment == "test") & (D.h == 3)]
for name, col in [("last_minute", "y0"), ("gbq_p50", "p50")]:
    r = T.groupby("function").apply(lambda g: (g[col] - g.y).abs().mean() / g.y.mean(), include_groups=False)
    print(name, r.round(3).to_dict(), "MEAN", round(r.mean(), 3))
print("(Chronos-2 mean was 0.196, last_minute 0.237)")
