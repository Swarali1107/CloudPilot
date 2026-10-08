import argparse
import numpy as np
import pandas as pd


def load(path, h):
    d = pd.read_parquet(path)
    d = d[d.h == h].copy()
    L = d.L.fillna(d.L_static)
    U = d.U.fillna(d.U_static)
    d["w"] = (U - L) / np.maximum(d.p50.abs(), 1.0)   # known at forecast time
    d["e_last"] = (d.y - d.y0).abs()
    d["e_chr"] = (d.y - d.p50).abs()
    return d


def nmae(d, err):
    """mean over functions of (MAE / mean actual)"""
    g = pd.DataFrame({"f": d.function.values, "e": err, "y": d.y.values}).groupby("f")
    return float((g.e.mean() / g.y.mean()).mean())


def pick_tau(cal):
    cands = [0.0] + list(np.unique(np.quantile(cal.w.dropna(), np.linspace(0.05, 0.95, 19)))) + [np.inf]
    best = None
    for tau in cands:
        s = nmae(cal, np.where(cal.w <= tau, cal.e_chr, cal.e_last))
        if best is None or s < best[1]:
            best = (tau, s)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("store")
    ap.add_argument("--h", type=int, default=3)
    ap.add_argument("--out", default="results/gate_scores.csv")
    a = ap.parse_args()

    d = load(a.store, a.h)
    print("segments:", d.segment.unique().tolist(), "| functions:", d.function.nunique())
    cal = d[d.segment == "calibration"]
    test = d[d.segment == "test"]
    assert len(cal) and len(test), "need 'calibration' and 'test' segments"

    tau, s_cal = pick_tau(cal)
    print(f"tau chosen on calibration segment: {tau:.3f}  (score {s_cal:.4f})")

    rows = []
    for f, g in test.groupby("function"):
        use = g.w <= tau
        e_gate = np.where(use, g.e_chr, g.e_last)
        m = g.y.mean()
        rows.append(dict(
            function=f[:8],
            last_minute=g.e_last.mean() / m,
            chronos2=g.e_chr.mean() / m,
            gated=e_gate.mean() / m,
            best_of_two=min(g.e_last.mean(), g.e_chr.mean()) / m,
            pct_chronos_used=100 * use.mean(),
        ))
    r = pd.DataFrame(rows).set_index("function")
    r.loc["MEAN"] = r.mean()
    pd.options.display.float_format = "{:.3f}".format
    print(f"\nTEST segment, h={a.h}, error = MAE / mean actual (lower is better)\n")
    print(r)
    r.to_csv(a.out)
    print("\nsaved", a.out)


if __name__ == "__main__":
    main()
