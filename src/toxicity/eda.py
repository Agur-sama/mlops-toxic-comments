from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .data import LABEL_COLUMNS, inspect_dataset

WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.IGNORECASE)
EDA_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "it", "that",
    "this", "for", "on", "with", "as", "be", "are", "was", "were", "you",
    "i", "he", "she", "they", "we", "at", "by", "from", "have", "has",
}


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _tokens(series: pd.Series, limit: int = 2_000_000) -> Counter[str]:
    counts: Counter[str] = Counter()
    seen = 0
    for text in series.astype(str):
        words = [w.lower() for w in WORD_RE.findall(text)]
        words = [w for w in words if w not in EDA_STOPWORDS and len(w) > 2]
        counts.update(words)
        seen += len(words)
        if seen >= limit:
            break
    return counts


def _word_bar(counts: Counter[str], title: str, path: Path) -> None:
    data = pd.DataFrame(counts.most_common(20), columns=["word", "count"]).sort_values("count")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(data["word"], data["count"], color="#365f91")
    ax.set_title(title)
    ax.set_xlabel("Частота")
    ax.set_ylabel("Слово")
    ax.grid(axis="x", alpha=0.2)
    _save(fig, path)


def run_eda(frame: pd.DataFrame, source_path: Path, figures_dir: Path, results_dir: Path) -> dict:
    sns.set_theme(style="whitegrid", context="notebook")
    work = frame.copy()
    work["char_length"] = work["comment_text"].astype(str).str.len()
    work["word_length"] = work["comment_text"].astype(str).str.split().str.len()
    summary = inspect_dataset(work, source_path)

    class_counts = work["toxic"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(["Нетоксичные", "Токсичные"], class_counts.values, color=["#4c78a8", "#e45756"])
    ax.bar_label(bars, fmt="%d")
    ax.set_title("Распределение целевого класса")
    ax.set_ylabel("Количество комментариев")
    _save(fig, figures_dir / "eda_target_distribution.png")

    label_counts = work[LABEL_COLUMNS].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(x=label_counts.index, y=label_counts.values, ax=ax, color="#365f91")
    ax.set_title("Распределение шести категорий токсичности")
    ax.set_xlabel("Категория")
    ax.set_ylabel("Количество положительных меток")
    ax.tick_params(axis="x", rotation=25)
    _save(fig, figures_dir / "eda_all_labels.png")

    for column, xlabel, filename, cap in (
        ("char_length", "Количество символов", "eda_length_characters.png", 5000),
        ("word_length", "Количество слов", "eda_length_words.png", 1000),
    ):
        fig, ax = plt.subplots(figsize=(9, 5))
        sns.histplot(work[column].clip(upper=cap), bins=60, ax=ax, color="#4c78a8")
        ax.set_title(f"Распределение длины комментариев: {xlabel.lower()}")
        ax.set_xlabel(f"{xlabel} (значения выше {cap} ограничены на графике)")
        ax.set_ylabel("Количество комментариев")
        _save(fig, figures_dir / filename)

    sample = work.sample(min(len(work), 50_000), random_state=42)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    sns.boxplot(data=sample, x="toxic", y=sample["char_length"].clip(upper=5000), ax=axes[0])
    sns.boxplot(data=sample, x="toxic", y=sample["word_length"].clip(upper=1000), ax=axes[1])
    axes[0].set(title="Длина в символах по классу", xlabel="Toxic", ylabel="Символы")
    axes[1].set(title="Длина в словах по классу", xlabel="Toxic", ylabel="Слова")
    _save(fig, figures_dir / "eda_length_by_class.png")

    toxic_words = _tokens(work.loc[work["toxic"] == 1, "comment_text"])
    neutral_words = _tokens(work.loc[work["toxic"] == 0, "comment_text"])
    _word_bar(toxic_words, "Частые слова в токсичных комментариях", figures_dir / "eda_words_toxic.png")
    _word_bar(neutral_words, "Частые слова в нетоксичных комментариях", figures_dir / "eda_words_nontoxic.png")
    combined = toxic_words + neutral_words
    _word_bar(combined, "Частые содержательные слова во всём корпусе", figures_dir / "eda_words_all.png")

    cooccurrence = work[LABEL_COLUMNS].T.dot(work[LABEL_COLUMNS])
    fig, ax = plt.subplots(figsize=(8, 7))
    sns.heatmap(cooccurrence, annot=True, fmt="d", cmap="Blues", ax=ax)
    ax.set_title("Совместная встречаемость меток токсичности")
    _save(fig, figures_dir / "eda_label_cooccurrence.png")

    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "eda_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pd.DataFrame(
        [(word, count, "toxic") for word, count in toxic_words.most_common(100)]
        + [(word, count, "non_toxic") for word, count in neutral_words.most_common(100)],
        columns=["word", "count", "class"],
    ).to_csv(results_dir / "word_frequencies.csv", index=False)
    return summary

