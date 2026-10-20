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
    def test_all_releases_since_on_device_build_introduction(self):
        expected = {f"10.2.{patch}" for patch in range(5)} | {f"10.3.{patch}" for patch in range(7)}
        all_profiles = cli.profiles()
        self.assertEqual({p["moode_version"] for p in all_profiles}, expected)
        seen = set()
        for profile in all_profiles:
            for name in [profile["moode_version"], *profile["aliases"]]:
                with self.subTest(release=name):
                    self.assertNotIn(name, seen)
                    seen.add(name)
                    for renderer in profile["renderers"]:
                        selected = cli.select_profile(name, "3b+", renderer)
                        self.assertEqual(selected["moode_version"], profile["moode_version"])
                        self.assertEqual(selected["packages"], profile["renderers"][renderer]["packages"])
            self.assertRegex(profile["moode_commit"], r"^[0-9a-f]{40}$")
            if profile["moode_version"] != "10.3.6":
                for renderer in profile["renderers"].values():
                    self.assertEqual(renderer["validated_models"], [])

    def test_corrected_1020_image_uses_the_same_renderer_profile(self):
        self.assertEqual(cli.select_profile("r1020fix", "3b+"), cli.select_profile("r1020", "3b+"))

    def test_alias_selects_exact_moode_package(self):
        profile = cli.select_profile("r1036", "3b+")
        self.assertEqual(profile, cli.select_profile("10.3.6", "3b+"))
        self.assertEqual(profile["packages"][0]["package_version"], "0.8.0-1moode1")
        self.assertEqual(profile["target"], "aarch64-unknown-linux-gnu")

    def test_unsupported_targets_are_rejected(self):
        for version, model in [("9.4.2", "3b+"), ("10.3.6", "zero"), ("10.3.6", "2b")]:
            with self.subTest(version=version, model=model), self.assertRaises(ValueError):
                cli.select_profile(version, model)

    def test_airplay_versions_and_timing_daemon(self):
        expected = {"10.2.0": "5.0.4", "10.3.1": "5.0.4", "10.3.2": "5.2.1",
                    "10.3.3": "5.2.1", "10.3.4": "5.5.1", "10.3.5": "5.5.2", "10.3.6": "5.5.2"}
        for version, shairport in expected.items():
            with self.subTest(version=version):
                packages = cli.select_profile(version, "3b+", "airplay")["packages"]
                self.assertEqual([(p["name"], p["package_version"]) for p in packages],
                                 [("shairport-sync", shairport + "-1moode1"), ("nqptp", "1.2.6-1moode1")])

    def test_qobuz_availability_and_rename(self):
        for profile in cli.profiles():
            version = profile["moode_version"]
            if tuple(map(int, version.split("."))) < (10, 3, 4):
                with self.assertRaisesRegex(ValueError, "unavailable"):
                    cli.select_profile(version, "3b+", "qobuz")
            else:
                package = cli.select_profile(version, "3b+", "qobuz")["packages"][0]
                self.assertEqual(package["name"], "qbzd" if version == "10.3.4" else "pibuz")

    def test_spotify_alias_is_backwards_compatible(self):
        self.assertEqual(cli.select_profile("r1036", "3b+", "spotify"), cli.select_profile("10.3.6", "3b+"))

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

    def test_airplay_second_component_failure_discards_first_package(self):
        with tempfile.TemporaryDirectory() as output:
            args = type("Args", (), dict(moode_version="10.3.6", pi_model="3b+",
                                        renderer="airplay", output=output, jobs=1))()
            class FailedSecondComponent:
                stdout = ["nqptp failed after shairport-sync was packaged\n"]
                def wait(self):
                    return 1
            def start_worker(command, **kwargs):
                stage = Path(command[command.index("--stage") + 1])
                (stage / "shairport-sync_5.5.2-1moode1_arm64.deb").write_bytes(b"first package")
                return FailedSecondComponent()
            with patch.object(cli.subprocess, "Popen", side_effect=start_worker), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, "Build failed"):
                    cli.build(args)
            self.assertEqual([p.name for p in Path(output).iterdir()], ["build.failed.log"])

    def test_unavailable_renderer_fails_without_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            result = subprocess.run([sys.executable, str(ROOT / "compiler/cli.py"), "build",
                                     "--pi-model", "3b+", "--moode-version", "10.3.3",
                                     "--renderer", "qobuz", "--output", str(output)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unavailable", result.stderr)
            self.assertFalse(output.exists())

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
