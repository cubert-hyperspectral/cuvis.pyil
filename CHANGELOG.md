# Changelog

All notable changes to the `cuvis-il` Python interface layer are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Entry wording follows the conventions in [CONTRIBUTING.md](CONTRIBUTING.md#changelog-conventions).

Versions are `GENERATION.MAJOR.MINOR.PATCH`.
`GENERATION.MAJOR.MINOR` is the cuvis SDK release the interface layer is compiled against; `PATCH` counts revisions against that same SDK.
See [CONTRIBUTING.md](CONTRIBUTING.md#version-scheme) for the full scheme.

Releases before 3.5.3.0 predate this file and are documented on the [GitHub releases page](https://github.com/cubert-hyperspectral/cuvis.pyil/releases).
Pre-releases (`b*`, `rc*`) are not listed.

## [Unreleased]

### Added

- `CI` - `.github/workflows/release.yml` is driven by `v*.*.*.*` tags: it validates the tag against `pyproject.toml`, this file and the `cuvis_base` images, builds the wheels, publishes to TestPyPI and PyPI, pushes the `cubertgmbh/cuvis_pyil` images, and creates a GitHub Release with the matching section here as notes.
  Pre-release tags (`a`, `b`, `rc` suffix) publish to PyPI as pre-releases and push the images but create no GitHub Release.
- `CI` - `.github/scripts/build_matrix.py` builds wheels and images only for the variants whose `cuvis_base` image exists; a pre-release finishes with a warning for the missing ones, a final release fails.
- `CI` - `.github/workflows/ci.yml` runs the build and smoke tests on every pull request and push to `develop` and `main`, and requires a changelog entry per pull request.
  It builds and tests on Ubuntu 22.04, 24.04 and 26.04, matching the released image variants; 26.04 is amd64 only.
- `docker/Dockerfile`, `docker-bake.hcl` - build `cubertgmbh/cuvis_pyil:<sdk>-ubuntu<22.04|24.04|26.04>[-arm64]` from `cuvis_base` and the wheels of the same release, in a virtual environment at `/opt/venv`.
  Ubuntu 26.04 exists for amd64 only and installs the 24.04 wheel.
  The image was previously built by cuvis.docker from a clone of `main`.
- `CHANGELOG.md`, `CONTRIBUTING.md` - this file and the version, changelog and release conventions.
- `cuvis_il` - reports the SDK version it was built against, the library version it loaded and the symbols that library lacks, so a mismatch between the installed SDK and the interface layer raises a descriptive error instead of failing at import.

### Changed

- `cuvis.swig` - submodule advanced: the interface layer releases the GIL around SDK calls, string arguments are passed without copies, and reference-spectrum handling uses the struct-based shims with the white and target reference-spectrum names.
- `cuvis.swig` - submodule advanced: the calibration wavelength reader tolerates a null pointer.

### Removed

- Python 3.9 support dropped; `requires-python` is now `>=3.10`, and no 3.9 wheels are built or tested.
- `CI` - `.github/workflows/publish_version.yml` and `.github/workflows/build_and_test.yml` removed; their jobs moved into `release.yml` and `ci.yml`.
- `build_and_upload_linux.sh`, `build_and_upload_win.sh`, `build_dispatcher_win.sh` - removed; they duplicated the workflow build and uploaded with a pasted token.

## [3.5.3.2] - 2026-06-22

Compiled against cuvis SDK 3.5.3.

### Added

- Wheels for Windows on Python 3.10 to 3.14, built by the publish workflow.

## [3.5.3.1] - 2026-06-02

Compiled against cuvis SDK 3.5.3.

### Added

- Wheels for arm64 on Ubuntu 22.04 and 24.04.

### Fixed

- `CI` - the publish workflow could not be dispatched manually.

## [3.5.3.0] - 2026-06-01

Compiled against cuvis SDK 3.5.3.
