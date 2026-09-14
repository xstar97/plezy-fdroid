from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

inspect_apk_stub = types.ModuleType("inspect_apk")
inspect_apk_stub.inspect_apk = mock.Mock()
sys.modules.setdefault("inspect_apk", inspect_apk_stub)

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_repo.py"
SPEC = importlib.util.spec_from_file_location("build_repo", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EnsureRepoIconTests(unittest.TestCase):
    def test_keeps_existing_repo_icon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "fdroid" / "repo"
            icon_path = repo_dir / "icons" / MODULE.REPO_ICON_NAME
            icon_path.parent.mkdir(parents=True, exist_ok=True)
            icon_path.write_bytes(b"existing")

            with mock.patch.object(MODULE, "download_with_cache") as download_mock:
                MODULE.ensure_repo_icon(repo_dir, project_dir=Path(tmp))

            self.assertEqual(icon_path.read_bytes(), b"existing")
            download_mock.assert_not_called()

    def test_copies_legacy_root_icon_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            repo_dir = project_dir / "fdroid" / "repo"
            legacy_icon_path = project_dir / MODULE.REPO_ICON_NAME
            legacy_icon_path.write_bytes(b"legacy")

            MODULE.ensure_repo_icon(repo_dir, project_dir=project_dir)

            self.assertEqual(
                (repo_dir / "icons" / MODULE.REPO_ICON_NAME).read_bytes(),
                b"legacy",
            )

    def test_downloads_fallback_icon_when_local_icon_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            repo_dir = project_dir / "fdroid" / "repo"
            icon_path = repo_dir / "icons" / MODULE.REPO_ICON_NAME

            def fake_download(url: str, destination: Path, expected_sha256: str | None = None) -> Path:
                self.assertEqual(url, MODULE.REPO_ICON_FALLBACK_URL)
                self.assertIsNone(expected_sha256)
                destination.write_bytes(b"downloaded")
                return destination

            with mock.patch.object(MODULE, "download_with_cache", side_effect=fake_download) as download_mock:
                MODULE.ensure_repo_icon(repo_dir, project_dir=project_dir)

            self.assertEqual(icon_path.read_bytes(), b"downloaded")
            download_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
