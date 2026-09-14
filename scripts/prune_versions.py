from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prune APKs that are not in a build report")
    parser.add_argument("--repo-dir", type=Path, default=Path("fdroid/repo"))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    keep = {entry["output_filename"] for entry in report.get("artifacts", [])}

    removed = []
    for apk in args.repo_dir.glob("*.apk"):
        if apk.name not in keep:
            apk.unlink()
            removed.append(apk.name)

    print(json.dumps({"removed": removed, "kept": sorted(keep)}, indent=2))


if __name__ == "__main__":
    main()
