from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import write_pages


class NormalizePagesBaseUrlTests(unittest.TestCase):
    def test_trims_trailing_slash(self) -> None:
        self.assertEqual(
            write_pages.normalize_pages_base_url("https://xstar97.github.io/plezy-fdroid/"),
            "https://xstar97.github.io/plezy-fdroid",
        )

    def test_preserves_encoded_path(self) -> None:
        self.assertEqual(
            write_pages.normalize_pages_base_url("https://example.com/plezy%20fdroid/"),
            "https://example.com/plezy%20fdroid",
        )

    def test_rejects_relative_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "absolute URL"):
            write_pages.normalize_pages_base_url("/plezy-fdroid")


class WritePagesOutputTests(unittest.TestCase):
    def test_writes_expected_pages_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fdroid_dir = Path(tmp) / "fdroid"
            repo_url = "https://xstar97.github.io/plezy-fdroid/repo"

            original_argv = sys.argv
            try:
                sys.argv = [
                    "write_pages.py",
                    "--fdroid-dir",
                    str(fdroid_dir),
                    "--pages-base-url",
                    "https://xstar97.github.io/plezy-fdroid/",
                ]
                write_pages.main()
            finally:
                sys.argv = original_argv

            self.assertTrue((fdroid_dir / ".nojekyll").exists())
            self.assertIn(repo_url, (fdroid_dir / "index.html").read_text(encoding="utf-8"))
            self.assertIn(
                repo_url,
                (fdroid_dir / "repo" / "index.html").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "../build-report.json",
                (fdroid_dir / "repo" / "index.html").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
