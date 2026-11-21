from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from toxicity.bert import run_bert_training
from toxicity.classical import run_classical_experiments
from toxicity.config import get_paths, load_config, save_environment, set_global_seed
from toxicity.data import create_or_load_splits, load_train, remove_duplicate_texts
from toxicity.eda import run_eda
from toxicity.error_analysis import build_error_analysis
from toxicity.plots import plot_bert_history, plot_results


def prepare(config: dict, attempt_download: bool, force_split: bool = False):
    paths = get_paths(config)
    frame, source = load_train(paths.raw_dir, attempt_download=attempt_download)
    clean, removed = remove_duplicate_texts(frame)
    splits = create_or_load_splits(
        clean,
        paths.processed_dir,
        seed=int(config["project"]["seed"]),
        force=force_split,
    )
    (paths.results_dir / "data_preparation.json").write_text(
        json.dumps(
            {
                "source_rows": len(frame),
                "deduplicated_rows": len(clean),
                "removed_duplicate_texts": removed,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return paths, frame, source, splits


def combine_results(paths) -> pd.DataFrame:
    files = [paths.results_dir / "classical_results.csv"]
    files += sorted(paths.results_dir.glob("distilbert*_results.csv"))
    available = [pd.read_csv(p) for p in files if p.exists()]
    if not available:
        raise FileNotFoundError("No completed experiment result files were found")
    combined = pd.concat(available, ignore_index=True)
    combined.to_csv(paths.results_dir / "all_results.csv", index=False)
    return combined


def run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    set_global_seed(int(config["project"]["seed"]))
    paths = get_paths(config)
    save_environment(paths.results_dir / "environment.json")

    if args.command == "report":
        from toxicity.report import build_report

        build_report(config, paths)
        return 0

    if args.command == "validate":
        from toxicity.validation import validate_project

        validate_project(ROOT)
        return 0

    paths, frame, source, splits = prepare(config, args.download, args.force_split)
    if args.command in {"all", "eda"}:
        run_eda(frame, source, paths.figures_dir, paths.results_dir)
    if args.command in {"all", "classical"}:
        run_classical_experiments(
            splits,
            config,
            paths.results_dir,
            paths.models_dir,
            paths.predictions_dir,
            quick=args.quick,
        )
    if args.command == "bert" or (args.command == "all" and args.bert):
        run_bert_training(
            splits,
            config,
            paths.results_dir,
            paths.models_dir,
            paths.predictions_dir,
            variant_name=args.bert_variant,
        )
        plot_bert_history(paths.results_dir / f"{args.bert_variant}_history.json", paths.figures_dir)
    if args.command in {"all", "classical", "bert"} and not args.quick:
        try:
            results = combine_results(paths)
            plot_results(results, paths.predictions_dir, paths.figures_dir)
            for model in ("tfidf_logistic_regression", "tfidf_linear_svm", args.bert_variant):
                pred = paths.predictions_dir / f"{model}_test_predictions.csv"
                if pred.exists():
                    build_error_analysis(
                        pred,
                        paths.results_dir / f"error_analysis_{model}.csv",
                        extra_labels=frame,
                    )
        except FileNotFoundError:
            pass
    if args.command == "all" and not args.quick:
        from toxicity.report import build_report

        build_report(config, paths)
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Jigsaw toxic comment classification coursework")
    p.add_argument("command", nargs="?", choices=["all", "eda", "classical", "bert", "report", "validate"], default="all")
    p.add_argument("--config", default=str(ROOT / "config/default.yaml"))
    p.add_argument("--download", action="store_true", help="Attempt official KaggleHub download")
    p.add_argument("--force-split", action="store_true", help="Recreate saved split manifest")
    p.add_argument("--quick", action="store_true", help="Demonstration-only small stratified sample")
    p.add_argument("--bert", action="store_true", help="Include DistilBERT when command is all")
    p.add_argument("--bert-variant", default="distilbert")
    return p


if __name__ == "__main__":
    raise SystemExit(run(parser().parse_args()))

