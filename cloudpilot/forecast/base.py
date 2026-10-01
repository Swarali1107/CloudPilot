"""The contract every forecaster follows (Chronos-2, Prophet, LSTM, baselines).

predict(history, horizon):
  history : 1-D array = demand for minutes 0..t (everything known at time t, nothing later)
  horizon : H
  returns : array of length H = forecast of demand for minutes t+1 .. t+H   (median / p50)

Quantile forecasters (p10/p90) get added in the next step; the p50 contract stays the same.
"""
import numpy as np


class Forecaster:
    name = "base"

    def predict(self, history: np.ndarray, horizon: int) -> np.ndarray:
        raise NotImplementedError
