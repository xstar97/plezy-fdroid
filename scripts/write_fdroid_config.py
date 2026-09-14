#!/usr/bin/env python3
"""Write fdroid/config.yml with signing settings from workflow environment."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml


def clean(value: str) -> str:
    return value.rstrip("\r\n")


def detect_keystore_type(keystore_path: str, keystore_password: str) -> str:
    env = {**os.environ, "LC_ALL": "C", "LANG": "C", "FDROID_KEYSTORE_PASSWORD": keystore_password}
    result = subprocess.run(
        [
            "keytool",
            "-list",
            "-keystore",
            keystore_path,
            "-storepass:env",
            "FDROID_KEYSTORE_PASSWORD",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    for line in result.stdout.splitlines():
        if line.startswith("Keystore type:"):
            keystore_type = line.split(":", 1)[1].strip().upper()
            if keystore_type:
                return keystore_type

    raise ValueError("Unable to determine keystore type from keytool output")


def main() -> None:
    keystore_path = os.environ["FDROID_KEYSTORE_PATH"]
    keystore_password = os.environ["FDROID_KEYSTORE_PASSWORD"]
    configured_key_password = os.environ.get("FDROID_KEY_PASSWORD", "")
    key_alias = clean(os.environ["FDROID_KEY_ALIAS"])
    repo_name = clean(os.environ["REPO_NAME"])
    repo_url = os.environ["REPO_URL"]
    config_path = Path(os.environ.get("FDROID_CONFIG_PATH", "fdroid/config.yml"))

    if not keystore_password:
        raise ValueError("FDROID_KEYSTORE_PASSWORD resolves to empty")
    if not key_alias:
        raise ValueError("FDROID_KEY_ALIAS resolves to empty after newline trimming")
    if not repo_name:
        raise ValueError("REPO_NAME resolves to empty after newline trimming")

    keystore_type = detect_keystore_type(keystore_path, keystore_password)
    if keystore_type == "PKCS12":
        if configured_key_password and configured_key_password != keystore_password:
            print(
                "::warning::FDROID_KEY_PASSWORD differs from the PKCS12 key password. "
                "Using FDROID_KEYSTORE_PASSWORD for keypass."
            )
        key_password = keystore_password
    else:
        key_password = configured_key_password
        if not key_password:
            raise ValueError("FDROID_KEY_PASSWORD is required for non-PKCS12 keystores")

    config = {
        "repo_name": repo_name,
        "repo_url": repo_url,
        "repo_description": "Mirror of Android Plezy releases from edde746/plezy",
        "archive_older": 0,
        "keystore": keystore_path,
        "keystorepass": keystore_password,
        "keypass": key_password,
        "repo_keyalias": key_alias,
        "make_current_version_link": False,
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_text = yaml.safe_dump(config, sort_keys=False)
    fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(config_text)
    os.chmod(config_path, 0o600)


if __name__ == "__main__":
    main()
