# Releasing cuvis.pyil

Maintainer documentation.
Nothing here concerns someone who only installs `cuvis-il`; that is what `README.md` is for.

## Release order across repositories

The three wrapper repositories release in a fixed order, because each one builds inside the image the previous one published.

```
1. cuvis.docker   tag vX.Y.Z[rcN]     -> cubertgmbh/cuvis_base:X.Y.Z-ubuntu{22.04,24.04,26.04}[-arm64]
2. cuvis.pyil     tag vX.Y.Z.W[rcN]   -> cuvis-il X.Y.Z.W[rcN] on PyPI
                                      -> cubertgmbh/cuvis_pyil:X.Y.Z-ubuntu{22.04,24.04,26.04}[-arm64]
3. cuvis.python   tag vX.Y.Z.W[rcN]   -> cuvis X.Y.Z.W[rcN] on PyPI
```

Each repository gates on the previous one rather than on anyone remembering the order.
`validate` in this repository probes Docker Hub for `cuvis_base:<sdk>-*` and fails fast when nothing is there.

Image tags carry the SDK version only, never the wrapper revision and never a pre-release suffix.
Docker tags are mutable, the newest build for an SDK is the one people want, and cuvis.python's test container `cuvis_pyil:<sdk>-ubuntu24.04` is therefore pre-release agnostic.

## What a variant being missing means

The SDK download does not always contain every platform.
SDK 3.6.0, for instance, ships no arm64 packages at all, so no `cuvis_base:3.6.0-*-arm64` exists and none can be built.

`.github/scripts/build_matrix.py` probes which `cuvis_base` images exist and emits three matrices from that one answer: `test_matrix` for CI, `wheel_matrix` and `image_matrix` for the release.
A variant without a base image is a warning annotation and is skipped.
On a final release the script runs with `--strict` and a missing variant fails instead, because a final release must not silently ship fewer platforms than the last one.

A registry lookup that fails to reach Docker Hub is not treated as "missing" - it aborts, so a network blip cannot quietly shrink a release.

## Version scheme and pre-releases

Versions are `GENERATION.MAJOR.MINOR.PATCH`, always four components, optionally followed by `a1`, `b1` or `rc1`.
`GENERATION.MAJOR.MINOR` follows the cuvis SDK release the interface layer is compiled against; `PATCH` counts revisions against that same SDK, starting at `0`.

A pre-release tag runs the entire pipeline:

- It publishes to PyPI as a PEP 440 pre-release, which `pip` ignores unless asked with `--pre` or an exact pin.
- It pushes the same image tags a final release would, overwriting them.
- It creates **no** GitHub Release, and its changelog entries stay under `## [Unreleased]`.
- It tolerates missing platform variants with a warning.

A pre-release is therefore not a dry run: it publishes to PyPI and overwrites live image tags.

## One-time repository setup

### Trusted publishers

PyPI and TestPyPI bind a trusted publisher to a workflow *file name*.
Both publishers for `cuvis-il` must name `release.yml`; they previously named `publish_version.yml`.
`publish-testpypi` gates `publish-pypi`, so a stale TestPyPI publisher blocks the whole release, not just the TestPyPI step.

### Environments

| Environment | Used by | Secrets | Protection |
| --- | --- | --- | --- |
| `testpypi` | `publish-testpypi` | none, authenticates by OIDC | deployment tag rule `v*` |
| `pypi` | `publish-pypi` | none, authenticates by OIDC | deployment tag rule `v*`, plus required reviewers |
| `dockerhub` | `docker-image` | `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` | deployment tag rule `v*` |

`release-gate` is left over from the old workflow, is referenced by nothing, and should be deleted.

The deployment rule is what ties an environment to the release decision.
Under Settings -> Environments -> *environment* -> Deployment branches and tags, choose "Selected branches and tags" and add one rule of type **Tag** with the pattern `v*`.
Only a run triggered by a version tag can then reach the environment and its secrets, and since pushing a `v*` tag is already restricted by a ruleset, the environment inherits that control.

Two ways to get this wrong:

- Leaving the environment unrestricted lets a workflow run from any branch in the repository reach the Docker Hub token.
- Choosing "protected branches only" rejects the release outright, because a tag ref is never a protected branch.

`pypi` additionally carries required reviewers, which makes the PyPI publish the one human gate in the pipeline.
TestPyPI and the image push need no reviewer; both are replaceable.

`dockerhub` holds an Organization Access Token scoped to read and write, the same token as in cuvis.docker.
Docker Hub OIDC would remove the token entirely, but it requires a Team or Business plan, which `cubertgmbh` does not have.

### Protection rules

- `main` and `develop` require the `ci.yml` checks; `main` forbids direct pushes.
- A ruleset restricts who may push `v*` tags, which is what gives the deployment tag rule its meaning.

## Releasing from `develop`

1. Confirm which SDK version the interface layer targets, and that `cuvis_base:<sdk>-*` has been released from cuvis.docker.
2. For a final version, rename `## [Unreleased]` to `## [X.Y.Z.W] - <today>` and add a fresh empty `## [Unreleased]` above it.
   For a pre-release, leave the entries under `## [Unreleased]`.
3. Set `[project].version` in `pyproject.toml` to `X.Y.Z.W` or `X.Y.Z.WrcN`.
   The version lives in exactly one place; the release refuses to publish when the tag and `pyproject.toml` disagree.
4. Open a pull request `develop` -> `main` titled `release: vX.Y.Z.W` and merge it once CI is green.
5. Tag the merge commit on `main` and push the tag:

   ```bash
   git checkout main && git pull
   git tag -a vX.Y.Z.W -m "cuvis-il X.Y.Z.W"
   git push origin vX.Y.Z.W
   ```

6. `release.yml` validates the tag, builds the wheels, publishes to TestPyPI, waits for approval on the `pypi` environment, publishes to PyPI, pushes the `cuvis_pyil` images, and for a final version creates the GitHub Release from the changelog section.
7. Merge `main` back into `develop`.

## If a release goes wrong

A published PyPI version cannot be replaced.
Fix forward with the next `PATCH`; yank on PyPI only when the artifact is actively harmful.

Image tags carry the SDK version only and are overwritten by the next release for that SDK, so a bad image is corrected by releasing again.

Delete a tag and re-tag only while the release workflow has not yet published anything.
