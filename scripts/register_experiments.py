from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import mlflow

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from toxicity.config import load_config

SELECTED_RUNS = (
    ("bow_multinomial_nb", "jigsaw-minimal-v1"),
    ("tfidf_logistic_regression", "jigsaw-minimal-v1"),
    ("tfidf_logreg_preprocess_standard", "jigsaw-standard-v2"),
)


def git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "uncommitted"


def make_store_portable(store: Path) -> None:
    """Remove author-machine prefixes from MLflow's generated YAML metadata."""
    prefix = f"{ROOT}{os.sep}"
    for path in store.rglob("*"):
        if not path.is_file() or path.suffix == ".joblib":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text = text.replace(prefix, "")
        text = text.replace("maksim", "student")
        path.write_text(text, encoding="utf-8")


def main() -> None:
    config = load_config(ROOT / "config" / "default.yaml")
    train_config = config["train"]
    tracking_uri = os.getenv(
        "MLFLOW_TRACKING_URI", str(ROOT / train_config["tracking_uri"])
    )
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(train_config["experiment_name"])

    source_path = ROOT / "artifacts" / "results" / "classical_results.json"
    all_results = json.loads(source_path.read_text(encoding="utf-8"))
    by_name = {item["model"]: item for item in all_results}
    metadata_path = ROOT / "artifacts" / "models" / "model_metadata.json"
    model_path = ROOT / "artifacts" / "models" / "tfidf_logreg_preprocess_standard.joblib"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    code_sha = git_sha()
    registry: list[dict[str, object]] = []

    for model_name, data_version in SELECTED_RUNS:
        result = by_name[model_name]
        with mlflow.start_run(run_name=model_name) as run:
            mlflow.set_tags(
                {
                    "code.git_sha": code_sha,
                    "data.version": data_version,
                    "split.manifest_sha256": metadata["split_manifest_sha256"],
                    "source.dataset_sha256": metadata["source_dataset_sha256"],
                    "project.stage": "coursework-final",
                }
            )
            params = json.loads(result["parameters"])
            params.update(
                {
                    "model": model_name,
                    "preprocessing": result["preprocessing"],
                    "vectorizer": result["vectorizer"],
                    "seed": config["project"]["seed"],
                }
            )
            mlflow.log_params(params)
            metrics = {
                f"validation_{name}": float(value)
                for name, value in result["validation"].items()
                if isinstance(value, int | float)
            }
            metrics.update(
                {
                    f"test_{name}": float(value)
                    for name, value in result["test"].items()
                    if isinstance(value, int | float)
                }
            )
            metrics["fit_seconds"] = float(result["fit_seconds"])
            mlflow.log_metrics(metrics)
            mlflow.log_artifact(str(metadata_path), artifact_path="metadata")
            if model_name == "tfidf_logreg_preprocess_standard":
                mlflow.log_artifact(str(model_path), artifact_path="model")
            registry.append(
                {
                    "run_id": run.info.run_id,
                    "run_name": model_name,
                    "data_version": data_version,
                    "git_sha": code_sha,
                    "validation_f1": result["validation"]["f1"],
                    "test_f1": result["test"]["f1"],
                    "selected": model_name == "tfidf_logreg_preprocess_standard",
                }
            )

    output = ROOT / "artifacts" / "results" / "mlflow_runs.json"
    output.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    if tracking_uri == str(ROOT / train_config["tracking_uri"]):
        make_store_portable(ROOT / train_config["tracking_uri"])
    print(f"Registered {len(registry)} runs in {tracking_uri}")


if __name__ == "__main__":
    main()
