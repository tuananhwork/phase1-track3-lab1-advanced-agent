from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from urllib.request import urlopen


DEFAULT_URL = "http://curtis.ml.cmu.edu/datasets/hotpot/hotpot_dev_distractor_v1.json"


def _map_difficulty(raw_level: str) -> str:
    level = (raw_level or "").strip().lower()
    if level in {"easy", "medium", "hard"}:
        return level
    if level == "harder":
        return "hard"
    return "medium"


def _convert(item: dict, index: int) -> dict:
    context = []
    for chunk in item.get("context", []):
        if not isinstance(chunk, list) or len(chunk) != 2:
            continue
        title, sentences = chunk
        if isinstance(sentences, list):
            text = " ".join(str(s).strip() for s in sentences if str(s).strip())
        else:
            text = str(sentences).strip()
        context.append({"title": str(title), "text": text})
    return {
        "qid": str(item.get("_id", f"hotpot_{index}")),
        "difficulty": _map_difficulty(str(item.get("level", "medium"))),
        "question": str(item.get("question", "")).strip(),
        "gold_answer": str(item.get("answer", "")).strip(),
        "context": context,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare deterministic HotpotQA sample in lab schema.")
    parser.add_argument("--source-url", default=DEFAULT_URL)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-path", default="data/hotpot_100.json")
    args = parser.parse_args()

    with urlopen(args.source_url, timeout=60) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError("Unexpected source format: expected list of records.")
    if args.sample_size <= 0 or args.sample_size > len(raw):
        raise RuntimeError(f"sample_size must be in [1, {len(raw)}], got {args.sample_size}.")

    rng = random.Random(args.seed)
    sampled = rng.sample(raw, args.sample_size)
    converted = [_convert(item, i) for i, item in enumerate(sampled)]

    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(converted, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(converted)} rows to {out_path}")


if __name__ == "__main__":
    main()
