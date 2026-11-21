from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

PROFANITY_HINTS = re.compile(r"\b(fuck|shit|bitch|asshole|damn)\w*\b", re.IGNORECASE)
NEGATION = re.compile(r"\b(no|not|never|isn't|aren't|don't|doesn't|didn't)\b", re.IGNORECASE)
MASKED = re.compile(r"\b\w*[*@$!0-9]{1,}\w*\b")
SARCASM = re.compile(r"\b(yeah right|sure|great job|brilliant|genius)\b", re.IGNORECASE)


def _categories(text: str, word_count: int) -> list[str]:
    categories: list[str] = []
    if SARCASM.search(text):
        categories.append("possible_sarcasm")
    if NEGATION.search(text):
        categories.append("negation")
    if PROFANITY_HINTS.search(text):
        categories.append("profanity")
    if MASKED.search(text):
        categories.append("masked_word")
    if word_count <= 5:
        categories.append("short")
    if word_count >= 150:
        categories.append("long")
    if not categories:
        categories.append("implicit_or_other")
    return categories


def build_error_analysis(
    predictions_path: Path,
    output_path: Path,
    extra_labels: pd.DataFrame | None = None,
    max_per_type: int = 25,
) -> pd.DataFrame:
    frame = pd.read_csv(predictions_path)
    errors = frame[frame["toxic"] != frame["prediction"]].copy()
    errors["error_type"] = np.where(errors["prediction"] == 1, "false_positive", "false_negative")
    errors["word_count"] = errors["comment_text"].astype(str).str.split().str.len()
    errors["heuristic_categories"] = errors.apply(
        lambda row: ";".join(_categories(str(row["comment_text"]), int(row["word_count"]))), axis=1
    )
    errors["excerpt"] = errors["comment_text"].astype(str).str.replace(r"\s+", " ", regex=True).str.slice(0, 350)
    errors["reason_note"] = errors["heuristic_categories"].map(
        lambda x: "Категория сформирована наблюдаемым текстовым признаком; требует ручной интерпретации. " + x
    )
    if extra_labels is not None:
        label_cols = [c for c in ("severe_toxic", "obscene", "threat", "insult", "identity_hate") if c in extra_labels]
        errors = errors.merge(extra_labels[["id", *label_cols]], on="id", how="left")
    selected = (
        errors.sort_values("score", ascending=False)
        .groupby("error_type", group_keys=False)
        .head(max_per_type)
        .reset_index(drop=True)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(output_path, index=False)
    return selected

