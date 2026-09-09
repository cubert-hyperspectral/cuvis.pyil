# Contributing to cuvis.pyil

This document covers the branch model, the version scheme and the changelog conventions.
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
