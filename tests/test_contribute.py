import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "plain-korean" / "scripts"))
import contribute as c
import examples


def candidate():
    row = {k: v for k, v in examples.load()[10].items() if k != "id"}
    return dict(row, synthetic_examples=True, privacy_reviewed=True)


class ContributionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.data = candidate()
        self.calls = []
        self.issue = {"html_url": "https://github.com/" + c.REPO + "/issues/7"}

    def enable(self):
        state = c.fresh_state()
        state.update(enabled=True, account_hash="account")
        c.save_state(self.directory, state)

    def api(self, endpoint, *args, payload=None):
        self.calls.append((endpoint, args, payload))
        if endpoint == "repos/" + c.REPO:
            return [dict(full_name=c.REPO, private=False, archived=False, has_issues=True)]
        if "POST" in args:
            return [self.issue]
        return [[]]

    def submit(self):
        with patch.object(c, "account_hash", return_value="account"), patch.object(c, "gh_api", side_effect=self.api):
            return c.submit(self.data, self.directory)

    def test_off_by_default_has_no_network_calls(self):
        with patch.object(c, "gh_api") as api, patch.object(c, "account_hash") as auth:
            with self.assertRaisesRegex(c.Stop, "off"):
                c.submit(self.data, self.directory)
            api.assert_not_called()
            auth.assert_not_called()

    def test_sensitive_content_blocked_before_authentication(self):
        unsafe = ["name@example.test", "C:\\Users\\Example\\draft", "https://example.test",
                  "10.12.34.56", "010-1234-5678", "2026-10-08", "a" * 40,
                  "token=" + "fictional", "\u202etest", "test\u200b", "줄\n바꿈", "줄\u2028바꿈",
                  "@someone", "<img>", "server.internal", "2001:db8::1"]
        with patch.object(c, "gh_api") as api:
            for value in unsafe:
                with self.subTest(value=value):
                    data = dict(self.data, context=value)
                    with self.assertRaises(c.Stop):
                        c.submit(data, self.directory)
            api.assert_not_called()

    def test_all_fields_and_unknown_fields_are_checked(self):
        for field in c.FIELDS:
            with self.subTest(field=field), self.assertRaises(c.Stop):
                c.validate(dict(self.data, **{field: "name@example.test"}))
        with self.assertRaises(c.Stop):
            c.validate(dict(self.data, raw_document="hidden"))
        for key in ("synthetic_examples", "privacy_reviewed"):
            with self.assertRaises(c.Stop):
                c.validate(dict(self.data, **{key: False}))

    def test_fullwidth_identifiers_cannot_bypass_check(self):
        with self.assertRaises(c.Stop):
            c.validate(dict(self.data, context="ｎａｍｅ＠ｅｘａｍｐｌｅ．ｔｅｓｔ"))

    def test_account_switch_stops_before_repository_or_post(self):
        self.enable()
        with patch.object(c, "account_hash", return_value="other"), patch.object(c, "gh_api") as api:
            with self.assertRaisesRegex(c.Stop, "account changed"):
                c.submit(self.data, self.directory)
            api.assert_not_called()

    def test_created_issue_has_only_synthetic_payload(self):
        self.enable()
        result = self.submit()
        self.assertEqual(result, {"status": "created", "url": self.issue["html_url"]})
        post = [call for call in self.calls if "POST" in call[1]]
        self.assertEqual(len(post), 1)
        self.assertEqual(set(post[0][2]), {"title", "body"})
        state = c.read_state(self.directory)
        self.assertEqual(state["events"][0]["status"], "sent")
        stored = (self.directory / "state.json").read_text()
        self.assertNotIn(self.data["before"], stored)
        self.assertNotIn(self.data["title"], stored)

    def test_title_and_reason_changes_do_not_change_fingerprint(self):
        a = c.validate(self.data)
        b = c.validate(dict(self.data, title="다른 제목", reason="같은 수정 예를 설명한다."))
        self.assertEqual(c.fingerprint(a), c.fingerprint(b))

    def test_duplicate_on_later_page_including_closed_issue(self):
        self.enable()
        def api(endpoint, *args, payload=None):
            if "--paginate" in args:
                return [[], [dict(self.issue, body=c.render(c.validate(self.data))[0]["body"], state="closed")]]
            return self.api(endpoint, *args, payload=payload)
        with patch.object(c, "account_hash", return_value="account"), patch.object(c, "gh_api", side_effect=api):
            self.assertEqual(c.submit(self.data, self.directory)["status"], "duplicate")
        self.assertFalse(any("POST" in call[1] for call in self.calls))

    def test_private_or_redirected_repo_cannot_receive_candidate(self):
        self.enable()
        for repository in [dict(full_name="other/repo", private=False, archived=False, has_issues=True),
                           dict(full_name=c.REPO, private=True, archived=False, has_issues=True)]:
            with patch.object(c, "account_hash", return_value="account"), patch.object(c, "gh_api", return_value=[repository]) as api:
                with self.assertRaises(c.Stop):
                    c.submit(self.data, self.directory)
                self.assertEqual(api.call_count, 1)

    def test_timeout_reserves_and_does_not_blindly_post_again(self):
        self.enable()
        def failing(endpoint, *args, payload=None):
            if "POST" in args:
                raise c.Stop("timeout")
            return self.api(endpoint, *args, payload=payload)
        with patch.object(c, "account_hash", return_value="account"), patch.object(c, "gh_api", side_effect=failing):
            with self.assertRaisesRegex(c.Stop, "uncertain"):
                c.submit(self.data, self.directory)
        self.assertEqual(c.read_state(self.directory)["events"][0]["status"], "pending")
        self.calls.clear()
        with self.assertRaisesRegex(c.Stop, "uncertain"):
            self.submit()
        self.assertFalse(any("POST" in call[1] for call in self.calls))

    def test_uncertain_submission_can_be_reconciled_with_remote(self):
        self.enable()
        _, digest = c.render(c.validate(self.data))
        state = c.read_state(self.directory)
        state["events"] = [dict(fingerprint=digest, at=time.time(), status="pending")]
        c.save_state(self.directory, state)
        body, _ = c.render(c.validate(self.data))
        def api(endpoint, *args, payload=None):
            if "--paginate" in args:
                return [[dict(self.issue, body=body["body"])]]
            return self.api(endpoint, *args, payload=payload)
        with patch.object(c, "account_hash", return_value="account"), patch.object(c, "gh_api", side_effect=api):
            self.assertEqual(c.submit(self.data, self.directory)["status"], "duplicate")
        self.assertEqual(c.read_state(self.directory)["events"][0]["status"], "sent")

    def test_pending_different_candidate_blocks_new_submission(self):
        self.enable()
        state = c.read_state(self.directory)
        state["events"] = [dict(fingerprint="a" * 64, at=time.time(), status="pending")]
        c.save_state(self.directory, state)
        with self.assertRaisesRegex(c.Stop, "previous submission"):
            self.submit()
        self.assertFalse(any("POST" in call[1] for call in self.calls))

    def test_daily_limit_and_lock_block_submission(self):
        self.enable()
        state = c.read_state(self.directory)
        state["events"] = [dict(fingerprint=str(i) * 64, at=time.time(), status="sent") for i in range(3)]
        c.save_state(self.directory, state)
        with self.assertRaisesRegex(c.Stop, "limit"):
            self.submit()
        (self.directory / "submit.lock").touch()
        with patch.object(c, "gh_api") as api:
            with self.assertRaisesRegex(c.Stop, "lock"):
                c.submit(self.data, self.directory)
            api.assert_not_called()

    def test_preview_runs_without_gh_or_state(self):
        path = self.directory / "synthetic.json"
        path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        env = dict(__import__("os").environ, XDG_STATE_HOME=str(self.directory / "state"))
        result = subprocess.run([sys.executable, str(Path(c.__file__)), "preview", str(path)],
                                capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["repository"], c.REPO)
        self.assertFalse((self.directory / "state").exists())

    def test_cli_pagination_and_post_use_fixed_host_no_shell(self):
        responses = [subprocess.CompletedProcess([], 0, "[]\n[]", ""),
                     subprocess.CompletedProcess([], 0, json.dumps(self.issue), "")]
        with patch.object(c.shutil, "which", return_value="gh"), patch.object(c.subprocess, "run", side_effect=responses) as run:
            self.assertEqual(c.gh_api("repos/" + c.REPO + "/issues", "--paginate"), [[], []])
            c.gh_api("repos/" + c.REPO + "/issues", "--method", "POST", payload={"title": "가상 제목", "body": "가상 본문"})
        self.assertIn("github.com", run.call_args_list[0].args[0])
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(json.loads(run.call_args.kwargs["input"])["body"], "가상 본문")

    def test_malformed_state_stops_before_network(self):
        (self.directory / "state.json").write_text('{"enabled": true}', encoding="utf-8")
        with patch.object(c, "gh_api") as api, patch.object(c, "account_hash") as auth:
            with self.assertRaisesRegex(c.Stop, "Invalid local state"):
                c.submit(self.data, self.directory)
            api.assert_not_called()
            auth.assert_not_called()

    def test_unexpected_create_response_preserves_reservation(self):
        self.enable()
        self.issue = {"html_url": "https://example.test/issues/7"}
        with self.assertRaisesRegex(c.Stop, "uncertain"):
            self.submit()
        self.assertEqual(c.read_state(self.directory)["events"][0]["status"], "pending")

    def test_disable_works_without_gh_and_preserves_history(self):
        self.enable()
        state = c.read_state(self.directory)
        state["events"] = [dict(fingerprint="a" * 64, at=time.time(), status="sent")]
        c.save_state(self.directory, state)
        with patch.object(sys, "argv", ["contribute.py", "disable"]), patch.object(c, "state_directory", return_value=self.directory), patch.object(c, "gh_api") as api, patch("builtins.print"):
            self.assertEqual(c.main(), 0)
            api.assert_not_called()
        saved = c.read_state(self.directory)
        self.assertFalse(saved["enabled"])
        self.assertEqual(saved["account_hash"], "")
        self.assertEqual(saved["events"], state["events"])

    def test_duplicate_json_keys_and_oversized_candidates_are_rejected(self):
        path = self.directory / "invalid.json"
        for text in ['{"title":"첫 값","title":"다른 값"}', " " * 16385]:
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(c.Stop):
                c.read_candidate(str(path))


class PackageTests(unittest.TestCase):
    def test_bundled_cases_are_valid_and_contain_keep_examples(self):
        rows = examples.load()
        self.assertEqual(len({r["id"] for r in rows}), len(rows))
        self.assertTrue(any(r["before"] == r["after"] for r in rows))
        for row in rows:
            data = dict(row)
            data.pop("id")
            c.validate(dict(data, synthetic_examples=True, privacy_reviewed=True))

    def test_search_returns_relevant_case(self):
        found = examples.search("연결 끊겨도", 3)
        self.assertIn("P013", [row["id"] for row in found])


if __name__ == "__main__":
    unittest.main()
