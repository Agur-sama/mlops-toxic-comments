from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)


def classification_metrics(
    y_true: np.ndarray,
    scores: np.ndarray,
    threshold: float = 0.5,
    score_kind: str = "probability",
) -> tuple[dict[str, Any], np.ndarray]:
    if score_kind == "decision":
        predictions = (scores >= threshold).astype(int)
    else:
        predictions = (scores >= threshold).astype(int)
    matrix = confusion_matrix(y_true, predictions, labels=[0, 1])
    metrics = {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "pr_auc": float(average_precision_score(y_true, scores)),
        "threshold": float(threshold),
        "score_kind": score_kind,
        "tn": int(matrix[0, 0]),
        "fp": int(matrix[0, 1]),
        "fn": int(matrix[1, 0]),
        "tp": int(matrix[1, 1]),
    }
    return metrics, predictions


def select_f1_threshold(y_true: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    if len(thresholds) == 0:
        return {"threshold": 0.5, "f1": 0.0, "precision": 0.0, "recall": 0.0}
    f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(
        precision[:-1] + recall[:-1], np.finfo(float).eps
    )
    best = int(np.nanargmax(f1))
    return {
        "threshold": float(thresholds[best]),
        "f1": float(f1[best]),
        "precision": float(precision[best]),
        "recall": float(recall[best]),
    }

