import numpy as np, pandas as pd, torch, torch.nn as nn
torch.manual_seed(0); np.random.seed(0); torch.set_num_threads(4)
CTX, HS, QS = 60, 5, torch.tensor([0.1, 0.5, 0.9])
TRAIN_END, VAL_START = 11520, 10080

ref = pd.read_parquet("results/store_chronos_c512.parquet")
ref = ref[(ref.forecaster == "chronos2") & (ref.h == 1)][["function", "scenario", "seed", "segment", "t"]].drop_duplicates()
c = np.load("data/processed/cohort.npz", allow_pickle=True)
keys = [str(k) for k in c["keys"]]; S = c["series"].astype(float)
def row(fn):
    for i, k in enumerate(keys):
        if k == fn or k.startswith(fn) or fn.startswith(k) or fn in k: return i
    raise KeyError(fn)

fns = sorted(ref.function.unique())
stats, Z = {}, {}
for f in fns:
    s = S[row(f)]; l = np.log1p(s)
    mu, sd = l[:TRAIN_END].mean(), l[:TRAIN_END].std() + 1e-6
    stats[f] = (mu, sd); Z[f] = (l - mu) / sd

def windows(z, origins):
    idx = origins[:, None] + np.arange(-CTX + 1, 1)
    m = idx % 1440
    X = np.stack([z[idx], np.sin(2*np.pi*m/1440), np.cos(2*np.pi*m/1440)], -1)
    return torch.tensor(X, dtype=torch.float32)
def targets(z, origins):
    return torch.tensor(z[origins[:, None] + np.arange(1, HS + 1)], dtype=torch.float32)

tr_X, tr_Y, va_X, va_Y = [], [], [], []
for f in fns:
    z = Z[f]
    o_tr = np.arange(CTX, VAL_START - HS)
    o_va = np.arange(VAL_START, TRAIN_END - HS)
    tr_X.append(windows(z, o_tr)); tr_Y.append(targets(z, o_tr))
    va_X.append(windows(z, o_va)); va_Y.append(targets(z, o_va))
tr_X, tr_Y, va_X, va_Y = map(torch.cat, (tr_X, tr_Y, va_X, va_Y))
print("train windows", len(tr_X), "val windows", len(va_X))

class Net(nn.Module):
    def __init__(s):
        super().__init__(); s.g = nn.GRU(3, 64, batch_first=True); s.o = nn.Linear(64, HS * 3)
    def forward(s, x):
        h, _ = s.g(x); return s.o(h[:, -1]).view(-1, HS, 3)
def pinball(p, y):
    e = y[..., None] - p
    return torch.maximum(QS * e, (QS - 1) * e).mean()

net = Net(); opt = torch.optim.Adam(net.parameters(), 2e-3)
best, bad, state = 1e9, 0, None
for ep in range(30):
    net.train(); perm = torch.randperm(len(tr_X))
    for i in range(0, len(perm), 512):
        b = perm[i:i+512]; opt.zero_grad(); pinball(net(tr_X[b]), tr_Y[b]).backward(); opt.step()
    net.eval()
    with torch.no_grad(): v = pinball(net(va_X), va_Y).item()
    print(f"epoch {ep:2d} val pinball {v:.4f}")
    if v < best - 1e-4: best, bad, state = v, 0, {k: x.clone() for k, x in net.state_dict().items()}
    else:
        bad += 1
        if bad >= 3: break
net.load_state_dict(state); net.eval()

out = []
for f in fns:
    r = ref[ref.function == f]; o = r.t.values.astype(int); z = Z[f]; s = S[row(f)]; mu, sd = stats[f]
    with torch.no_grad(): p = net(windows(z, o)).numpy()
    p = np.sort(p, axis=-1)
    p = np.clip(np.expm1(p * sd + mu), 0, None)
    for h in range(1, HS + 1):
        d = r.copy(); d["h"] = h; d["y0"] = s[o]; d["y"] = s[o + h]
        d["p10"], d["p50"], d["p90"] = p[:, h-1, 0], p[:, h-1, 1], p[:, h-1, 2]
        out.append(d)
D = pd.concat(out); D["forecaster"] = "lstm"; D["context"] = CTX
D.to_parquet("results/store_lstm.parquet"); print("saved results/store_lstm.parquet", D.shape)

# quick check: test segment, h=3, MAE / mean actual
T = D[(D.segment == "test") & (D.h == 3)]
for name, col in [("last_minute", "y0"), ("lstm_p50", "p50")]:
    r = T.groupby("function").apply(lambda g: (g[col] - g.y).abs().mean() / g.y.mean(), include_groups=False)
    print(name, r.round(3).to_dict(), "MEAN", round(r.mean(), 3))
print("(Chronos-2 mean was 0.196, last_minute 0.237)")
