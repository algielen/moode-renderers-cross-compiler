import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("license_policy", Path(__file__).resolve().parent.parent / "compiler/license_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class LicenseSelectionTests(unittest.TestCase):
    def test_offered_mit_is_preferred(self):
        self.assertEqual(policy.select_license("MIT OR Apache-2.0 OR LGPL-2.1-or-later"), "MIT")
        self.assertEqual(policy.select_license("Apache-2.0/MIT"), "MIT")

    def test_every_and_obligation_is_kept(self):
        self.assertEqual(policy.select_license("(MIT OR Apache-2.0) AND Unicode-3.0"), "MIT AND Unicode-3.0")
        self.assertIsNone(policy.select_license("MIT AND LicenseRef-Unknown"))

    def test_mpl_alternative_is_explicit(self):
        self.assertEqual(policy.select_license("LGPL-3.0-or-later OR MPL-2.0"), "MPL-2.0")

    def test_exceptions_are_not_dropped(self):
        self.assertEqual(policy.select_license("Apache-2.0 WITH LLVM-exception"), "Apache-2.0 WITH LLVM-exception")
        self.assertIsNone(policy.select_license("Apache-2.0 WITH Unknown-exception"))

    def test_gpl_and_custom_license_choices_require_review(self):
        self.assertIsNone(policy.select_license("GPL-3.0-only OR LicenseRef-Commercial"))
        self.assertIsNone(policy.select_license(None))

    def test_invalid_expression_is_not_partially_accepted(self):
        for expression in ("MIT OR", "(MIT", "MIT) OR Apache-2.0", "MIT / Unknown", "MIT OR ( )", "MIT @ Apache-2.0"):
            with self.subTest(expression=expression):
                self.assertIsNone(policy.select_license(expression))
