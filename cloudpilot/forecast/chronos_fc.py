"""Chronos-2 behind the same Forecaster contract (p10 / p50 / p90).

Needs:  pip install "chronos-forecasting>=2.0"   (a GPU makes the big precompute fast; use Colab)
"""
import numpy as np
from .base import Forecaster

QUANTILES = [0.1, 0.5, 0.9]


class ChronosForecaster(Forecaster):
    name = "chronos2"

    def __init__(self, model_id="amazon/chronos-2", device="cuda", context=512, pipeline=None, batch_size=256):
        self.context = context
        self.batch_size = batch_size
        if pipeline is None:
            from chronos import Chronos2Pipeline
            pipeline = Chronos2Pipeline.from_pretrained(model_id, device_map=device)
        self.pipe = pipeline

    def predict_batch(self, histories, horizon):
        """histories: list of 1-D arrays (each = everything known at its origin).
        Returns array (n, horizon, 3) with columns p10, p50, p90 (demand cannot be negative)."""
        inputs = [np.asarray(h[-self.context:], dtype=np.float32) for h in histories]
        q, _ = self.pipe.predict_quantiles(inputs, prediction_length=horizon,
                                           quantile_levels=QUANTILES, batch_size=self.batch_size)
        out = np.stack([np.asarray(x.cpu() if hasattr(x, "cpu") else x)[0] for x in q])   # (n, H, 3)
        out = np.sort(out, axis=-1)          # quantiles must not cross
        return np.maximum(out, 0.0)

    def predict(self, history, horizon):
        return self.predict_batch([history], horizon)[0, :, 1]
