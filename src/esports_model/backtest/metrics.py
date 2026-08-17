"""Probability scoring metrics."""

from __future__ import annotations

import math
from collections.abc import Sequence


def accuracy(labels: Sequence[int], probs: Sequence[float]) -> float:
    if not labels:
        return float("nan")
    hits = sum(1 for label, prob in zip(labels, probs, strict=True) if int(prob >= 0.5) == label)
    return hits / len(labels)


def log_loss(labels: Sequence[int], probs: Sequence[float]) -> float:
    if not labels:
        return float("nan")
    total = 0.0
    for label, prob in zip(labels, probs, strict=True):
        clipped = min(max(prob, 1e-12), 1.0 - 1e-12)
        total += -(label * math.log(clipped) + (1 - label) * math.log(1.0 - clipped))
    return total / len(labels)


def brier(labels: Sequence[int], probs: Sequence[float]) -> float:
    if not labels:
        return float("nan")
    return sum((prob - label) ** 2 for label, prob in zip(labels, probs, strict=True)) / len(
        labels
    )


def calibration_curve(
    labels: Sequence[int],
    probs: Sequence[float],
    *,
    bins: int = 10,
) -> list[dict[str, float]]:
    buckets: list[list[tuple[int, float]]] = [[] for _ in range(bins)]
    for label, prob in zip(labels, probs, strict=True):
        index = min(bins - 1, max(0, int(prob * bins)))
        buckets[index].append((label, prob))
    curve: list[dict[str, float]] = []
    for index, bucket in enumerate(buckets):
        if not bucket:
            continue
        mean_p = sum(prob for _label, prob in bucket) / len(bucket)
        mean_y = sum(label for label, _prob in bucket) / len(bucket)
        curve.append(
            {
                "bin": index,
                "n": float(len(bucket)),
                "mean_predicted": mean_p,
                "empirical_rate": mean_y,
            }
        )
    return curve


def summarize(name: str, labels: Sequence[int], probs: Sequence[float]) -> dict[str, object]:
    return {
        "name": name,
        "n": len(labels),
        "accuracy": accuracy(labels, probs),
        "log_loss": log_loss(labels, probs),
        "brier": brier(labels, probs),
        "calibration": calibration_curve(labels, probs),
    }
