from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from toxicity.classical import _tfidf
from toxicity.config import get_paths, load_config, set_global_seed
from toxicity.data import create_or_load_splits, load_train, remove_duplicate_texts
from toxicity.metrics import classification_metrics, select_f1_threshold
from toxicity.preprocessing import get_preprocessor


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    config = load_config(ROOT / "config" / "default.yaml")
    set_global_seed(int(config["project"]["seed"]))
    paths = get_paths(config)
    frame, source = load_train(paths.raw_dir)
    clean, _ = remove_duplicate_texts(frame)
    splits = create_or_load_splits(clean, paths.processed_dir, seed=42)
    cfg = config["classical"]
    vectorizer_params = {
        "max_features": int(cfg["max_features"]),
        "min_df": int(cfg["min_df"]),
        "ngram_range": tuple(cfg["ngram_range"]),
        "sublinear_tf": bool(cfg["sublinear_tf"]),
    }
    model = Pipeline(
        [
            ("vectorizer", _tfidf(get_preprocessor("standard"), **vectorizer_params)),
            (
                "classifier",
                LogisticRegression(
                    C=float(cfg["logistic_c"]),
                    max_iter=int(cfg["max_iter"]),
                    class_weight="balanced",
                    solver="liblinear",
                    random_state=42,
                ),
            ),
        ]
    )
    started = time.perf_counter()
    model.fit(splits["train"]["comment_text"], splits["train"]["toxic"])
    fit_seconds = time.perf_counter() - started
    validation_scores = model.predict_proba(splits["validation"]["comment_text"])[:, 1]
    threshold = float(
        select_f1_threshold(
            splits["validation"]["toxic"].to_numpy(), validation_scores
        )["threshold"]
    )
    validation, _ = classification_metrics(
        splits["validation"]["toxic"].to_numpy(),
        validation_scores,
        threshold,
        "probability",
    )
    test_scores = model.predict_proba(splits["test"]["comment_text"])[:, 1]
    test, _ = classification_metrics(
        splits["test"]["toxic"].to_numpy(), test_scores, threshold, "probability"
    )

    model_path = paths.models_dir / "tfidf_logreg_preprocess_standard.joblib"
    joblib.dump(model, model_path, compress=3)
    metadata_path = paths.models_dir / "model_metadata.json"
    metadata = {
        "model_name": "tfidf_logreg_preprocess_standard",
        "model_version": "toxicity-tfidf-logreg-v1.0.0",
        "artifact_sha256": sha256_file(model_path),
        "data_version": "jigsaw-standard-v2",
        "preprocessing": "standard",
        "decision_threshold": threshold,
        "selection_metric": "validation_f1",
        "validation_f1": validation["f1"],
        "test_f1": test["f1"],
        "test_precision": test["precision"],
        "test_recall": test["recall"],
        "test_roc_auc": test["roc_auc"],
        "test_pr_auc": test["pr_auc"],
        "training_seed": 42,
        "source_dataset_sha256": sha256_file(source),
        "split_manifest_sha256": sha256_file(paths.processed_dir / "split_manifest.csv"),
        "fit_seconds": fit_seconds,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (paths.results_dir / "final_model_metrics.json").write_text(
        json.dumps(
            {"validation": validation, "test": test, "fit_seconds": fit_seconds},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
