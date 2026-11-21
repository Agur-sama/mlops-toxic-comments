from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from toxicity.config import load_config
from toxicity.data import locate_file


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_train_csv() -> Path:
    root_copy = ROOT / "train.csv"
    if root_copy.is_file():
        return root_copy
    located = locate_file(ROOT / "data" / "raw", "train.csv")
    if located is None:
        raise FileNotFoundError(
            "train.csv not found; run `python scripts/download_data.py` first"
        )
    return located


def build_manifest(variant: str, output: Path) -> dict[str, object]:
    config = load_config(ROOT / "config" / "default.yaml")
    version = config["data_versions"][variant]
    source = find_train_csv()
    preprocessing_path = ROOT / "src" / "toxicity" / "preprocessing.py"
    split_path = ROOT / "data" / "processed" / "split_manifest.csv"
    if not split_path.is_file():
        raise FileNotFoundError("Split manifest is missing; run data preparation first")
    source_sha = sha256_file(source)
    preprocessing_sha = sha256_file(preprocessing_path)
    split_sha = sha256_file(split_path)
    identity = hashlib.sha256(
        f"{source_sha}:{preprocessing_sha}:{split_sha}:{version['preprocessing']}".encode()
    ).hexdigest()
    payload: dict[str, object] = {
        "version_id": version["id"],
        "content_id": identity,
        "source": {
            "name": "Jigsaw Toxic Comment Classification Challenge",
            "competition": "jigsaw-toxic-comment-classification-challenge",
            "file": "train.csv",
            "sha256": source_sha,
            "size_bytes": source.stat().st_size,
        },
        "preprocessing": {
            "variant": version["preprocessing"],
            "implementation": "src/toxicity/preprocessing.py",
            "implementation_sha256": preprocessing_sha,
        },
        "split": {
            "strategy": "stratified 70/15/15 after exact-text deduplication",
            "seed": int(config["project"]["seed"]),
            "manifest": "data/processed/split_manifest.csv",
            "manifest_sha256": split_sha,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("v1", "v2"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_manifest(args.variant, ROOT / args.output)


if __name__ == "__main__":
    main()
