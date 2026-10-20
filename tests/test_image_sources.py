import importlib.util
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("image_sources", Path(__file__).resolve().parent.parent / "compiler/image_sources.py")
image_sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image_sources)


class ImageSourceTests(unittest.TestCase):
    def test_completed_materials_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "SOURCE-MANIFEST.json"
            marker.write_text("original completion marker")
            with self.assertRaisesRegex(ValueError, "completed materials"):
                image_sources.collect(root, resume=True)
            self.assertEqual(marker.read_text(), "original completion marker")

    def test_corrupt_download_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "source.tar.gz"
            with patch.object(image_sources.urllib.request, "urlopen", return_value=io.BytesIO(b"corrupt")):
                with self.assertRaisesRegex(ValueError, "Source checksum mismatch"):
                    image_sources.download("https://example.invalid/source", target, sha256="0" * 64)
            self.assertFalse(target.exists())

    def test_valid_download_is_reused_after_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "source.tar.gz"
            target.write_bytes(b"source")
            with patch.object(image_sources.urllib.request, "urlopen") as request:
                image_sources.download("https://example.invalid/source", target, sha256=hashlib.sha256(b"source").hexdigest())
            request.assert_not_called()

    def test_cross_package_retains_built_using_source_version(self):
        rows = [["libc6-arm64-cross", "2.41-11cross1", "cross-toolchain-base", "76",
                 "glibc (= 2.41-11), linux (= 6.12.38-1)", ""]]
        self.assertEqual(image_sources.source_requirements(rows),
                         [("cross-toolchain-base", "76"), ("glibc", "2.41-11"), ("linux", "6.12.38-1")])

    def test_static_built_using_and_source_epochs_are_preserved(self):
        rows = [["tool:amd64", "1.0-1+b1", "tool", "1:1.0-1", "", "rust-library (= 2:3.0-1)"],
                ["tool:arm64", "1.0-1+b1", "tool", "1:1.0-1", "", "rust-library (= 2:3.0-1)"]]
        self.assertEqual(image_sources.source_requirements(rows), [("rust-library", "2:3.0-1"), ("tool", "1:1.0-1")])

    def test_unrecognized_built_using_does_not_silently_omit_source(self):
        with self.assertRaisesRegex(ValueError, "Unrecognized Built-Using"):
            image_sources.source_requirements([["tool", "1", "tool", "1", "lib (>= 2)", ""]])
