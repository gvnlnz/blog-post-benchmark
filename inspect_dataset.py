"""Print quick counts for a benchmark dataset."""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", nargs="?", default="data/clusters.json")
    args = ap.parse_args()

    path = Path(args.dataset)
    data = json.load(open(path))
    items_per_sample = [len(sample.get("items", [])) for sample in data]

    print(f"dataset: {path}")
    print(f"samples/posts: {len(data)}")
    print(f"cluster topics/items: {sum(items_per_sample)}")
    if items_per_sample:
        print(f"clusters per post: min={min(items_per_sample)} max={max(items_per_sample)}")
        print(f"clusters per post list: {items_per_sample}")


if __name__ == "__main__":
    main()
