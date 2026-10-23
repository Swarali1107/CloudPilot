"""Conformal calibration (CQR) of the raw p10-p90 band, so it covers 90% instead of about 80%.

  score = max(p10 - y, y - p90)      how far the actual fell OUTSIDE the band (negative = inside)
  q     = the ceil((n+1)(1-alpha))-th smallest score
  band  = [p10 - q, p90 + q]

Two versions, both written to the store:
  static  : q from the calibration days (9-10) only, one q per (function, horizon)  -> columns q_static, L_static, U_static
  rolling : q from the last WINDOW minutes of RESOLVED scores, refreshed every REFRESH minutes -> columns q, L, U
            A forecast made at minute t for minute t+h is only 'resolved' at t+h, so it is never used before then.

Usage: python -m cloudpilot.calibrate.cqr results/store_chronos_c512.parquet results/store_chronos_c512_cal.parquet
"""
import sys
import numpy as np, pandas as pd


def cqr_q(score, alpha=0.10):
    n = len(score)
    if n == 0:
        return np.nan
    k = min(n, int(np.ceil((n + 1) * (1 - alpha))))
    return float(np.sort(score)[k - 1])


def calibrate(df, alpha=0.10, window=1440, refresh=15, min_scores=60, static_segment="calibration"):
    df = df.copy()
    df["score"] = np.maximum(df.p10 - df.y, df.y - df.p90)
    df["q_static"] = np.nan
    df["q"] = np.nan
    for (fn, h), idx in df.groupby(["function", "h"], sort=False).groups.items():
        g = df.loc[idx].sort_values("t")
        t = g.t.to_numpy()
        resolve = t + h                                     # minute at which the actual becomes known
        sc = g.score.to_numpy()
        order = np.argsort(resolve)
        res_sorted, sc_sorted = resolve[order], sc[order]
        # static: calibration days only
        q_static = cqr_q(g.loc[g.segment == static_segment, "score"].to_numpy(), alpha)
        # rolling: at refresh time r use scores resolved in (r - window, r]; r <= t, so nothing is peeked
        tref = (t // refresh) * refresh
        uniq, inv = np.unique(tref, return_inverse=True)
        qv = np.full(len(uniq), np.nan)
        for j, r in enumerate(uniq):
            hi = np.searchsorted(res_sorted, r, side="right")
            lo = np.searchsorted(res_sorted, r - window, side="right")
            if hi - lo >= min_scores:
                qv[j] = cqr_q(sc_sorted[lo:hi], alpha)
        df.loc[g.index, "q"] = qv[inv]
        df.loc[g.index, "q_static"] = q_static
    df["L_static"] = np.maximum(df.p10 - df.q_static, 0)
    df["U_static"] = df.p90 + df.q_static
    df["L"] = np.maximum(df.p10 - df.q, 0)
    df["U"] = df.p90 + df.q
    return df.drop(columns=["score"])


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    out = calibrate(pd.read_parquet(src))
    out.to_parquet(dst)
    print(f"saved {len(out)} rows -> {dst}   (rolling q missing on {out.q.isna().mean():.1%} of rows: not enough resolved history yet)")
