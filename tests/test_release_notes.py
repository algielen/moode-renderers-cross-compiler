import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("release_notes", Path(__file__).with_name("release_notes.py"))
notes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notes)


class ReleaseNotesTests(unittest.TestCase):
    def test_initial_profile_notes_omit_deferred_and_unavailable_renderers(self):
        profile = notes.profiles()["10.2.0"]
        result = notes.render(profile, "@MOODE_PROFILE@\n@PACKAGES@\n", limited=True)
        self.assertIn("10.2.0", result)
        self.assertIn("librespot", result)
        self.assertNotIn("shairport", result)
        self.assertNotIn("Qobuz Connect", result)
        self.assertIn("Full compatibility-matrix validation is still pending", result)
