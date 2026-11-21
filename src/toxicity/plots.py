from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import precision_recall_curve, roc_curve


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_results(results: pd.DataFrame, predictions_dir: Path, figures_dir: Path) -> None:
    sns.set_theme(style="whitegrid")
    primary_names = ["bow_multinomial_nb", "tfidf_logistic_regression", "tfidf_linear_svm", "distilbert"]
    primary = results[results["model"].isin(primary_names)].copy()
    if primary.empty:
        return

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=primary, x="model", y="test_f1", ax=ax, color="#365f91")
    ax.set(title="Сравнение F1-score моделей", xlabel="Модель", ylabel="F1-score", ylim=(0, 1))
    ax.tick_params(axis="x", rotation=20)
    _save(fig, figures_dir / "results_f1_comparison.png")

    melted = primary.melt(id_vars="model", value_vars=["test_precision", "test_recall"], var_name="metric", value_name="value")
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=melted, x="model", y="value", hue="metric", ax=ax)
    ax.set(title="Precision и Recall на тестовой выборке", xlabel="Модель", ylabel="Значение", ylim=(0, 1))
    ax.tick_params(axis="x", rotation=20)
    _save(fig, figures_dir / "results_precision_recall.png")

    fig_roc, ax_roc = plt.subplots(figsize=(7, 6))
    fig_pr, ax_pr = plt.subplots(figsize=(7, 6))
    for model in primary["model"]:
        path = predictions_dir / f"{model}_test_predictions.csv"
        if not path.exists():
            continue
        pred = pd.read_csv(path)
        fpr, tpr, _ = roc_curve(pred["toxic"], pred["score"])
        precision, recall, _ = precision_recall_curve(pred["toxic"], pred["score"])
        row = primary.loc[primary["model"] == model].iloc[0]
        ax_roc.plot(fpr, tpr, label=f"{model} (AUC={row['test_roc_auc']:.3f})")
        ax_pr.plot(recall, precision, label=f"{model} (AP={row['test_pr_auc']:.3f})")
    ax_roc.plot([0, 1], [0, 1], "--", color="gray", linewidth=1)
    ax_roc.set(title="ROC-кривые", xlabel="False Positive Rate", ylabel="True Positive Rate")
    ax_roc.legend(fontsize=8)
    ax_pr.set(title="Precision-Recall-кривые", xlabel="Recall", ylabel="Precision")
    ax_pr.legend(fontsize=8)
    _save(fig_roc, figures_dir / "results_roc_curves.png")
    _save(fig_pr, figures_dir / "results_pr_curves.png")

    for _, row in primary.iterrows():
        matrix = np.array([[row["test_tn"], row["test_fp"]], [row["test_fn"], row["test_tp"]]])
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.heatmap(matrix, annot=True, fmt=".0f", cmap="Blues", cbar=False, ax=ax)
        ax.set(title=f"Матрица ошибок: {row['model']}", xlabel="Предсказание", ylabel="Истинный класс")
        ax.set_xticklabels(["0", "1"])
        ax.set_yticklabels(["0", "1"], rotation=0)
        _save(fig, figures_dir / f"confusion_{row['model']}.png")

    c_rows = results[results["model"].str.contains(r"logreg_c_|svm_c_", regex=True)].copy()
    if not c_rows.empty:
        def family(name: str) -> str:
            return "Logistic Regression" if "logreg" in name else "Linear SVM"
        c_rows["family"] = c_rows["model"].map(family)
        c_rows["C"] = c_rows["parameters"].map(lambda x: float(json.loads(x)["C"]))
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.lineplot(data=c_rows, x="C", y="validation_f1", hue="family", marker="o", ax=ax)
        ax.set(title="Влияние параметра C на F1 validation", ylabel="F1-score")
        _save(fig, figures_dir / "results_c_influence.png")

    prep = results[results["model"].str.startswith("tfidf_logreg_preprocess_") | (results["model"] == "tfidf_logistic_regression")].copy()
    if not prep.empty:
        fig, ax = plt.subplots(figsize=(7, 5))
        sns.barplot(data=prep, x="preprocessing", y="validation_f1", ax=ax, color="#4c78a8")
        ax.set(title="Влияние предобработки на F1 validation", xlabel="Вариант", ylabel="F1-score", ylim=(0, 1))
        _save(fig, figures_dir / "results_preprocessing_influence.png")


def plot_bert_history(history_path: Path, figures_dir: Path) -> None:
    if not history_path.exists():
        return
    history = json.loads(history_path.read_text(encoding="utf-8"))
    train = [(x["epoch"], x["loss"]) for x in history if "loss" in x and "eval_loss" not in x and x.get("epoch")]
    valid = [(x["epoch"], x["eval_loss"]) for x in history if "eval_loss" in x and x.get("epoch")]
    if not train and not valid:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    if train:
        ax.plot(*zip(*train, strict=False), label="Train loss")
    if valid:
        ax.plot(*zip(*valid, strict=False), label="Validation loss", marker="o")
    ax.set(title="Обучение DistilBERT", xlabel="Эпоха", ylabel="Loss")
    ax.legend()
    _save(fig, figures_dir / "bert_learning_curves.png")

