# Contributing to cuvis.pyil

This document covers the branch model, the version scheme, the changelog conventions and the release process.
For bug reports and questions use [GitHub Issues](https://github.com/cubert-hyperspectral/cuvis.pyil/issues).

## Branch model

| Branch | Role |
| --- | --- |
| `main` | The latest released interface layer for the latest released cuvis SDK. Every commit on `main` is a release and carries a `v*` tag. Never receives direct pushes. |
| `develop` | Integration branch for the next release. All feature work lands here. |
| `feature/*` | One branch per change, cut from `develop`, merged back into `develop` by pull request. |
| `hotfix/*` | Cut from `main` when a released version needs a fix before `develop` is ready to release. Merged into `main` by pull request, tagged, then merged back into `develop`. |

A pull request into `develop` or `main` must pass the `ci.yml` build and changelog jobs.

## Version scheme

Versions are `GENERATION.MAJOR.MINOR.PATCH`, always with all four components, optionally followed by a pre-release suffix `a1`, `b1` or `rc1`.

- `GENERATION.MAJOR.MINOR` is the cuvis SDK release the interface layer is compiled against.
  It is not chosen here; it follows the SDK.
- `PATCH` counts revisions against that same SDK release, starting at `0`.
- A pre-release (`3.6.0.0rc1`) runs the whole release pipeline and reaches PyPI as a pre-release, which `pip` ignores unless asked for with `--pre` or an exact pin.
  It creates no GitHub Release; its changelog entries stay under `## [Unreleased]` until the final version.

The version lives in exactly one place: `[project].version` in `pyproject.toml`.
The git tag is `v` followed by that value, and the release workflow refuses to publish when the two disagree.

## Changelog conventions

Every user-visible change is recorded in `CHANGELOG.md` under `## [Unreleased]` in the same pull request that makes the change.
The file follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and is validated in CI by the shared `changelog` action from [cuvis.docker](https://github.com/cubert-hyperspectral/cuvis.docker).

Rules the validator enforces:

- Release headers are `## [<version>] - <YYYY-MM-DD>`, plus one `## [Unreleased]` at the top.
- Versions descend down the file, and no version appears twice.
- Section headings are `### ` followed by exactly one of `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`, in that order, and each appears at most once per release.
- Every line inside a section is a `- ` bullet or an indented continuation line.

Each bullet names what changed first, in backticks (`cuvis_il.cuvis_il.<function>`, `cuvis.swig`, `CI`, `pyproject.toml`), then states the change in one sentence.
A second sentence goes on its own indented continuation line.
Do not write commit subjects, pull request numbers or author names into the changelog.

## Releasing

Releases run in a fixed order across repositories; see the [cuvis.docker README](https://github.com/cubert-hyperspectral/cuvis.docker#release-order).
The `cuvis_base:<sdk>-ubuntu*` images must exist before cuvis.pyil can release for that SDK.
A pre-release skips the variants whose base image is missing (typically Jetson) and finishes green with a warning annotation; a final release needs all of them and fails otherwise.

### One-time repository setup

- **Trusted publishers.** PyPI and TestPyPI bind a trusted publisher to a workflow file name.
  The publisher for `cuvis-il` must name `release.yml`; it previously named `publish_version.yml`.
- **Environments.** `testpypi`, `pypi` and `dockerhub` must exist under Settings -> Environments.
  `pypi` carries the required reviewers that make the PyPI publish a human gate.
  `dockerhub` holds the secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`, the same as in cuvis.docker.
- **Branch protection.** `main` and `develop` require the `ci.yml` checks, and `main` forbids direct pushes.

### Regular release from `develop`

1. On `develop`, confirm which SDK version the interface layer targets.
2. For a final version rename `## [Unreleased]` to `## [X.Y.Z.W] - <today>`, add the SDK statement line beneath it and a fresh empty `## [Unreleased]` above it.
   For a pre-release leave the entries under `## [Unreleased]`.
3. Set `[project].version` in `pyproject.toml` to `X.Y.Z.W` (or `X.Y.Z.WrcN`).
4. Open a pull request `develop` -> `main` titled `release: vX.Y.Z.W` and merge it once CI is green.
5. Tag the merge commit on `main` and push the tag:

   ```bash
   git checkout main && git pull
   git tag -a vX.Y.Z.W -m "cuvis-il X.Y.Z.W"
   git push origin vX.Y.Z.W
   ```

6. `release.yml` validates the tag, builds the wheels, publishes to TestPyPI, waits for approval on the `pypi` environment, publishes to PyPI, pushes the `cuvis_pyil` images, and for a final version creates the GitHub Release.
7. Merge `main` back into `develop`.

### If a release goes wrong

A published PyPI version cannot be replaced.
Fix forward with the next `PATCH`; yank on PyPI only when the artifact is actively harmful.
Image tags carry the SDK version only and are overwritten by the next release for that SDK.
Delete the tag and re-tag only while the release workflow has not yet published anything.
