import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("check_release_scope", Path(__file__).with_name("check_release_scope.py"))
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


class ReleaseScopeTests(unittest.TestCase):
    def fixture(self, root):
        for renderer, name in (("librespot", "librespot"), ("qobuz", "pibuz")):
            directory = root / renderer
            directory.mkdir()
            (directory / "manifest.json").write_text(json.dumps({
                "profile": {"moode_version": "10.3.6"}, "packages": [{"name": name}]}))

    def test_selected_downloads_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            self.fixture(Path(directory))
            scope.check(directory)

    def test_airplay_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "airplay").mkdir()
            with self.assertRaisesRegex(ValueError, "only librespot and qobuz"):
                scope.check(root)

    def test_mislabeled_airplay_package_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "qobuz/manifest.json"
            manifest = json.loads(path.read_text())
            manifest["packages"] = [{"name": "shairport-sync"}]
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Unexpected release package"):
                scope.check(root)
