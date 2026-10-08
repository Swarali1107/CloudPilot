import sys
import numpy as np, pandas as pd

C, H = 16.0, 3
d = pd.read_parquet(sys.argv[1] if len(sys.argv) > 1 else "results/store_chronos_c512_cal.parquet")
d = d[d.h == H].copy()
d["L"] = d.L.fillna(d.L_static); d["U"] = d.U.fillna(d.U_static)
d["w"] = (d.U - d.L) / np.maximum(d.p50.abs(), 1.0)
pods = lambda x: np.maximum(np.ceil(np.maximum(x, 0) / C), 1)
d["p50_pods"], d["U_pods"] = pods(d.p50), pods(d.U)
d["s50"] = (d.y > 1.2 * C * d.p50_pods).astype(float)   # severe shortfall with p50 provisioning
d["sU"] = (d.y > 1.2 * C * d.U_pods).astype(float)      # severe shortfall with U provisioning
cal, test = d[d.segment == "calibration"], d[d.segment == "test"]

print("share of minutes upgraded to U | severe-shortfall rate: gate vs random | extra pods vs p50: gate vs random")
for q in [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]:
    r = []
    for f, g in test.groupby("function"):
        if q == 0: use = np.zeros(len(g), bool)
        elif q == 1: use = np.ones(len(g), bool)
        else: use = (g.w > cal[cal.function == f].w.quantile(1 - q)).values
        a = use.mean(); base = g.p50_pods.mean()
        sg = np.where(use, g.sU, g.s50).mean()
        sr = (1 - a) * g.s50.mean() + a * g.sU.mean()
        pg = np.where(use, g.U_pods, g.p50_pods).mean() / base
        pr = ((1 - a) * g.p50_pods.mean() + a * g.U_pods.mean()) / base
        r.append([a, sg, sr, pg, pr])
    a, sg, sr, pg, pr = np.mean(r, axis=0)
    print(f"  q={q:.1f}: upgraded {a:5.1%} | severe {sg:.3f} vs {sr:.3f} | pods x{pg:.2f} vs x{pr:.2f}")
