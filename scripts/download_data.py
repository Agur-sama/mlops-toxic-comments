from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from toxicity.config import get_paths, load_config
from toxicity.data import download_competition, extract_archives, locate_file

if __name__ == "__main__":
    paths = get_paths(load_config())
    downloaded = download_competition(paths.raw_dir)
    extract_archives(paths.raw_dir)
    train = locate_file(paths.raw_dir, "train.csv")
    if train is None:
        raise SystemExit(f"Download completed at {downloaded}, but train.csv was not found")
    print(f"train.csv: {train.resolve()} ({train.stat().st_size:,} bytes)")

