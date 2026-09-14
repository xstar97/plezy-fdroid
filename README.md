# Plezy F-Droid Mirror

This repository mirrors Android releases from [`edde746/plezy`](https://github.com/edde746/plezy) into an F-Droid-compatible repository.

## What it does

- Discovers upstream GitHub Releases using the GitHub API.
- Selects the latest 10 Plezy Android releases by default.
- Downloads `plezy-android-*.tar.gz` release assets and verifies GitHub-provided SHA256 digests when available.
- Securely extracts APKs (with tar path traversal protection).
- Inspects APK metadata from the APK itself (package ID, versionName, versionCode, minSdkVersion, targetSdkVersion, supported ABI).
- Generates F-Droid index metadata using `fdroid update --create-metadata`.
- Publishes the repository via GitHub Pages.

The detected Plezy Android package ID is `com.edde746.plezy`.

## Repository URL for F-Droid clients

After GitHub Pages is enabled, the repository URL is:

```text
https://<github-user>.github.io/plezy-fdroid/repo
```

## Supported architectures

The mirror currently tracks Android assets such as:

- `arm64-v8a`
- `armeabi-v7a`
- `x86_64`

Architecture discovery is dynamic, so added/removed upstream Android architectures are handled automatically.

## Version policy

- Automatic workflow: newest **10** upstream Plezy releases containing Android assets.
- Manual workflow: request specific older/newer versions, optionally combined with latest 10.

## Workflows

### Automatic sync

Workflow: `.github/workflows/update-fdroid.yml`

- Runs daily.
- Also supports manual trigger.
- Builds latest 10 valid Android releases and publishes to GitHub Pages.

### Manual custom generation

Workflow: `.github/workflows/build-custom-version.yml`

`workflow_dispatch` inputs:

- `version`: single tag (example: `v1.5.0` or `2.19.1`)
- `versions`: comma-separated tags (example: `v1.5.0,v1.8.2,v1.11.1`)
- `include_latest` (boolean, default `true`)
- `include_prereleases` (boolean, default `false`)
- `publish_to_pages` (boolean, default `false`)

If `include_latest=true`, output includes:

- latest 10 Android-capable releases
- plus all requested manual versions

Manual runs always upload a `custom-fdroid-repo` workflow artifact.
Set `publish_to_pages=true` only when you intentionally want that custom build deployed to the GitHub Pages URL.

## Signing key setup (required)

F-Droid repository metadata must be signed with a persistent key.

Do **not** commit private keys to Git.

### 1) Generate keystore once

Example:

```bash
keytool -genkeypair \
  -keystore fdroid-keystore.jks \
  -alias fdroid \
  -keyalg RSA \
  -keysize 4096 \
  -validity 36500
```

### 2) Add GitHub Secrets

Repository secrets required by workflows:

- `FDROID_KEYSTORE_B64` (base64 of the `.jks` file)
- `FDROID_KEYSTORE_PASSWORD`
- `FDROID_KEY_ALIAS`
- `FDROID_KEY_PASSWORD`
- `FDROID_REPO_NAME` (optional display name)

Create base64:

```bash
base64 -w0 fdroid-keystore.jks
```

### 3) Workflow restore process

Each workflow run:

1. Decodes `FDROID_KEYSTORE_B64` to `/tmp/fdroid-keystore.jks`
2. Writes `fdroid/config.yml` using secret credentials
3. Runs `fdroid update --create-metadata`

This reuses the same signing identity across all updates.

## Scripts

- `scripts/discover_releases.py`
- `scripts/download_release.py`
- `scripts/extract_android.py`
- `scripts/inspect_apk.py`
- `scripts/build_repo.py`
- `scripts/prune_versions.py`

Examples:

```bash
python scripts/build_repo.py --latest 10
```

```bash
python scripts/build_repo.py --latest 10 --include-version v1.5.0
```

```bash
python scripts/build_repo.py --latest 10 --include-version v1.5.0 --include-version v1.8.2
```

The build script logs release, architecture, output APK name, package, versionName, versionCode, and SHA256.
