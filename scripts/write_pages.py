"""Write GitHub Pages landing files for the published F-Droid repository."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit


ROOT_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Plezy F-Droid Mirror</title>
    <style>
      :root {{
        color-scheme: light dark;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}

      body {{
        margin: 0;
        padding: 2rem;
        line-height: 1.5;
      }}

      main {{
        max-width: 48rem;
        margin: 0 auto;
      }}

      code,
      a.button {{
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      }}

      a.button {{
        display: inline-block;
        margin-top: 1rem;
        padding: 0.75rem 1rem;
        border: 1px solid currentColor;
        border-radius: 0.5rem;
        text-decoration: none;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>Plezy F-Droid Mirror</h1>
      <p>This GitHub Pages site publishes the F-Droid repository for Plezy Android releases.</p>
      <p>Use the repository URL below in an F-Droid client:</p>
      <p><code>{repo_url}</code></p>
      <p><a class="button" href="./repo/">Open repository endpoint</a></p>
    </main>
  </body>
</html>
"""


REPO_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Plezy F-Droid Repository</title>
    <style>
      :root {{
        color-scheme: light dark;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}

      body {{
        margin: 0;
        padding: 2rem;
        line-height: 1.5;
      }}

      main {{
        max-width: 48rem;
        margin: 0 auto;
      }}

      code {{
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>Plezy F-Droid Repository</h1>
      <p>This path hosts the signed F-Droid metadata and APK files for Plezy.</p>
      <p>Add this URL to an F-Droid client:</p>
      <p><code>{repo_url}</code></p>
      <ul>
        <li><a href="./index-v1.json">index-v1.json</a></li>
        <li><a href="./index-v1.jar">index-v1.jar</a></li>
        <li><a href="./build-report.json">build-report.json</a></li>
      </ul>
    </main>
  </body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write GitHub Pages landing files")
    parser.add_argument(
        "--fdroid-dir",
        type=Path,
        default=Path("fdroid"),
        help="F-Droid site directory where .nojekyll plus root/repo landing pages are written.",
    )
    parser.add_argument(
        "--pages-base-url",
        required=True,
        help="Configured GitHub Pages site base URL, for example https://xstar97.github.io/plezy-fdroid.",
    )
    return parser.parse_args()


def normalize_pages_base_url(pages_base_url: str) -> str:
    parts = urlsplit(pages_base_url.strip())
    normalized_path = unquote(parts.path).rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, normalized_path, "", ""))


def main() -> None:
    args = parse_args()
    repo_dir = args.fdroid_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    pages_base_url = normalize_pages_base_url(args.pages_base_url)
    repo_url = f"{pages_base_url}/repo"
    escaped_repo_url = escape(repo_url, quote=True)

    (args.fdroid_dir / ".nojekyll").write_text("", encoding="utf-8")
    (args.fdroid_dir / "index.html").write_text(
        ROOT_TEMPLATE.format(repo_url=escaped_repo_url) + "\n",
        encoding="utf-8",
    )
    (repo_dir / "index.html").write_text(
        REPO_TEMPLATE.format(repo_url=escaped_repo_url) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
