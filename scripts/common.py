from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

GITHUB_API = "https://api.github.com"
ANDROID_ASSET_PATTERN = re.compile(r"^plezy-android-(?P<arch>[^/]+)\\.tar\\.gz$")


@dataclass(frozen=True)
class AssetInfo:
    name: str
    arch: str
    url: str
    digest: str | None
    size: int


@dataclass(frozen=True)
class ReleaseInfo:
    tag: str
    published_at: str
    prerelease: bool
    assets: tuple[AssetInfo, ...]


@dataclass(frozen=True)
class ApkMetadata:
    package: str
    version_name: str
    version_code: int
    min_sdk: str | None
    target_sdk: str | None
    supported_abis: tuple[str, ...]
    sha256: str


def github_get(path: str, token: str | None = None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "plezy-fdroid-mirror",
    }
    auth_token = token or os.environ.get("GITHUB_TOKEN")
    if auth_token:
        headers["Authorization"] = "token " + auth_token
    request = Request(f"{GITHUB_API}{path}", headers=headers)
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def _release_from_api_item(item: dict[str, Any]) -> ReleaseInfo | None:
    if item.get("draft"):
        return None

    assets: list[AssetInfo] = []
    for asset in item.get("assets", []):
        name = asset.get("name", "")
        match = ANDROID_ASSET_PATTERN.match(name)
        if not match:
            continue
        assets.append(
            AssetInfo(
                name=name,
                arch=match.group("arch"),
                url=asset["browser_download_url"],
                digest=asset.get("digest"),
                size=int(asset.get("size", 0)),
            )
        )

    if not assets:
        return None

    return ReleaseInfo(
        tag=str(item["tag_name"]),
        published_at=str(item["published_at"]),
        prerelease=bool(item.get("prerelease", False)),
        assets=tuple(sorted(assets, key=lambda a: a.arch)),
    )


def list_android_releases(
    owner: str,
    repo: str,
    include_prereleases: bool = False,
    per_page: int = 100,
) -> list[ReleaseInfo]:
    page = 1
    releases: list[ReleaseInfo] = []

    while True:
        data = github_get(
            f"/repos/{owner}/{repo}/releases?per_page={per_page}&page={page}"
        )
        if not data:
            break

        for item in data:
            release = _release_from_api_item(item)
            if release is None:
                continue
            if release.prerelease and not include_prereleases:
                continue
            releases.append(release)

        page += 1

    releases.sort(key=lambda r: r.published_at, reverse=True)
    return releases


def normalize_tag(tag: str) -> str:
    tag = tag.strip()
    if tag.startswith("refs/tags/"):
        tag = tag[len("refs/tags/") :]
    return tag


def fetch_release_by_tag(
    owner: str,
    repo: str,
    tag: str,
    include_prereleases: bool = False,
) -> ReleaseInfo:
    candidates = [normalize_tag(tag)]
    if candidates[0].startswith("v"):
        candidates.append(candidates[0][1:])
    else:
        candidates.append(f"v{candidates[0]}")

    last_error: Exception | None = None
    for candidate in dict.fromkeys(candidates):
        try:
            item = github_get(f"/repos/{owner}/{repo}/releases/tags/{quote(candidate)}")
            release = _release_from_api_item(item)
            if release is None:
                raise ValueError(
                    f"Release '{candidate}' exists but has no Plezy Android assets"
                )
            if release.prerelease and not include_prereleases:
                raise ValueError(
                    f"Release '{candidate}' is a prerelease; enable prereleases to include it"
                )
            return release
        except HTTPError as error:
            if error.code != 404:
                raise
            last_error = error
            continue

    raise ValueError(f"Could not find release tag '{tag}'") from last_error


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_with_cache(url: str, destination: Path, expected_sha256: str | None = None) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        actual = sha256_file(destination)
        if expected_sha256 and actual != expected_sha256:
            destination.unlink()
        else:
            return destination

    with tempfile.NamedTemporaryFile(delete=False, dir=str(destination.parent)) as tmp:
        tmp_path = Path(tmp.name)
        request = Request(url)
        with urlopen(request) as response:
            shutil.copyfileobj(response, tmp)

    if expected_sha256:
        actual = sha256_file(tmp_path)
        if actual != expected_sha256:
            tmp_path.unlink(missing_ok=True)
            raise ValueError(
                f"Checksum mismatch for {url}: expected {expected_sha256}, got {actual}"
            )

    tmp_path.replace(destination)
    return destination


def expected_sha_from_digest(digest: str | None) -> str | None:
    if not digest:
        return None
    if digest.startswith("sha256:"):
        return digest.split(":", 1)[1]
    return None


def extract_single_apk(archive_path: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)

    try:
        tar = tarfile.open(archive_path, mode="r:gz")
    except tarfile.TarError as error:
        raise ValueError(f"Corrupt archive: {archive_path}") from error

    apk_members = []
    with tar:
        for member in tar.getmembers():
            member_path = PurePosixPath(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe archive path detected: {member.name}")
            if member.isfile() and member_path.name.endswith(".apk"):
                apk_members.append(member)

        if not apk_members:
            raise ValueError(f"No APK file found in archive: {archive_path}")
        if len(apk_members) > 1:
            names = ", ".join(member.name for member in apk_members)
            raise ValueError(f"Expected exactly one APK in {archive_path}, found: {names}")
        apk_member = apk_members[0]

        fileobj = tar.extractfile(apk_member)
        if fileobj is None:
            raise ValueError(f"Failed to extract APK from archive: {archive_path}")

        output_path = destination_dir / apk_member_path_name(apk_member.name)
        with fileobj, output_path.open("wb") as out:
            shutil.copyfileobj(fileobj, out)

    return output_path


def apk_member_path_name(name: str) -> str:
    return PurePosixPath(name).name


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
