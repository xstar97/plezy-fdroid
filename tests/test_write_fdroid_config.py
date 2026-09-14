import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "write_fdroid_config.py"
SPEC = importlib.util.spec_from_file_location("write_fdroid_config", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DetectKeystoreTypeTests(unittest.TestCase):
    @mock.patch.object(MODULE.subprocess, "run")
    def test_detect_keystore_type_parses_keytool_output(self, run_mock):
        run_mock.return_value = mock.Mock(stdout="Keystore type: PKCS12\n")

        result = MODULE.detect_keystore_type("/tmp/test.jks", "store-pass")

        self.assertEqual(result, "PKCS12")
        args = run_mock.call_args.args[0]
        self.assertIn("-storepass:env", args)
        self.assertEqual(args[-1], "FDROID_KEYSTORE_PASSWORD")

    @mock.patch.object(MODULE.subprocess, "run")
    def test_detect_keystore_type_requires_parseable_output(self, run_mock):
        run_mock.return_value = mock.Mock(stdout="unexpected output\n")

        with self.assertRaisesRegex(ValueError, "Unable to determine keystore type"):
            MODULE.detect_keystore_type("/tmp/test.jks", "store-pass")

    @mock.patch.object(MODULE.subprocess, "run")
    def test_detect_keystore_type_includes_keytool_stderr(self, run_mock):
        run_mock.side_effect = MODULE.subprocess.CalledProcessError(
            returncode=1, cmd=["keytool"], stderr="keystore tampered with, or password was incorrect"
        )

        with self.assertRaisesRegex(ValueError, "keystore tampered"):
            MODULE.detect_keystore_type("/tmp/test.jks", "store-pass")


class MainTests(unittest.TestCase):
    def test_main_uses_store_password_for_pkcs12(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yml"
            env = {
                "FDROID_KEYSTORE_PATH": "/tmp/fdroid-keystore.jks",
                "FDROID_KEYSTORE_PASSWORD": "store-pass",
                "FDROID_KEY_PASSWORD": "different-key-pass",
                "FDROID_KEY_ALIAS": "alias\r\n",
                "REPO_NAME": "Repo Name\r\n",
                "REPO_URL": "https://example.com/repo",
                "FDROID_CONFIG_PATH": str(config_path),
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
                MODULE, "detect_keystore_type", return_value="PKCS12"
            ), mock.patch("builtins.print") as print_mock:
                MODULE.main()

            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["keypass"], "store-pass")
            self.assertEqual(config["repo_keyalias"], "alias")
            self.assertEqual(config["repo_name"], "Repo Name")
            self.assertEqual(config["repo_icon"], "icon.png")
            self.assertIn("FDROID_KEY_PASSWORD differs", print_mock.call_args.args[0])
            self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), 0o600)

    def test_main_requires_key_password_for_non_pkcs12(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yml"
            env = {
                "FDROID_KEYSTORE_PATH": "/tmp/fdroid-keystore.jks",
                "FDROID_KEYSTORE_PASSWORD": "store-pass",
                "FDROID_KEY_ALIAS": "alias",
                "REPO_NAME": "Repo Name",
                "REPO_URL": "https://example.com/repo",
                "FDROID_CONFIG_PATH": str(config_path),
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
                MODULE, "detect_keystore_type", return_value="JKS"
            ):
                with self.assertRaisesRegex(ValueError, "FDROID_KEY_PASSWORD is required"):
                    MODULE.main()

    def test_main_preserves_key_password_for_non_pkcs12(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yml"
            env = {
                "FDROID_KEYSTORE_PATH": "/tmp/fdroid-keystore.jks",
                "FDROID_KEYSTORE_PASSWORD": "store-pass",
                "FDROID_KEY_PASSWORD": "separate-key-pass",
                "FDROID_KEY_ALIAS": "alias",
                "REPO_NAME": "Repo Name",
                "REPO_URL": "https://example.com/repo",
                "FDROID_CONFIG_PATH": str(config_path),
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
                MODULE, "detect_keystore_type", return_value="JKS"
            ):
                MODULE.main()

            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["keypass"], "separate-key-pass")

    def test_main_rejects_symlink_config_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_path = Path(tmp) / "target.yml"
            target_path.write_text("", encoding="utf-8")
            config_path = Path(tmp) / "config.yml"
            config_path.symlink_to(target_path)
            env = {
                "FDROID_KEYSTORE_PATH": "/tmp/fdroid-keystore.jks",
                "FDROID_KEYSTORE_PASSWORD": "store-pass",
                "FDROID_KEY_ALIAS": "alias",
                "REPO_NAME": "Repo Name",
                "REPO_URL": "https://example.com/repo",
                "FDROID_CONFIG_PATH": str(config_path),
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
                MODULE, "detect_keystore_type", return_value="PKCS12"
            ):
                with self.assertRaisesRegex(ValueError, "must not be a symlink"):
                    MODULE.main()


if __name__ == "__main__":
    unittest.main()
