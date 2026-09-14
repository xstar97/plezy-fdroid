from __future__ import annotations

import argparse
from pathlib import Path

from common import extract_single_apk


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Android APK from Plezy tar.gz")
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    apk_path = extract_single_apk(args.archive, args.destination)
    print(apk_path)


if __name__ == "__main__":
    main()
