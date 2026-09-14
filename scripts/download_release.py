from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import download_with_cache, expected_sha_from_digest, fetch_release_by_tag


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Plezy Android release archives")
    parser.add_argument("--owner", default="edde746")
    parser.add_argument("--repo", default="plezy")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/plezy/releases"))
    parser.add_argument("--include-prereleases", action="store_true")
    args = parser.parse_args()

    release = fetch_release_by_tag(
        owner=args.owner,
        repo=args.repo,
        tag=args.tag,
        include_prereleases=args.include_prereleases,
    )

    output = []
    for asset in release.assets:
        destination = args.cache_dir / release.tag / asset.name
        downloaded = download_with_cache(
            asset.url,
            destination,
            expected_sha256=expected_sha_from_digest(asset.digest),
        )
        output.append(
            {
                "tag": release.tag,
                "asset": asset.name,
                "arch": asset.arch,
                "path": str(downloaded),
                "digest": asset.digest,
            }
        )

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
