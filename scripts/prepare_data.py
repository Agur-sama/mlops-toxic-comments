from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from toxicity.config import get_paths, load_config
from toxicity.data import create_or_load_splits, load_train, remove_duplicate_texts


def main() -> None:
    config = load_config(ROOT / "config" / "default.yaml")
    paths = get_paths(config)
    frame, _ = load_train(paths.raw_dir)
    clean, removed = remove_duplicate_texts(frame)
    splits = create_or_load_splits(
        clean,
        paths.processed_dir,
        seed=int(config["project"]["seed"]),
        force=True,
    )
    counts = ", ".join(f"{name}={len(part)}" for name, part in splits.items())
    print(f"Prepared splits ({counts}); removed exact-text duplicates={removed}")


if __name__ == "__main__":
    main()
