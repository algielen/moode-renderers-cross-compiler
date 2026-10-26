import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("check_release_scope", Path(__file__).with_name("check_release_scope.py"))
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


class ReleaseScopeTests(unittest.TestCase):
    def fixture(self, root):
        profile = json.loads((Path(__file__).resolve().parent.parent / "profiles/10.3.6.json").read_text())
        for renderer, name in (("librespot", "librespot"), ("qobuz", "pibuz")):
            directory = root / renderer
            directory.mkdir()
            (directory / "manifest.json").write_text(json.dumps({
                "profile": {"moode_version": "10.3.6"}, "packages": profile["renderers"][renderer]["packages"]}))

    def test_selected_downloads_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            self.fixture(Path(directory))
            with patch.object(scope, "cleared", return_value=True):
                scope.check(directory, "10.3.6")

    def test_initial_profile_requires_spotify_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "librespot").mkdir()
            (root / "librespot/manifest.json").write_text(json.dumps({
                "profile": {"moode_version": "10.2.0"}, "packages": json.loads((Path(__file__).resolve().parent.parent / "profiles/10.2.0.json").read_text())["renderers"]["librespot"]["packages"]}))
            scope.check(root)
            (root / "qobuz").mkdir()
            with self.assertRaises(ValueError):
                scope.check(root)

    def test_changed_source_recipe_cannot_borrow_existing_clearance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "librespot/manifest.json"
            manifest = json.loads(path.read_text())
            manifest["packages"][0]["source_commit"] = "0" * 40
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "package recipe"):
                scope.check(root, "10.3.6")

    def test_airplay_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "airplay").mkdir()
            with self.assertRaisesRegex(ValueError, "only approved renderer"):
                scope.check(root, "10.3.6")

    def test_mislabeled_airplay_package_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "qobuz/manifest.json"
            manifest = json.loads(path.read_text())
            manifest["packages"] = [{"name": "shairport-sync"}]
            path.write_text(json.dumps(manifest))
            with patch.object(scope, "cleared", return_value=True), self.assertRaisesRegex(ValueError, "Unexpected release package"):
                scope.check(root, "10.3.6")
