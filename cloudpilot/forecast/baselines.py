"""Three dumb baselines. A real forecaster has to beat these, or it is not worth its cost."""
import numpy as np
from .base import Forecaster

DAY = 1440


class LastValue(Forecaster):
    """Same as the last minute."""
    name = "last_minute"

    def predict(self, history, horizon):
        return np.full(horizon, float(history[-1]))


class SameAsYesterday(Forecaster):
    """Same as the same minute yesterday (needs at least one day of history)."""
    name = "yesterday"

    def predict(self, history, horizon):
        t = len(history) - 1
        idx = np.arange(t + 1, t + horizon + 1) - DAY
        return history[idx].astype(float)


class YesterdayScaled(Forecaster):
    """Yesterday's shape, rescaled by how today compares with yesterday over the last 15 minutes."""
    name = "yesterday_scaled"

    def __init__(self, window=15):
        self.w = window

    def predict(self, history, horizon):
        t = len(history) - 1
        recent = history[t - self.w + 1: t + 1].mean()
        before = history[t - self.w + 1 - DAY: t + 1 - DAY].mean()
        ratio = recent / before if before > 0 else 1.0
        ratio = float(np.clip(ratio, 0.25, 4.0))          # keep one odd minute from exploding
        idx = np.arange(t + 1, t + horizon + 1) - DAY
        return history[idx].astype(float) * ratio
