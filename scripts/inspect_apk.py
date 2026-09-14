from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from loguru import logger

from androguard.core.apk import APK

from common import ApkMetadata, sha256_file

logger.remove()


def inspect_apk(apk_path: Path) -> ApkMetadata:
    apk = APK(str(apk_path))
    package = apk.get_package()
    version_name = apk.get_androidversion_name()
    version_code_raw = apk.get_androidversion_code()
    min_sdk = apk.get_min_sdk_version()
    target_sdk = apk.get_target_sdk_version()

    if not package or not version_name or not version_code_raw:
        raise ValueError(f"Invalid APK metadata in {apk_path}")

    try:
        version_code = int(str(version_code_raw))
    except ValueError as error:
        raise ValueError(f"Invalid versionCode '{version_code_raw}' in {apk_path}") from error

    with zipfile.ZipFile(apk_path) as archive:
        abis = sorted(
            {
                part.split("/")[1]
                for part in archive.namelist()
                if part.startswith("lib/") and part.count("/") >= 2
            }
        )

    return ApkMetadata(
        package=package,
        version_name=str(version_name),
        version_code=version_code,
        min_sdk=str(min_sdk) if min_sdk else None,
        target_sdk=str(target_sdk) if target_sdk else None,
        supported_abis=tuple(abis),
        sha256=sha256_file(apk_path),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Android APK metadata")
    parser.add_argument("apk", type=Path)
    args = parser.parse_args()

    metadata = inspect_apk(args.apk)
    print(
        json.dumps(
            {
                "package": metadata.package,
                "versionName": metadata.version_name,
                "versionCode": metadata.version_code,
                "minSdkVersion": metadata.min_sdk,
                "targetSdkVersion": metadata.target_sdk,
                "supportedAbis": list(metadata.supported_abis),
                "sha256": metadata.sha256,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
