from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import common


class AndroidAssetPatternTests(unittest.TestCase):
    def test_matches_android_tarball_assets(self) -> None:
        match = common.ANDROID_ASSET_PATTERN.match("plezy-android-arm64-v8a.tar.gz")
        self.assertIsNotNone(match)
        self.assertEqual(match.group("arch"), "arm64-v8a")

    def test_rejects_non_android_assets(self) -> None:
        self.assertIsNone(common.ANDROID_ASSET_PATTERN.match("plezy-linux-x64.tar.gz"))


if __name__ == "__main__":
    unittest.main()
