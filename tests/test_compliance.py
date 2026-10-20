import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("compliance", Path(__file__).resolve().parent.parent / "compiler/compliance.py")
compliance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compliance)


class InlineNoticeTests(unittest.TestCase):
    def test_inline_bsd_notice_retains_complete_original_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "alac.c"
            source.write_text("/* Copyright holder\nRedistribution in source and binary forms is permitted.\n*/\nint main(void) {}\n")
            self.assertEqual(list(compliance.notice_files(root)), [])
            self.assertEqual(list(compliance.inline_notice_files(root)), [source])

    def test_spdx_and_permission_notices_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in (("a.rs", "// SPDX-License-Identifier: MIT\n"),
                               ("b.c", "/* Permission is hereby granted ... */\n")):
                (root / name).write_text(text)
            self.assertEqual({p.name for p in compliance.inline_notice_files(root)}, {"a.rs", "b.c"})

    def test_binary_and_named_license_files_are_not_duplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "LICENSE").write_text("Copyright holder")
            (root / "binary").write_bytes(b"Copyright\x00binary")
            (root / "plain.c").write_text("int value = 0;\n")
            self.assertEqual(list(compliance.inline_notice_files(root)), [])
