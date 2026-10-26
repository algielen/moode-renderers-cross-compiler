import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import release_policy as policy


class ReleasePolicyTests(unittest.TestCase):
    def setUp(self):
        self.profiles = policy.profiles_for_policy()
        self.librespot = policy.identity(self.profiles["10.2.0"], self.profiles["10.2.0"]["renderers"]["librespot"]["packages"][0])
        self.pibuz = policy.identity(self.profiles["10.3.5"], self.profiles["10.3.5"]["renderers"]["qobuz"]["packages"][0])
        self.policy = {"schema": 1, "reviewed_build_inputs": {}, "approvals": [
            {"status": "cleared", "recipe": self.librespot}, {"status": "cleared", "recipe": self.pibuz}],
            "published": [{"recipe": self.librespot, "release": "v0.1.2", "profile": "10.2.0"}]}

    def test_existing_spotify_reused_for_every_profile(self):
        for version in self.profiles:
            result = policy.plan(version, self.profiles, self.policy)
            self.assertFalse(any(s["renderer"] == "librespot" for s in result["matrix"]["include"]))
            self.assertEqual(result["reused"][0]["release"], "v0.1.2")
        self.assertEqual(policy.plan("10.2.1", self.profiles, self.policy)["matrix"], {"include": []})

    def test_pibuz_built_once_at_first_matching_profile(self):
        result = policy.plan("10.3.6", self.profiles, self.policy)
        self.assertEqual(result["profile"], "10.3.5")
        self.assertEqual(result["matrix"]["include"], [{"renderer": "qobuz", "versions": ["10.3.5"],
                                                       "compatible_profiles": ["10.3.5", "10.3.6"]}])
        self.policy["published"].append({"recipe": self.pibuz, "release": "v0.1.3", "profile": "10.3.5"})
        self.assertFalse(policy.plan("10.3.6", self.profiles, self.policy)["matrix"]["include"])

    def test_pending_and_unknown_licenses_block_builds(self):
        self.policy["approvals"][1]["status"] = "reviewed_pending_owner"
        self.assertIn("qobuz", policy.plan("10.3.5", self.profiles, self.policy)["blocked"])
        self.assertIn("airplay", policy.plan("10.2.0", self.profiles, self.policy)["blocked"])
        self.assertIn("qobuz", policy.plan("10.3.4", self.profiles, self.policy)["blocked"])

    def test_committed_policy_reuses_published_pibuz(self):
        for version in ("10.3.5", "10.3.6"):
            result = policy.plan(version, self.profiles)
            self.assertEqual(result["matrix"]["include"], [])
            self.assertEqual(next(r for r in result["reused"] if r["renderer"] == "qobuz")["release"], "v0.1.3")
            self.assertEqual(result["reused"][0]["release"], "v0.1.2")
            self.assertIn("airplay", result["blocked"])
        self.assertIn("qobuz", policy.plan("10.3.4", self.profiles)["blocked"])

    def test_release_aggregate_requires_only_the_new_cleared_renderer(self):
        import ci_verification as verification
        profile = self.profiles["10.3.5"]
        packages = profile["renderers"]["qobuz"]["packages"]
        evidence = {"schema": 1, "commit": "commit", "renderer": "qobuz", "versions": ["10.3.5"],
                    "builds": [{"version": "10.3.5", "renderer": "qobuz",
                                "files": {name: "a" * 64 for name in verification.expected_files(packages)},
                                "packages": [{"recipe": verification.recipe(profile, p), "binary_sha256": "a" * 64}
                                             for p in packages]}]}
        with patch.object(policy, "load", return_value=self.policy):
            approval = verification.aggregate([evidence], ["10.3.5"], "commit", self.profiles,
                                               release=True, release_profile="10.3.5")
            self.assertEqual([b["renderer"] for b in approval["builds"]], ["qobuz"])
            with self.assertRaises(ValueError):
                verification.aggregate([], ["10.3.5"], "commit", self.profiles, release=True, release_profile="10.3.5")

    def test_full_recipe_changes_do_not_inherit_clearance(self):
        for field in ("package_version", "source_commit", "features", "rust_toolchain", "build_env"):
            profile = copy.deepcopy(self.profiles["10.2.0"])
            profile["renderers"]["librespot"]["packages"][0][field] = "changed"
            self.assertFalse(policy.cleared(profile, "librespot", self.policy), field)
        for field in ("target", "distribution", "architecture"):
            profile = copy.deepcopy(self.profiles["10.2.0"])
            profile[field] = "changed"
            self.assertFalse(policy.cleared(profile, "librespot", self.policy), field)

    def test_profile_labels_and_validation_do_not_change_package_identity(self):
        profile = copy.deepcopy(self.profiles["10.2.0"])
        profile.update(moode_version="99.0.0", aliases=["another"], models=["5"])
        profile["renderers"]["librespot"]["validated_models"] = []
        self.assertTrue(policy.cleared(profile, "librespot", self.policy))

    def test_build_input_change_invalidates_clearance_and_line_endings_do_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Dockerfile").write_bytes(b"reviewed\r\n")
            self.policy["reviewed_build_inputs"] = {"Dockerfile": hashlib.sha256(b"reviewed\n").hexdigest()}
            self.assertTrue(policy.cleared(self.profiles["10.2.0"], "librespot", self.policy, root))
            (root / "Dockerfile").write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "changed build input"):
                policy.plan("10.2.0", self.profiles, self.policy, root)

    def test_real_tag_plan_skips_unchanged_packages_and_keeps_structured_outputs(self):
        spec = importlib.util.spec_from_file_location("tag_planner", Path(__file__).with_name("select_profiles.py"))
        planner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(planner)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event = root / "event.json"
            event.write_text(json.dumps({"ref": "refs/tags/v9.0.0"}))
            output = root / "output"
            with contextlib.chdir(policy.ROOT), patch("sys.argv", ["select_profiles", "--event", str(event), "--release-profile", "10.2.1"]), patch.object(planner, "baseline", return_value=None), patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}), contextlib.redirect_stdout(io.StringIO()):
                planner.main()
            values = dict(line.split("=", 1) for line in output.read_text().splitlines())
            self.assertEqual(values["build"], "false")
            self.assertEqual(json.loads(values["matrix"]), {"include": []})
            self.assertEqual(values["release_artifacts"], "true")
