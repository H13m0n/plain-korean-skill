"""Publish synthetic writing patterns after explicit opt-in. Python 3.10+, gh CLI."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

REPO = "H13m0n/plain-korean-skill"
FIELDS = ("pattern", "title", "context", "before", "after", "reason", "keep_when")
PATTERNS = {
    "redundant-caveat", "negative-contrast", "research-narration", "vague-action",
    "attributed-claim", "overprecision", "additive-list", "noun-chain",
    "hypothetical-case", "synonym-cycle", "redundant-conclusion", "condition-result",
    "other",
}
# These checks catch obvious identifiers; semantic review is still required.
BLOCKED = (
    ("address-or-path", r"[@/\\]|\b(?:https?|file|ssh):|\b[A-Za-z]:"),
    ("host-or-file", r"\b[A-Za-z0-9_-]+\.[A-Za-z]{2,}\b"),
    ("network-address", r"\b\d{1,3}(?:\.\d{1,3}){3}\b|(?:[0-9a-f]{0,4}:){2,}[0-9a-f:]*"),
    ("identifier-or-number", r"\d{3,}|\b[0-9a-f]{8,}\b|\b[A-Za-z0-9_+=-]{32,}\b"),
    ("phone", r"\b\d{2,4}[ .-]\d{3,4}[ .-]\d{4}\b"),
    ("secret", r"(?i)\b(?:gh[pousr]_|github_pat_|sk-|AKIA|ASIA)[A-Za-z0-9_-]+|(?:password|passwd|token|secret|api[_ -]?key|비밀번호|인증키)\s*[:=]"),
    ("markup", r"[<>`]|!\[|BEGIN .*PRIVATE KEY"),
)


class Stop(Exception):
    pass


def state_directory():
    if os.environ.get("XDG_STATE_HOME"):
        base = Path(os.environ["XDG_STATE_HOME"])
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"])
    else:
        base = Path.home() / ".local" / "state"
    return base / "plain-korean"


def fresh_state():
    return {"schema": 1, "enabled": False, "repo": REPO, "account_hash": "", "events": []}


def read_state(directory):
    path = directory / "state.json"
    if not path.exists():
        return fresh_state()
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if (state["schema"] != 1 or state["repo"] != REPO
                or type(state["enabled"]) is not bool
                or not isinstance(state["account_hash"], str)
                or not isinstance(state["events"], list)):
            raise ValueError
        for event in state["events"]:
            if (not re.fullmatch(r"[a-f0-9]{64}", event["fingerprint"])
                    or event["status"] not in {"sent", "pending"}
                    or type(event["at"]) not in {int, float}):
                raise ValueError
        return state
    except (ValueError, KeyError, TypeError):
        raise Stop("Invalid local state; submission stopped.") from None


def save_state(directory, state):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix="state-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, directory / "state.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / "submit.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise Stop("Another operation holds submit.lock; inspect it before retrying.") from None
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()


def gh_api(endpoint, *arguments, payload=None):
    executable = shutil.which("gh")
    if not executable:
        raise Stop("GitHub CLI (gh) is required for opt-in and submission.")
    command = [executable, "api", "--hostname", "github.com", endpoint, *arguments]
    if payload is not None:
        command.extend(["--input", "-"])
    try:
        result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                                capture_output=True, text=True, encoding="utf-8", timeout=30,
                                errors="replace", check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Stop("GitHub request failed or timed out; no automatic retry.") from None
    if result.returncode:
        # Do not print CLI stderr: it can contain authentication/environment details.
        raise Stop("GitHub request failed; check gh authentication and repository access.")
    try:
        # --paginate returns successive JSON values, not necessarily one array.
        decoder, values, position = json.JSONDecoder(), [], 0
        output = result.stdout
        if not isinstance(output, str):
            raise ValueError
        while position < len(output):
            if output[position].isspace():
                position += 1
                continue
            value, position = decoder.raw_decode(output, position)
            values.append(value)
        if not values:
            raise ValueError
        return values
    except ValueError:
        raise Stop("Unexpected GitHub response; submission stopped.") from None


def account_hash():
    user = gh_api("user")[0]
    if not isinstance(user, dict) or not isinstance(user.get("id"), int):
        raise Stop("Could not verify GitHub account.")
    return hashlib.sha256(str(user["id"]).encode("ascii")).hexdigest()


def validate(candidate):
    expected = set(FIELDS) | {"synthetic_examples", "privacy_reviewed"}
    if not isinstance(candidate, dict) or set(candidate) != expected:
        raise Stop("Candidate must contain exactly the documented fields.")
    if candidate["synthetic_examples"] is not True or candidate["privacy_reviewed"] is not True:
        raise Stop("Fresh synthetic examples and semantic privacy review are required.")
    clean = {}
    for field in FIELDS:
        value = candidate[field]
        if not isinstance(value, str):
            raise Stop("Candidate text fields must be strings.")
        # Reject invisible, directional and multiline content before normalizing.
        if any(unicodedata.category(char).startswith("C") or char in "\r\n\u2028\u2029" for char in value):
            raise Stop("Control/invisible characters are not allowed.")
        value = unicodedata.normalize("NFKC", value).strip()
        maximum = 80 if field in {"title", "pattern"} else 400
        if len(value) > maximum or (not value and field != "after"):
            raise Stop("Candidate field length is invalid.")
        for category, regex in BLOCKED:
            if re.search(regex, value, flags=re.IGNORECASE):
                raise Stop("Privacy check blocked a field: " + category + ". Rewrite the synthetic example.")
        clean[field] = value
    if clean["pattern"] not in PATTERNS:
        raise Stop("Unknown pattern; use other for a new pattern proposal.")
    return clean


def fingerprint(candidate):
    # Different titles/reasons for the same correction should not create duplicates.
    key = {k: " ".join(candidate[k].casefold().split()) for k in ("pattern", "before", "after")}
    return hashlib.sha256(json.dumps(key, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def render(candidate):
    digest = fingerprint(candidate)
    body = "\n\n".join([
        "## 새로 작성한 가상 예문", "실제 문서나 대화의 원문을 포함하지 않은 패턴 제안입니다.",
        "### 패턴\n" + candidate["pattern"], "### 가상 문맥\n" + candidate["context"],
        "### 수정 전\n" + candidate["before"], "### 수정 후\n" + (candidate["after"] or "문장 삭제"),
        "### 수정 이유\n" + candidate["reason"], "### 유지할 문맥\n" + candidate["keep_when"],
        "개인·조직·프로젝트·환경 정보와 고유 사건 조합을 검토했습니다. 이슈는 검토 후 반영합니다.",
        "<!-- plain-korean-pattern:" + digest + " -->",
    ])
    return {"title": "[패턴 제안] " + candidate["title"], "body": body}, digest


def issue_url(issue):
    if not isinstance(issue, dict):
        raise Stop("Unexpected issue response; inspect GitHub before retrying.")
    url = issue.get("html_url", "")
    if not isinstance(url, str):
        raise Stop("Unexpected issue URL; inspect GitHub before retrying.")
    if not re.fullmatch(r"https://github\.com/" + re.escape(REPO) + r"/issues/[1-9]\d*", url):
        raise Stop("Unexpected issue URL; inspect the repository before retrying.")
    return url


def submit(candidate, directory):
    clean = validate(candidate)
    payload, digest = render(clean)
    with locked(directory):
        state = read_state(directory)
        if not state["enabled"]:
            raise Stop("Automatic contribution is off. Explicit user opt-in is required.")
        if state["account_hash"] != account_hash():
            raise Stop("GitHub account changed; explicit user opt-in is required again.")
        repository = gh_api("repos/" + REPO)[0]
        if (not isinstance(repository, dict) or repository.get("full_name") != REPO or repository.get("private") is not False
                or repository.get("archived") is not False or repository.get("has_issues") is not True):
            raise Stop("The expected public issue destination is unavailable.")
        marker = "<!-- plain-korean-pattern:" + digest + " -->"
        pages = gh_api("repos/" + REPO + "/issues", "--method", "GET", "--paginate",
                       "-f", "state=all", "-f", "per_page=100")
        for page in pages:
            if not isinstance(page, list):
                raise Stop("Unexpected issue listing; submission stopped.")
            for issue in page:
                if not isinstance(issue, dict) or not isinstance(issue.get("body") or "", str):
                    raise Stop("Unexpected issue entry; submission stopped.")
                if "pull_request" not in issue and marker in (issue.get("body") or ""):
                    url = issue_url(issue)
                    for event in state["events"]:
                        if event["fingerprint"] == digest and event["status"] == "pending":
                            event["status"] = "sent"
                    save_state(directory, state)
                    return {"status": "duplicate", "url": url}
        matching = [e for e in state["events"] if e["fingerprint"] == digest]
        if matching:
            raise Stop("This candidate was already sent or has an uncertain result; inspect GitHub before retrying.")
        if any(e["status"] == "pending" for e in state["events"]):
            raise Stop("A previous submission has an uncertain result; resolve it before new submissions.")
        now = time.time()
        if sum(e["at"] > now - 86400 for e in state["events"]) >= 3:
            raise Stop("Local limit reached: at most three new issues per 24 hours.")
        event = {"fingerprint": digest, "at": now, "status": "pending"}
        state["events"].append(event)
        save_state(directory, state)  # Reserve before POST, including uncertain outcomes.
        try:
            issue = gh_api("repos/" + REPO + "/issues", "--method", "POST", payload=payload)[0]
            url = issue_url(issue)
        except Stop:
            raise Stop("Issue creation result is uncertain. A reservation was saved; inspect GitHub, do not retry blindly.") from None
        event["status"] = "sent"
        save_state(directory, state)
        return {"status": "created", "url": url}


def read_candidate(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError
            result[key] = value
        return result
    try:
        if path == "-":
            raw = sys.stdin.buffer.read(16385)
        else:
            with Path(path).open("rb") as handle:
                raw = handle.read(16385)
        if len(raw) > 16384:
            raise ValueError
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique)
    except (OSError, ValueError, UnicodeError):
        raise Stop("Cannot read candidate: expected a UTF-8 JSON object under 16 KiB.") from None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    enable = sub.add_parser("enable")
    enable.add_argument("--accept-public-synthetic-issues", action="store_true", required=True)
    sub.add_parser("disable")
    sub.add_parser("status")
    for command in ("preview", "submit"):
        sub.add_parser(command).add_argument("candidate", help="JSON path, or - for stdin")
    args = parser.parse_args()
    directory = state_directory()
    try:
        if args.command == "preview":
            payload, digest = render(validate(read_candidate(args.candidate)))
            print(json.dumps({"repository": REPO, "fingerprint": digest, **payload}, ensure_ascii=False, indent=2))
        elif args.command == "submit":
            print(json.dumps(submit(read_candidate(args.candidate), directory), ensure_ascii=False))
        elif args.command == "status":
            state = read_state(directory)
            print(json.dumps({"enabled": state["enabled"], "repository": REPO,
                              "pending": sum(e["status"] == "pending" for e in state["events"])}))
        else:
            with locked(directory):
                state = read_state(directory)
                state["enabled"] = args.command == "enable"
                state["account_hash"] = account_hash() if state["enabled"] else ""
                save_state(directory, state)
            print(json.dumps({"enabled": state["enabled"], "repository": REPO}))
    except Stop as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
