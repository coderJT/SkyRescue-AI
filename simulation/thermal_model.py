"""
Lightweight thermal human detection model.

This model scores thermal signatures and returns a human-likelihood probability.
It is intentionally simple and dependency-free so it can run in real-time.
"""

import math


class ThermalHumanDetectionModel:
    """Simple logistic model for human-vs-nonhuman thermal classification."""

    def __init__(self, threshold: float = 0.60):
        self.threshold = threshold

    @staticmethod
    def _sigmoid(x: float) -> float:
        if x >= 0:
            z = math.exp(-x)
            return 1.0 / (1.0 + z)
        z = math.exp(x)
        return z / (1.0 + z)

    def predict_proba(self, signature: dict) -> float:
        """
        Return probability that the signature is a human.

        Expected keys:
          - apparent_temp_c: float
          - shape_score: float in [0, 1]
          - motion_score: float in [0, 1]
          - flicker_score: float in [0, 1]
          - distance_u: float
        """
        temp = float(signature.get("apparent_temp_c", 25.0))
        shape = float(signature.get("shape_score", 0.0))
        motion = float(signature.get("motion_score", 0.0))
        flicker = float(signature.get("flicker_score", 0.0))
        distance = float(signature.get("distance_u", 0.0))

        # Tuned weights: human signatures are warm, coherent in shape,
        # show moderate motion, and have lower flame-like flicker.
        logit = (
            -8.20
            + 0.18 * temp
            + 2.40 * shape
            + 1.80 * motion
            - 2.20 * flicker
            - 0.05 * distance
        )
        return self._sigmoid(logit)

    def is_human(self, signature: dict) -> bool:
        return self.predict_proba(signature) >= self.threshold
