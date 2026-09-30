"""Score every function and print candidate cohorts.
Usage: python -m cloudpilot.trace.select_cohort data/processed
"""
import sys, numpy as np, pandas as pd
from pathlib import Path

D = Path(sys.argv[1])
X = np.load(D / "series.npy").astype(np.float64)          # (functions, 20160)
meta = pd.read_csv(D / "meta.csv")
n = X.shape[0]

def rowcorr(a, b):                                          # correlation per row
    a = a - a.mean(1, keepdims=True); b = b - b.mean(1, keepdims=True)
    return (a * b).sum(1) / (np.sqrt((a**2).sum(1) * (b**2).sum(1)) + 1e-9)

bins = X.reshape(n, 14 * 96, 15).mean(axis=2)               # 15-minute averages
days = bins.reshape(n, 14, 96)
daily_ac = np.mean([rowcorr(days[:, d], days[:, d + 1]) for d in range(13)], axis=0)
ac1 = rowcorr(X[:, :-1], X[:, 1:])                          # 1-minute autocorrelation
med = np.median(X, axis=1)

m = meta.copy()
m["mean"] = X.mean(1)
m["zero_frac"] = (X == 0).mean(1)
m["daily_ac"] = daily_ac
m["ac1"] = ac1
m["cv15"] = bins.std(1) / (bins.mean(1) + 1e-9)
m["peak_over_mean"] = X.max(1) / (X.mean(1) + 1e-9)
m.to_csv(D / "function_scores.csv", index=False)

print("\nFunctions per trigger:\n", m.Trigger.value_counts().to_string())
print("\nMedian scores per trigger:")
print(m.groupby("Trigger")[["mean", "zero_frac", "daily_ac", "ac1", "cv15"]].median().round(2).to_string())

cols = ["key", "Trigger", "mean", "zero_frac", "daily_ac", "ac1", "cv15", "peak_over_mean"]
real = m[m.Trigger != "timer"]                              # timers are cron jobs, not user demand
A = real[(real.zero_frac < 0.02) & (real.daily_ac > 0.8) & (real.cv15.between(0.3, 1.2)) & (real.ac1 > 0.9) & (real.peak_over_mean < 6) & (real["mean"] > 100)].sort_values("daily_ac", ascending=False)
B = real[(real.zero_frac < 0.10) & (real.cv15 > 0.8) & (real.daily_ac < 0.3) & (real["mean"] > 50)].sort_values("cv15", ascending=False)
print(f"\nGROUP A (daily pattern, non-timer): {len(A)} candidates\n", A[cols].head(8).round(2).to_string(index=False))
print(f"\nGROUP B (bursty, weak daily pattern): {len(B)} candidates\n", B[cols].head(6).round(2).to_string(index=False))
for t in ["queue", "event", "storage", "orchestration"]:
    C = real[(real.Trigger == t) & (real.zero_frac < 0.10) & (real["mean"] > 30)].sort_values("daily_ac", ascending=False)
    print(f"\nGROUP C candidates, trigger={t}: {len(C)}\n", C[cols].head(3).round(2).to_string(index=False))
