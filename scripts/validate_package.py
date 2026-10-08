"""Validate the portable skill package using Python's standard library."""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "plain-korean"
sys.path.insert(0, str(SKILL / "scripts"))
import contribute
import examples


def check():
    errors = []
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    if not re.match(r"\A---\nname: plain-korean\ndescription: .+\nmetadata:\n  version: \"\d+\.\d+\.\d+\"\n---\n", skill):
        errors.append("invalid skill frontmatter")
    required = ["LICENSE", "README.md", "CONTRIBUTING.md", "PRIVACY.md", "docs/design.md",
                "skills/plain-korean/agents/openai.yaml", "skills/plain-korean/references/contributing.md"]
    for name in required:
        if not (ROOT / name).is_file():
            errors.append("missing " + name)
    ids = set()
    records = examples.load()
    for row in records:
        rid = row.get("id", "")
        if not re.fullmatch(r"P\d{3}", rid) or rid in ids:
            errors.append("invalid or duplicate example ID")
        ids.add(rid)
        candidate = {key: value for key, value in row.items() if key != "id"}
        candidate.update(synthetic_examples=True, privacy_reviewed=True)
        try:
            contribute.validate(candidate)
        except contribute.Stop as error:
            errors.append(rid + ": " + str(error))
    if not any(r["before"] == r["after"] for r in records):
        errors.append("missing keep examples")
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", text):
            if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            if not (path.parent / target.split("#")[0]).is_file():
                errors.append(str(path.relative_to(ROOT)) + ": broken link " + target)
    for path in SKILL.rglob("*"):
        if path.is_symlink():
            errors.append("symlinks are not part of the portable package")
        if path.suffix in {".md", ".yaml", ".jsonl"}:
            text = path.read_text(encoding="utf-8")
            if re.search(r"[A-Za-z]:[\\/]|/(?:Users|home)/[^\s/]+/|\\\\[A-Za-z0-9_-]+\\", text):
                errors.append("absolute personal/environment path in " + path.name)
    return errors


def main():
    errors = check()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("OK: portable skill, examples, keep cases and local Markdown links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
