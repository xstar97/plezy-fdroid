from __future__ import annotations

import argparse
import json

from common import list_android_releases


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover Plezy Android releases")
    parser.add_argument("--owner", default="edde746")
    parser.add_argument("--repo", default="plezy")
    parser.add_argument("--latest", type=int, default=3)
    parser.add_argument("--include-prereleases", action="store_true")
    args = parser.parse_args()

    releases = list_android_releases(
        owner=args.owner,
        repo=args.repo,
        include_prereleases=args.include_prereleases,
    )

    selected = releases[: args.latest] if args.latest > 0 else releases
    print(
        json.dumps(
            [
                {
                    "tag": release.tag,
                    "published_at": release.published_at,
                    "architectures": [asset.arch for asset in release.assets],
                }
                for release in selected
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
