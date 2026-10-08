"""Search the bundled synthetic examples. No network or third-party packages."""
import argparse
import json
from pathlib import Path
import sys
import unicodedata

DATA = Path(__file__).resolve().parents[1] / "references" / "examples.jsonl"


def load():
    return [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]


def search(query, limit=5):
    terms = unicodedata.normalize("NFKC", query).casefold().split()
    scored = []
    for row in load():
        text = unicodedata.normalize("NFKC", " ".join(row.values())).casefold()
        score = sum(term in text for term in terms)
        if score or not terms:
            scored.append((score, row))
    return [row for _, row in sorted(scored, key=lambda item: (-item[0], item[1]["id"]))[:limit]]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["search", "show"])
    parser.add_argument("text")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 20:
        parser.error("limit must be between 1 and 20")
    rows = search(args.text, args.limit) if args.command == "search" else [r for r in load() if r["id"] == args.text.upper()]
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
