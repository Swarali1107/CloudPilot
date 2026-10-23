import numpy as np
from pathlib import Path
P = Path("data/processed")
c = np.load(P / "cohort.npz", allow_pickle=True); keys, S = c["keys"], c["series"].astype(float)
T0, T1 = 14400, S.shape[1]; mu = S[:, :11520].mean(1)
for name in ["level", "unseen"]:
    out = S.copy()
    for i in range(len(S)):
        if name == "level":
            x = S[i, T0:T1].copy(); x[len(x) // 2:] *= 2.5
        else:
            j = (i + 3) % len(S); x = S[j, T0:T1] * (mu[i] / max(mu[j], 1e-6))
        out[i, T0:T1] = np.rint(np.maximum(x, 0))
    np.savez_compressed(P / f"cohort_{name}.npz", keys=keys, series=out.astype(np.int32))
    print(f"{name:7s} mean test traffic: normal {S[:, T0:T1].mean():.1f} -> {name} {out[:, T0:T1].mean():.1f}")
