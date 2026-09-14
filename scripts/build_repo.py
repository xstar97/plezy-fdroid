from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from common import (
    AssetInfo,
    ReleaseInfo,
    download_with_cache,
    expected_sha_from_digest,
    extract_single_apk,
    fetch_release_by_tag,
    list_android_releases,
)
from inspect_apk import inspect_apk

DEFAULT_ARCHES = {"arm64-v8a", "armeabi-v7a", "x86_64"}
REPO_ICON_NAME = "plezy.png"
REPO_ICON_FALLBACK_URL = "https://cdn.jsdelivr.net/gh/selfhst/icons@main/png/plezy.png"
REPO_ICON_FALLBACK_SHA256 = "d7f9084479aa4034c7df277e52e1668a571473955f719aff6c815ab30869ba40"
LOCAL_REPO_ICON_CANDIDATES = (
    Path(REPO_ICON_NAME),
    Path("fdroid") / REPO_ICON_NAME,
)


def select_releases(
    owner: str,
    repo: str,
    latest: int,
    include_versions: list[str],
    include_prereleases: bool,
) -> list[ReleaseInfo]:
    selected: dict[str, ReleaseInfo] = {}

    if latest > 0:
        for release in list_android_releases(owner, repo, include_prereleases)[:latest]:
            selected[release.tag] = release

    for tag in include_versions:
        release = fetch_release_by_tag(owner, repo, tag, include_prereleases)
        selected[release.tag] = release

    releases = list(selected.values())
    releases.sort(key=lambda r: r.published_at, reverse=True)
    return releases


def clear_repo_apks(repo_dir: Path) -> None:
    repo_dir.mkdir(parents=True, exist_ok=True)
    for apk_file in repo_dir.glob("*.apk"):
        apk_file.unlink()


def copy_apk_to_repo(apk_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(apk_path, output_path)


def ensure_repo_icon(repo_dir: Path, project_dir: Path | None = None) -> None:
    icon_path = repo_dir / "icons" / REPO_ICON_NAME
    if icon_path.exists():
        return

    icon_path.parent.mkdir(parents=True, exist_ok=True)
    root_dir = project_dir or Path(__file__).resolve().parents[1]
    for relative_icon_path in LOCAL_REPO_ICON_CANDIDATES:
        legacy_icon_path = root_dir / relative_icon_path
        if not legacy_icon_path.exists():
            continue
        shutil.copy2(legacy_icon_path, icon_path)
        print(f"[icon] Copied legacy repo icon from {legacy_icon_path} to {icon_path}")
        return

    with tempfile.TemporaryDirectory() as tmp:
        downloaded_icon_path = Path(tmp) / REPO_ICON_NAME
        download_with_cache(
            REPO_ICON_FALLBACK_URL,
            downloaded_icon_path,
            expected_sha256=REPO_ICON_FALLBACK_SHA256,
        )
        downloaded_icon_path.replace(icon_path)
    print(f"[icon] Downloaded fallback repo icon to {icon_path}")


def process_release(
    release: ReleaseInfo,
    cache_dir: Path,
    repo_dir: Path,
    seen_version_codes: dict[tuple[str, int, str], str],
) -> list[dict[str, object]]:
    artifacts: list[dict[str, object]] = []
    release_arches = {asset.arch for asset in release.assets}
    missing_expected = sorted(DEFAULT_ARCHES - release_arches)
    if missing_expected:
        print(
            f"[warn] {release.tag} missing expected Android assets: {', '.join(missing_expected)}"
        )

    for asset in release.assets:
        artifact = process_asset(release, asset, cache_dir, repo_dir, seen_version_codes)
        artifacts.append(artifact)

    return artifacts


def process_asset(
    release: ReleaseInfo,
    asset: AssetInfo,
    cache_dir: Path,
    repo_dir: Path,
    seen_version_codes: dict[tuple[str, int, str], str],
) -> dict[str, object]:
    expected_sha256 = expected_sha_from_digest(asset.digest)
    archive_path = cache_dir / "archives" / release.tag / asset.name
    download_with_cache(asset.url, archive_path, expected_sha256=expected_sha256)

    with tempfile.TemporaryDirectory() as tmp:
        extracted_apk = extract_single_apk(archive_path, Path(tmp))
        metadata = inspect_apk(extracted_apk)
        output_name = f"{metadata.package}_{metadata.version_code}_{asset.arch}.apk"
        output_path = repo_dir / output_name

        version_key = (metadata.package, metadata.version_code, asset.arch)
        prior_sha = seen_version_codes.get(version_key)
        if prior_sha and prior_sha != metadata.sha256:
            raise ValueError(
                "Conflicting APK content for "
                f"{metadata.package} versionCode={metadata.version_code} arch={asset.arch}"
            )
        seen_version_codes[version_key] = metadata.sha256

        copy_apk_to_repo(extracted_apk, output_path)

    if metadata.supported_abis and asset.arch not in metadata.supported_abis:
        print(
            f"[warn] ABI mismatch for {release.tag}: asset arch={asset.arch}, "
            f"apk abis={','.join(metadata.supported_abis)}"
        )

    print(
        "[apk]"
        f" release={release.tag}"
        f" arch={asset.arch}"
        f" file={output_name}"
        f" package={metadata.package}"
        f" versionName={metadata.version_name}"
        f" versionCode={metadata.version_code}"
        f" sha256={metadata.sha256}"
    )

    return {
        "release_tag": release.tag,
        "release_published_at": release.published_at,
        "asset_name": asset.name,
        "asset_arch": asset.arch,
        "asset_digest": asset.digest,
        "output_filename": output_name,
        "apk": {
            "package": metadata.package,
            "version_name": metadata.version_name,
            "version_code": metadata.version_code,
            "min_sdk": metadata.min_sdk,
            "target_sdk": metadata.target_sdk,
            "supported_abis": list(metadata.supported_abis),
            "sha256": metadata.sha256,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Plezy F-Droid APK set")
    parser.add_argument("--owner", default="edde746")
    parser.add_argument("--repo", default="plezy")
    parser.add_argument("--latest", type=int, default=3)
    parser.add_argument("--include-version", action="append", default=[])
    parser.add_argument("--include-prereleases", action="store_true")
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/plezy"))
    parser.add_argument("--fdroid-dir", type=Path, default=Path("fdroid"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("fdroid/build-report.json"),
        help="Output JSON report path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_dir = args.fdroid_dir / "repo"

    include_versions = [tag for tag in args.include_version if tag.strip()]
    releases = select_releases(
        owner=args.owner,
        repo=args.repo,
        latest=max(args.latest, 0),
        include_versions=include_versions,
        include_prereleases=args.include_prereleases,
    )
    if not releases:
        raise ValueError("No valid Plezy Android releases were selected")

    clear_repo_apks(repo_dir)
    ensure_repo_icon(repo_dir)

    all_artifacts: list[dict[str, object]] = []
    seen_version_codes: dict[tuple[str, int, str], str] = {}
    for release in releases:
        artifacts = process_release(
            release=release,
            cache_dir=args.cache_dir,
            repo_dir=repo_dir,
            seen_version_codes=seen_version_codes,
        )
        all_artifacts.extend(artifacts)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(
            {
                "source": f"{args.owner}/{args.repo}",
                "latest": args.latest,
                "include_versions": include_versions,
                "include_prereleases": args.include_prereleases,
                "selected_releases": [release.tag for release in releases],
                "artifacts": all_artifacts,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[done] Wrote {len(all_artifacts)} APK artifacts for {len(releases)} releases")


if __name__ == "__main__":
    main()
