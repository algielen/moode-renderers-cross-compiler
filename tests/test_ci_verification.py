import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("ci_verification", Path(__file__).with_name("ci_verification.py"))
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class VerificationTests(unittest.TestCase):
    def setUp(self):
        package = {"name": "librespot", "package_version": "1", "build_system": "cargo"}
        base = {"target": "aarch64", "distribution": "trixie", "renderers": {"librespot": {"packages": [package]}}}
        self.profiles = {"old": copy.deepcopy(base), "new": copy.deepcopy(base)}
        self.profiles["new"]["renderers"]["qobuz"] = {"packages": [dict(package, name="pibuz")]}
        self.versions = ["new", "old"]

    def reports(self):
        result = []
        for shard in ci.matrix(self.versions, self.profiles)["include"]:
            renderer = shard["renderer"]
            builds = []
            for version in shard["versions"]:
                profile = self.profiles[version]
                packages = profile["renderers"][renderer]["packages"]
                builds.append({"version": version, "renderer": renderer,
                               "files": {name: "a" * 64 for name in ci.expected_files(packages)},
                               "packages": [{"recipe": ci.recipe(profile, p), "binary_sha256": "a" * 64} for p in packages]})
            result.append({"schema": 1, "commit": "commit", **shard, "builds": builds})
        return result

    def aggregate(self, reports):
        return ci.aggregate(reports, self.versions, "commit", self.profiles)

    def test_shards_cover_every_supported_pair_and_omit_empty_renderer(self):
        self.assertEqual(ci.matrix(["old"], self.profiles), {"include": [{"renderer": "librespot", "versions": ["old"]}]})
        self.assertEqual(len(self.aggregate(self.reports())["builds"]), 3)
        self.assertEqual(ci.matrix([], self.profiles), {"include": []})

    def test_missing_and_duplicate_shards_fail(self):
        reports = self.reports()
        for changed in (reports[:-1], reports + [reports[0]]):
            with self.assertRaises(ValueError):
                self.aggregate(changed)

    def test_unknown_renderer_cannot_be_silently_omitted(self):
        self.profiles["new"]["renderers"]["unknown"] = {"packages": []}
        with self.assertRaisesRegex(ValueError, "Unknown renderer"):
            ci.matrix(self.versions, self.profiles)

    def test_missing_duplicate_and_unexpected_builds_fail(self):
        for change in ("missing", "duplicate", "unexpected"):
            with self.subTest(change=change):
                reports = self.reports()
                if change == "missing":
                    reports[0]["builds"].pop()
                elif change == "duplicate":
                    reports[0]["builds"].append(copy.deepcopy(reports[0]["builds"][0]))
                else:
                    reports[0]["builds"][0]["version"] = "unknown"
                with self.assertRaises(ValueError):
                    self.aggregate(reports)

    def test_wrong_commit_declared_coverage_and_recipe_fail(self):
        for change in ("commit", "coverage", "recipe"):
            reports = self.reports()
            if change == "commit":
                reports[0]["commit"] = "other"
            elif change == "coverage":
                reports[0]["versions"].pop()
            else:
                reports[0]["builds"][0]["packages"][0]["recipe"]["target"] = "wrong"
            with self.assertRaises(ValueError):
                self.aggregate(reports)

    def test_equivalent_recipe_binary_disagreement_fails(self):
        reports = self.reports()
        build = reports[0]["builds"][1]
        build["packages"][0]["binary_sha256"] = build["files"]["librespot"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "equivalent recipe"):
            self.aggregate(reports)

    def test_malformed_or_missing_hash_fails(self):
        for digest in ("bad", None):
            reports = self.reports()
            reports[0]["builds"][0]["files"]["manifest.json"] = digest
            with self.assertRaisesRegex(ValueError, "hashes"):
                self.aggregate(reports)

    def test_release_requires_default_downloads(self):
        with self.assertRaisesRegex(ValueError, "default release coverage"):
            ci.aggregate(self.reports(), self.versions, "commit", self.profiles, release=True)

    def release_fixture(self, root):
        builds = []
        for renderer, name in (("librespot", "librespot"), ("qobuz", "pibuz")):
            directory = root / renderer
            directory.mkdir()
            package = {"name": name, "package_version": "1", "build_system": "cargo"}
            for filename in ci.expected_files([package]):
                (directory / filename).write_bytes(b"payload")
            (directory / "manifest.json").write_text(json.dumps({"profile": {"moode_version": "10.3.6"}, "packages": [package]}))
            files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}
            (directory / "SHA256SUMS").write_text("".join(f"{digest}  {filename}\n" for filename, digest in files.items()))
            builds.append({"version": "10.3.6", "renderer": renderer, "files": files})
        return {"schema": 1, "commit": "commit", "builds": builds}

    def test_bind_rejects_unapproved_files_and_changed_payloads(self):
        for mutation in (None, "extra.deb", "extra_sources.tar.gz", "changed"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                approval = self.release_fixture(root)
                if mutation:
                    (root / "qobuz" / ("pibuz" if mutation == "changed" else mutation)).write_bytes(b"unexpected")
                # Isolate binding from the separate archive-content checker.
                with patch("check_redistribution.check"):
                    if mutation:
                        with self.assertRaises(ValueError):
                            ci.bind(root, approval, "commit", "10.3.6")
                    else:
                        ci.bind(root, approval, "commit", "10.3.6")

    def test_bind_rejects_valid_checksums_from_different_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = self.release_fixture(root)
            approval["builds"][0]["files"]["librespot"] = "b" * 64
            with patch("check_redistribution.check"), self.assertRaisesRegex(ValueError, "aggregate-approved"):
                ci.bind(root, approval, "commit", "10.3.6")
