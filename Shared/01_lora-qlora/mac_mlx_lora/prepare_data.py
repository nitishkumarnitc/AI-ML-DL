"""Export the Guanaco instruction dataset into the train.jsonl / valid.jsonl
format that `mlx_lm.lora` expects (one JSON object per line, with a "text" field).

Usage:
    python prepare_data.py [--out-dir data] [--val-fraction 0.1]
"""

import argparse
import json
import random
from pathlib import Path

from datasets import load_dataset

DATASET_ID = "mlabonne/guanaco-llama2-1k"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="data", help="Directory to write train.jsonl / valid.jsonl into")
    parser.add_argument("--val-fraction", type=float, default=0.1, help="Fraction of examples held out for validation")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataset = load_dataset(DATASET_ID, split="train")
    rows = [{"text": row["text"]} for row in dataset]

    rng = random.Random(args.seed)
    rng.shuffle(rows)

    split_idx = max(1, int(len(rows) * (1 - args.val_fraction)))
    train_rows, val_rows = rows[:split_idx], rows[split_idx:]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_jsonl(out_dir / "train.jsonl", train_rows)
    _write_jsonl(out_dir / "valid.jsonl", val_rows)

    print(f"Wrote {len(train_rows)} training examples -> {out_dir / 'train.jsonl'}")
    print(f"Wrote {len(val_rows)} validation examples -> {out_dir / 'valid.jsonl'}")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
