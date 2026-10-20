import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("review_licenses", Path(__file__).with_name("review_licenses.py"))
reviewer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reviewer)


class BuildLicenseReviewTests(unittest.TestCase):
    def fixture(self, root, built_id):
        inventory = [{"id": "runtime", "name": "runtime", "license": "MIT OR Apache-2.0"},
                     {"id": "unused-gui", "name": "gui", "license": "GPL-3.0-only OR LicenseRef-Commercial"}]
        path = root / "sources.tar.gz"
        data = json.dumps(inventory).encode()
        with tarfile.open(path, "w:gz") as archive:
            member = tarfile.TarInfo("source/dependencies.json")
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
        manifest = {"profile": {"target": "aarch64-unknown-linux-gnu"}, "packages": [{
            "name": "demo", "build_system": "cargo", "source_commit": "a" * 40,
            "cargo_artifacts": [{"package_id": built_id, "role": "target", "features": [], "kind": ["lib"]}],
            "redistribution": {"source_archive": path.name, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
        }]}
        (root / "manifest.json").write_text(json.dumps(manifest))

    def test_unused_workspace_gpl_dependency_is_not_reported_as_built(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, "runtime")
            report = reviewer.review(root)["packages"][0]
            self.assertEqual(report["review_required"], [])
            self.assertEqual([item["id"] for item in report["built_packages"]], ["runtime"])
            self.assertEqual(report["built_packages"][0]["selected_license"], "MIT")

    def test_unrecognized_built_license_is_not_cleared(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, "unused-gui")
            self.assertEqual(reviewer.review(root)["packages"][0]["review_required"], ["unused-gui"])

    def test_missing_feature_dependency_metadata_fails_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, "alsa-feature-dependency")
            with self.assertRaisesRegex(ValueError, "Missing actual-build dependency metadata"):
                reviewer.review(root)
