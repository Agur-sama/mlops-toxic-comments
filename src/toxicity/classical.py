from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from .metrics import classification_metrics, select_f1_threshold
from .preprocessing import get_preprocessor


@dataclass
class RunResult:
    model: str
    preprocessing: str
    vectorizer: str
    parameters: str
    fit_seconds: float
    validation: dict
    test: dict


def _scores(model: Pipeline, texts: pd.Series) -> tuple[np.ndarray, str]:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(texts)[:, 1], "probability"
    return model.decision_function(texts), "decision"


def _evaluate_pipeline(
    name: str,
    pipeline: Pipeline,
    splits: dict[str, pd.DataFrame],
    preprocessing: str,
    vectorizer: str,
    parameters: dict,
    model_dir: Path,
    predictions_dir: Path,
) -> tuple[RunResult, pd.DataFrame]:
    started = time.perf_counter()
    pipeline.fit(splits["train"]["comment_text"], splits["train"]["toxic"])
    fit_seconds = time.perf_counter() - started
    val_scores, kind = _scores(pipeline, splits["validation"]["comment_text"])
    threshold_info = select_f1_threshold(splits["validation"]["toxic"].to_numpy(), val_scores)
    threshold = threshold_info["threshold"]
    val_metrics, _ = classification_metrics(
        splits["validation"]["toxic"].to_numpy(), val_scores, threshold, kind
    )
    test_scores, kind = _scores(pipeline, splits["test"]["comment_text"])
    test_metrics, test_pred = classification_metrics(
        splits["test"]["toxic"].to_numpy(), test_scores, threshold, kind
    )
    model_dir.mkdir(parents=True, exist_ok=True)
    predictions_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_dir / f"{name}.joblib", compress=3)
    predictions = splits["test"][["id", "comment_text", "toxic"]].copy()
    predictions["score"] = test_scores
    predictions["prediction"] = test_pred
    predictions["model"] = name
    predictions.to_csv(predictions_dir / f"{name}_test_predictions.csv", index=False)
    result = RunResult(
        model=name,
        preprocessing=preprocessing,
        vectorizer=vectorizer,
        parameters=json.dumps(parameters, sort_keys=True),
        fit_seconds=fit_seconds,
        validation=val_metrics,
        test=test_metrics,
    )
    return result, predictions


def _tfidf(
    preprocessor: Callable[[str], str],
    max_features: int,
    min_df: int,
    ngram_range: tuple[int, int],
    sublinear_tf: bool,
) -> TfidfVectorizer:
    return TfidfVectorizer(
        preprocessor=preprocessor,
        tokenizer=None,
        token_pattern=r"(?u)\b\w[\w']+\b|[!?]",
        ngram_range=ngram_range,
        min_df=min_df,
        max_features=max_features,
        sublinear_tf=sublinear_tf,
        strip_accents="unicode",
        dtype=np.float32,
    )


def run_classical_experiments(
    splits: dict[str, pd.DataFrame],
    config: dict,
    results_dir: Path,
    models_dir: Path,
    predictions_dir: Path,
    quick: bool = False,
) -> pd.DataFrame:
    cfg = config["classical"]
    if quick:
        sampled: dict[str, pd.DataFrame] = {}
        limits = {"train": 4000, "validation": 1000, "test": 1000}
        for name, part in splits.items():
            n = min(len(part), limits[name])
            toxic = part[part.toxic == 1]
            neutral = part[part.toxic == 0]
            n_toxic = min(len(toxic), max(1, int(round(n * part.toxic.mean()))))
            n_neutral = min(len(neutral), n - n_toxic)
            sampled[name] = pd.concat(
                [toxic.sample(n_toxic, random_state=42), neutral.sample(n_neutral, random_state=42)]
            ).sample(frac=1, random_state=42).reset_index(drop=True)
        splits = sampled

    runs: list[tuple[str, Pipeline, str, str, dict]] = []
    minimal = get_preprocessor("minimal")
    bow_params = {"ngram_range": (1, 2), "min_df": 2, "max_features": cfg["max_features"]}
    runs.append(
        (
            "bow_multinomial_nb",
            Pipeline([
                ("vectorizer", CountVectorizer(preprocessor=minimal, ngram_range=(1, 2), min_df=2, max_features=cfg["max_features"])),
                ("classifier", MultinomialNB(alpha=0.5)),
            ]),
            "minimal",
            "CountVectorizer",
            {**bow_params, "alpha": 0.5},
        )
    )

    base_tfidf = dict(
        max_features=cfg["max_features"],
        min_df=cfg["min_df"],
        ngram_range=tuple(cfg["ngram_range"]),
        sublinear_tf=cfg["sublinear_tf"],
    )
    runs.extend(
        [
            (
                "tfidf_logistic_regression",
                Pipeline([
                    ("vectorizer", _tfidf(minimal, **base_tfidf)),
                    ("classifier", LogisticRegression(C=cfg["logistic_c"], max_iter=cfg["max_iter"], class_weight="balanced", solver="liblinear", random_state=42)),
                ]),
                "minimal",
                "TF-IDF",
                {**base_tfidf, "C": cfg["logistic_c"]},
            ),
            (
                "tfidf_linear_svm",
                Pipeline([
                    ("vectorizer", _tfidf(minimal, **base_tfidf)),
                    ("classifier", LinearSVC(C=cfg["svm_c"], class_weight="balanced", random_state=42)),
                ]),
                "minimal",
                "TF-IDF",
                {**base_tfidf, "C": cfg["svm_c"]},
            ),
        ]
    )

    # Preprocessing ablation with a fixed classifier and vectorizer.
    for variant in ("standard", "extended"):
        processor = get_preprocessor(variant)
        runs.append(
            (
                f"tfidf_logreg_preprocess_{variant}",
                Pipeline([
                    ("vectorizer", _tfidf(processor, **base_tfidf)),
                    ("classifier", LogisticRegression(C=cfg["logistic_c"], max_iter=cfg["max_iter"], class_weight="balanced", solver="liblinear", random_state=42)),
                ]),
                variant,
                "TF-IDF",
                {**base_tfidf, "C": cfg["logistic_c"]},
            )
        )

    # Compact, reproducible hyperparameter study. Test remains untouched for selection.
    for c_value in (0.5, 1.0, 2.0, 4.0):
        if c_value == cfg["logistic_c"]:
            continue
        runs.append(
            (
                f"tfidf_logreg_c_{c_value:g}",
                Pipeline([
                    ("vectorizer", _tfidf(minimal, **base_tfidf)),
                    ("classifier", LogisticRegression(C=c_value, max_iter=cfg["max_iter"], class_weight="balanced", solver="liblinear", random_state=42)),
                ]),
                "minimal",
                "TF-IDF",
                {**base_tfidf, "C": c_value},
            )
        )
    for c_value in (0.25, 0.5, 1.0, 2.0):
        if c_value == cfg["svm_c"]:
            continue
        runs.append(
            (
                f"tfidf_svm_c_{c_value:g}",
                Pipeline([
                    ("vectorizer", _tfidf(minimal, **base_tfidf)),
                    ("classifier", LinearSVC(C=c_value, class_weight="balanced", random_state=42)),
                ]),
                "minimal",
                "TF-IDF",
                {**base_tfidf, "C": c_value},
            )
        )

    tfidf_variants = [
        {**base_tfidf, "ngram_range": (1, 1)},
        {**base_tfidf, "ngram_range": (1, 2)},
        {**base_tfidf, "min_df": 5},
        {**base_tfidf, "max_features": min(cfg["max_features"], 60000)},
        {**base_tfidf, "sublinear_tf": False},
    ]
    seen: set[str] = set()
    for idx, params in enumerate(tfidf_variants, 1):
        key = json.dumps(params, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        runs.append(
            (
                f"tfidf_variant_{idx}",
                Pipeline([
                    ("vectorizer", _tfidf(minimal, **params)),
                    ("classifier", LogisticRegression(C=cfg["logistic_c"], max_iter=cfg["max_iter"], class_weight="balanced", solver="liblinear", random_state=42)),
                ]),
                "minimal",
                "TF-IDF",
                {**params, "C": cfg["logistic_c"]},
            )
        )

    if quick:
        runs = runs[:3]

    results: list[RunResult] = []
    for name, pipeline, prep, vectorizer, params in runs:
        result, _ = _evaluate_pipeline(
            name, pipeline, splits, prep, vectorizer, params, models_dir, predictions_dir
        )
        results.append(result)

    rows: list[dict] = []
    for result in results:
        flat = {
            "model": result.model,
            "preprocessing": result.preprocessing,
            "vectorizer": result.vectorizer,
            "parameters": result.parameters,
            "fit_seconds": result.fit_seconds,
        }
        flat.update({f"validation_{k}": v for k, v in result.validation.items()})
        flat.update({f"test_{k}": v for k, v in result.test.items()})
        rows.append(flat)
    table = pd.DataFrame(rows)
    results_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(results_dir / ("classical_quick_results.csv" if quick else "classical_results.csv"), index=False)
    (results_dir / ("classical_quick_results.json" if quick else "classical_results.json")).write_text(
        json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return table

