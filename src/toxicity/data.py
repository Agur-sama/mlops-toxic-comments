from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split

LABEL_COLUMNS = [
    "toxic",
    "severe_toxic",
    "obscene",
    "threat",
    "insult",
    "identity_hate",
]


def download_competition(raw_dir: Path) -> Path:
    """Download through KaggleHub without bypassing Kaggle authentication/rules."""
    import kagglehub

    raw_dir.mkdir(parents=True, exist_ok=True)
    cache_path = Path(
        kagglehub.competition_download(
            "jigsaw-toxic-comment-classification-challenge"
        )
    )
    destination = raw_dir / cache_path.name
    if cache_path.resolve() != destination.resolve():
        if cache_path.is_dir():
            shutil.copytree(cache_path, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(cache_path, destination)
    return destination


def _safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            target = (destination / member.filename).resolve()
            if destination not in target.parents and target != destination:
                raise ValueError(f"Unsafe archive member: {member.filename}")
        zf.extractall(destination)


def extract_archives(raw_dir: Path) -> list[Path]:
    """Extract top-level and nested ZIP files; Kaggle distributes CSVs as ZIPs."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    processed: set[Path] = set()
    while True:
        archives = [p for p in raw_dir.rglob("*.zip") if p not in processed]
        if not archives:
            break
        for archive in archives:
            out_dir = archive.parent / archive.stem
            out_dir.mkdir(parents=True, exist_ok=True)
            _safe_extract(archive, out_dir)
            extracted.append(out_dir)
            processed.add(archive)
    return extracted


def locate_file(raw_dir: Path, filename: str) -> Path | None:
    matches = sorted(raw_dir.rglob(filename), key=lambda p: len(p.parts))
    return matches[0] if matches else None


def load_train(raw_dir: Path, attempt_download: bool = False) -> tuple[pd.DataFrame, Path]:
    extract_archives(raw_dir)
    train_path = locate_file(raw_dir, "train.csv")
    if train_path is None and attempt_download:
        download_competition(raw_dir)
        extract_archives(raw_dir)
        train_path = locate_file(raw_dir, "train.csv")
    if train_path is None:
        raise FileNotFoundError(
            "train.csv not found. Authenticate with `kagglehub login` and run "
            "`python scripts/download_data.py`, or place Kaggle archives in data/raw/."
        )
    frame = pd.read_csv(train_path)
    required = {"id", "comment_text", *LABEL_COLUMNS}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns in {train_path}: {sorted(missing)}")
    return frame, train_path


def inspect_dataset(frame: pd.DataFrame, source_path: Path) -> dict[str, Any]:
    text = frame["comment_text"]
    duplicate_texts = int(text.duplicated(keep=False).sum())
    full_duplicates = int(frame.duplicated().sum())
    label_counts = {col: int(frame[col].sum()) for col in LABEL_COLUMNS}
    return {
        "source_path": str(source_path.resolve()),
        "source_size_bytes": source_path.stat().st_size,
        "rows": int(frame.shape[0]),
        "columns": int(frame.shape[1]),
        "missing_values": {k: int(v) for k, v in frame.isna().sum().items()},
        "full_duplicate_rows": full_duplicates,
        "duplicate_text_rows": duplicate_texts,
        "unique_ids": int(frame["id"].nunique()),
        "unique_texts": int(text.nunique(dropna=False)),
        "label_counts": label_counts,
        "toxic_share": float(frame["toxic"].mean()),
        "non_toxic_share": float(1.0 - frame["toxic"].mean()),
        "character_length": {
            "mean": float(text.str.len().mean()),
            "median": float(text.str.len().median()),
            "p95": float(text.str.len().quantile(0.95)),
            "max": int(text.str.len().max()),
        },
        "word_length": {
            "mean": float(text.str.split().str.len().mean()),
            "median": float(text.str.split().str.len().median()),
            "p95": float(text.str.split().str.len().quantile(0.95)),
            "max": int(text.str.split().str.len().max()),
        },
    }


def remove_duplicate_texts(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Keep one record per exact text to prevent cross-split leakage."""
    before = len(frame)
    clean = frame.drop_duplicates(subset=["comment_text"], keep="first").copy()
    return clean.reset_index(drop=True), before - len(clean)


def create_or_load_splits(
    frame: pd.DataFrame,
    processed_dir: Path,
    seed: int = 42,
    force: bool = False,
) -> dict[str, pd.DataFrame]:
    manifest_path = processed_dir / "split_manifest.csv"
    processed_dir.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists() and not force:
        manifest = pd.read_csv(manifest_path, dtype={"id": str})
        if set(manifest["id"]) != set(frame["id"].astype(str)):
            raise ValueError(
                "Existing split manifest does not match the current deduplicated dataset. "
                "Use --force-split only after verifying the source data."
            )
    else:
        train_df, temp_df = train_test_split(
            frame,
            test_size=0.30,
            stratify=frame["toxic"],
            random_state=seed,
        )
        validation_df, test_df = train_test_split(
            temp_df,
            test_size=0.50,
            stratify=temp_df["toxic"],
            random_state=seed,
        )
        manifest = pd.concat(
            [
                train_df[["id"]].assign(split="train"),
                validation_df[["id"]].assign(split="validation"),
                test_df[["id"]].assign(split="test"),
            ],
            ignore_index=True,
        )
        manifest["id"] = manifest["id"].astype(str)
        manifest.to_csv(manifest_path, index=False)

    keyed = frame.copy()
    keyed["id"] = keyed["id"].astype(str)
    merged = keyed.merge(manifest, on="id", validate="one_to_one")
    splits = {
        name: merged.loc[merged["split"] == name].drop(columns="split").reset_index(drop=True)
        for name in ("train", "validation", "test")
    }
    text_sets = {name: set(part["comment_text"]) for name, part in splits.items()}
    if text_sets["train"] & text_sets["validation"] or text_sets["train"] & text_sets["test"] or text_sets["validation"] & text_sets["test"]:
        raise AssertionError("Exact comment text overlaps between splits")
    split_summary = {
        name: {"rows": len(part), "toxic_share": float(part["toxic"].mean())}
        for name, part in splits.items()
    }
    (processed_dir / "split_summary.json").write_text(
        json.dumps(split_summary, indent=2), encoding="utf-8"
    )
    return splits

