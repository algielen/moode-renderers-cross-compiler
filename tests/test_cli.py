import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cli", ROOT / "compiler/cli.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class ProfileTests(unittest.TestCase):
    def test_alias_selects_exact_moode_package(self):
        profile = cli.select_profile("r1036", "3b+")
        self.assertEqual(profile, cli.select_profile("10.3.6", "3b+"))
        self.assertEqual(profile["package_version"], "0.8.0-1moode1")
        self.assertEqual(profile["target"], "aarch64-unknown-linux-gnu")

    def test_unsupported_targets_are_rejected(self):
        for version, model in [("9.4.2", "3b+"), ("10.3.6", "zero"), ("10.3.6", "2b")]:
            with self.subTest(version=version, model=model), self.assertRaises(ValueError):
                cli.select_profile(version, model)

    def test_missing_moode_options_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "--onevent"):
            cli.check_help(" ".join(option for option in cli.REQUIRED_OPTIONS if option != "--onevent"))
        cli.check_help(" ".join(cli.REQUIRED_OPTIONS))

    def test_cli_fails_before_building_invalid_target(self):
        result = subprocess.run([sys.executable, str(ROOT / "compiler/cli.py"), "build",
                                 "--pi-model", "zero", "--moode-version", "10.3.6"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported Pi model", result.stderr)

    def test_failed_build_exports_no_success_artifacts(self):
        # Exercise the parent process failure boundary without downloading sources.
        with tempfile.TemporaryDirectory() as output:
            args = type("Args", (), dict(moode_version="10.3.6", pi_model="3b+",
                                        renderer="librespot", output=output, jobs=1))()
            class FailedProcess:
                stdout = ["compiler failed\n"]
                def wait(self):
                    return 1
            with patch.object(cli.subprocess, "Popen", return_value=FailedProcess()), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, "Build failed"):
                    cli.build(args)
            self.assertEqual([p.name for p in Path(output).iterdir()], ["build.failed.log"])

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as output:
            existing = Path(output) / "librespot"
            existing.write_bytes(b"previous build")
            args = type("Args", (), dict(moode_version="10.3.6", pi_model="3b+",
                                        renderer="librespot", output=output, jobs=1))()
            with self.assertRaisesRegex(ValueError, "empty directory"):
                cli.build(args)
            self.assertEqual(existing.read_bytes(), b"previous build")


if __name__ == "__main__":
    unittest.main()
