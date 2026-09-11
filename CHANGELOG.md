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

## [3.6.0.0] - 2026-09-11

Compiled against cuvis SDK 3.6.0.

### Added

- `CI` - `.github/workflows/release.yml` is driven by `v*.*.*.*` tags: it validates the tag against `pyproject.toml`, this file and the `cuvis_base` images, builds the wheels, publishes to TestPyPI and PyPI, pushes the `cubertgmbh/cuvis_pyil` images, and creates a GitHub Release with the matching section here as notes.
  Pre-release tags (`a`, `b`, `rc` suffix) publish to PyPI as pre-releases and push the images but create no GitHub Release.
- `CI` - `.github/scripts/build_matrix.py` builds wheels and images only for the variants whose `cuvis_base` image exists; a pre-release finishes with a warning for the missing ones, a final release fails.
- `CI` - `release.yml` installs the published wheel from TestPyPI into every `cuvis_base` variant and imports it before promoting the release to PyPI, which is what allows one wheel to serve several Ubuntu releases.
- `CI` - `.github/workflows/ci.yml` runs the build and smoke tests on every pull request and push to `develop` and `main`, and requires a changelog entry per pull request.
  It builds and tests on every Ubuntu variant that has a `cuvis_base` image, so the tested platforms match the released image variants.
  A variant the SDK has not shipped is reported as a warning and skipped instead of failing the run.
- `docker/Dockerfile`, `docker-bake.hcl` - build `cubertgmbh/cuvis_pyil:<sdk>-ubuntu<22.04|24.04|26.04>[-arm64]` from `cuvis_base` and the wheels of the same release, in a virtual environment at `/opt/venv`.
  Ubuntu 26.04 exists for amd64 only and installs the 24.04 wheel.
  The image was previously built by cuvis.docker from a clone of `main`.
- `CHANGELOG.md`, `CONTRIBUTING.md` - this file and the version, changelog and release conventions.
- `cuvis_il` - reports the SDK version it was built against, the library version it loaded and the symbols that library lacks, so a mismatch between the installed SDK and the interface layer raises a descriptive error instead of failing at import.
- `cuvis_il.cuvis_il.cuvis_proc_cont_set_reference_white_spectrum_swig`, `cuvis_il.cuvis_il.cuvis_proc_cont_set_reference_target_spectrum_swig` - set a white spectrum of sensor counts, or a target reflectance spectrum, on a processing context from numpy arrays.
  The wavelength array and the value array must have the same non-zero length; the white setter also takes the counts' effective bit depth and integration time, and target values are reflectance fractions, 1.0 meaning 100 percent.
- `cuvis_il.cuvis_il.cuvis_proc_cont_get_reference_white_spectrum_swig`, `cuvis_il.cuvis_il.cuvis_proc_cont_get_reference_target_spectrum_swig` - read a reference spectrum back into numpy arrays that own their memory, copied out of the arrays the C getters only borrow.
  The white getter also returns the stored effective bit depth and integration time; an empty slot yields `status_not_available` with empty arrays.

### Changed

- `CONTRIBUTING.md` - the branch model is now trunk based: `develop` is gone, every change is cut from `main` and merged back into it by pull request, and a commit on `main` is no longer necessarily a release.
- One Linux wheel per Python version and architecture, built on the oldest Ubuntu that has a `cuvis_base` image, instead of one per Ubuntu release.
  A `manylinux` tag states a minimum glibc, so the 22.04 build already served 24.04 and 26.04; the second wheel only ever duplicated it.
- The platform tag now comes from `auditwheel`, which derives it from the symbols the extension references and fails the build when they outgrow the tag, instead of being stamped from the build container.
  `libcuvis.so` is excluded from the repair, so the wheel still contains nothing but the binding and resolves the SDK installed on the system.
- `cuvis.swig` - submodule advanced: the interface layer releases the GIL around SDK calls and string arguments are passed without copies.
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
