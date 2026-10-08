"""Write the 8 cohort functions to one tiny file (about 1 MB) that is easy to upload to Colab.
Usage: python -m cloudpilot.trace.export_cohort      -> data/processed/cohort.npz
"""
import numpy as np, pandas as pd
from pathlib import Path
from cloudpilot.forecast.eval_baselines import COHORT

PROC = Path("data/processed")
X = np.load(PROC / "series.npy")
meta = pd.read_csv(PROC / "meta.csv")
idx = []
for k in COHORT:
    hit = meta.index[meta["key"] == k]
    if len(hit) == 0:
        raise SystemExit(f"key not in data: {k}")
    idx.append(int(hit[0]))
np.savez_compressed(PROC / "cohort.npz", keys=np.array(COHORT), series=X[idx].astype(np.int32))
print("saved", PROC / "cohort.npz", X[idx].shape)
