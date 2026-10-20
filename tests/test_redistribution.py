import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("redistribution_check", Path(__file__).with_name("check_redistribution.py"))
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class RedistributionTests(unittest.TestCase):
    def fixture(self, root):
        package = {"name": "daemon", "package_version": "1-1", "build_system": "nqptp"}
        materials = {}
        for kind, prefix in (("source", "source"), ("notice", "notices")):
            path = root / f"{kind}.tar.gz"
            names = ["SOURCE.txt"]
            if kind == "source":
                names += ["upstream", "build-scripts/compiler/recipes.py", "recipe.json", "dependencies.json"]
            with tarfile.open(path, "w:gz") as archive:
                for name in names:
                    member = tarfile.TarInfo(prefix + "/" + name)
                    member.size = 4
                    archive.addfile(member, io.BytesIO(b"data"))
            materials[kind + "_archive"] = path.name
            materials[kind + "_sha256"] = checker.sha256(path)
        package["redistribution"] = materials
        (root / "manifest.json").write_text(json.dumps({"packages": [package]}))
        (root / "daemon").write_bytes(b"binary")
        (root / "daemon_1-1_arm64.deb").write_bytes(b"package")
        self.checksums(root)

    def checksums(self, root):
        (root / "SHA256SUMS").write_text("".join(
            f"{checker.sha256(path)}  {path.name}\n" for path in sorted(root.iterdir())
            if path.name != "SHA256SUMS"))

    def test_missing_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "No build manifests"):
                checker.check(directory)

    def test_corrupt_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            checker.check(root)
            (root / "source.tar.gz").write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                checker.check(root)

    def test_old_manifest_without_materials_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            manifest = json.loads((root / "manifest.json").read_text())
            del manifest["packages"][0]["redistribution"]
            (root / "manifest.json").write_text(json.dumps(manifest))
            self.checksums(root)
            with self.assertRaises(KeyError):
                checker.check(root)

    def test_source_without_build_scripts_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            with tarfile.open(root / "source.tar.gz", "w:gz") as archive:
                member = tarfile.TarInfo("source/SOURCE.txt")
                archive.addfile(member, io.BytesIO())
            manifest = json.loads((root / "manifest.json").read_text())
            manifest["packages"][0]["redistribution"]["source_sha256"] = checker.sha256(root / "source.tar.gz")
            (root / "manifest.json").write_text(json.dumps(manifest))
            self.checksums(root)
            with self.assertRaisesRegex(ValueError, "Missing upstream"):
                checker.check(root)
