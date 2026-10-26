import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("select_profiles", Path(__file__).with_name("select_profiles.py"))
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


class SelectionTests(unittest.TestCase):
    versions = ["10.3.5", "10.3.6", "10.3.7"]

    def test_github_outputs_preserve_plain_profile_and_json_structures(self):
        output = io.StringIO()
        plan = {"release_profile": "10.2.0", "profile_only": True,
                "versions": ["10.2.0"], "matrix": {"include": [{"renderer": "librespot", "versions": ["10.2.0"]}]}}
        planner.write_outputs(plan, output)
        values = dict(line.split("=", 1) for line in output.getvalue().splitlines())
        self.assertEqual(values["release_profile"], "10.2.0")
        self.assertEqual(values["profile_only"], "true")
        self.assertEqual(json.loads(values["versions"]), plan["versions"])
        self.assertEqual(json.loads(values["matrix"]), plan["matrix"])

    def test_new_and_modified_profiles_only(self):
        plan = planner.select(["profiles/10.3.7.json", "tests/test_cli.py", "README.md"], self.versions)
        self.assertEqual(plan, {"versions": ["10.3.7"], "build": True, "full": False})
        self.assertEqual(planner.select(["profiles/10.3.5.json"], self.versions)["versions"], ["10.3.5"])

    def test_docs_and_deleted_profiles_skip_builds(self):
        self.assertFalse(planner.select(["AGENTS.md", "docs/validation.md"], self.versions)["build"])
        self.assertFalse(planner.select(["compiler/release-policy.json"], self.versions)["build"])
        self.assertFalse(planner.select(["profiles/10.2.0.json"], self.versions)["build"])

    def test_shared_changes_and_manual_full_verify_everything(self):
        for path in ["Dockerfile", ".dockerignore", "compiler/recipes.py", "tests/runtime.sh",
                     "tests/select_profiles.py", ".github/workflows/build.yml"]:
            with self.subTest(path=path):
                self.assertTrue(planner.select([path], self.versions)["full"])
                self.assertEqual(planner.select([path], self.versions)["versions"], self.versions)
        self.assertEqual(planner.select([], self.versions, full=True)["versions"], self.versions)

    def test_release_keeps_default_downloads_without_rebuilding_history(self):
        self.assertEqual(planner.select([], self.versions, release=True, release_profile="10.3.6")["versions"], ["10.3.6"])
        self.assertEqual(planner.select(["profiles/10.3.7.json"], self.versions, release=True, release_profile="10.3.6")["versions"],
                         ["10.3.6", "10.3.7"])

    def test_explicit_smoke_test_overrides_full_matrix_selection(self):
        self.assertEqual(planner.select(["compiler/recipes.py"], self.versions, profile_only=True, release_profile="10.3.6"),
                         {"versions": ["10.3.6"], "build": True, "full": False})
        with self.assertRaisesRegex(ValueError, "unavailable"):
            planner.select([], ["10.3.5"], profile_only=True)

    def test_first_and_subsequent_profile_releases(self):
        available = ["10.2.0", "10.2.1", "10.3.6"]
        self.assertEqual(planner.select([], available, release=True)["versions"], ["10.2.0"])
        self.assertEqual(planner.select(["compiler/recipes.py"], available, profile_only=True,
                                        release_profile="10.2.1")["versions"], ["10.2.1"])

    def test_push_and_pr_baselines(self):
        self.assertEqual(planner.baseline({"before": "abc", "ref": "refs/heads/main"}, "push", "HEAD"), "abc")
        self.assertIsNone(planner.baseline({"before": "0" * 40}, "push", "HEAD"))
        with patch.object(planner, "git", return_value="merge-base") as git:
            self.assertEqual(planner.baseline({"pull_request": {"base": {"sha": "base"}}},
                                              "pull_request", "HEAD"), "merge-base")
            git.assert_called_once_with("merge-base", "base", "HEAD")

    def test_release_baseline_excludes_current_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.check_output(["git", "-C", directory, *args], text=True).strip()
            git("init", "-q")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "first")
            git("tag", "v0.1.1")
            previous = git("rev-parse", "HEAD")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "next")
            git("tag", "v0.1.2")
            with patch.object(planner, "git", side_effect=git):
                base = planner.baseline({"ref": "refs/tags/v0.1.2"}, "push", "HEAD")
            self.assertEqual(git("rev-parse", base), previous)
