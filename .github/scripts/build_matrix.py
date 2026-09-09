#!/usr/bin/env python3
"""Emit the Linux build matrices for the cuvis_base images that exist for one SDK version.

Every image variant's cuvis_base is looked up on Docker Hub; the wheel matrix and the image
matrix are written as GITHUB_OUTPUT lines with only the variants that resolved.
A missing base image is reported as a warning annotation; --strict turns it into a failure.
"""

import argparse
import json
import os
import subprocess
import sys

# Wheels are built on 22.04 and 24.04 only; the 26.04 image installs the 24.04 wheel, whose
# manylinux_2_39 tag is satisfied by any newer glibc.
WHEEL_VARIANTS = (("22.04", "amd64"), ("24.04", "amd64"), ("22.04", "arm64"), ("24.04", "arm64"))
IMAGE_VARIANTS = WHEEL_VARIANTS + (("26.04", "amd64"),)
ARCHES = ("amd64", "arm64")
PYTHONS = {"3.9": "2.0.0", "3.10": "2.0.0", "3.11": "2.0.0", "3.12": "2.0.0", "3.13": "2.1.0", "3.14": "2.3.2"}
GLIBC = {"22.04": "2_35", "24.04": "2_39"}
MACHINE = {"amd64": "x86_64", "arm64": "aarch64"}
RUNNER = {("22.04", "amd64"): "ubuntu-latest", ("24.04", "amd64"): "ubuntu-latest",
          ("22.04", "arm64"): "ubuntu-22.04-arm", ("24.04", "arm64"): "ubuntu-24.04-arm"}
IMAGE_RUNNER = {"amd64": "ubuntu-latest", "arm64": "ubuntu-24.04-arm"}
ABSENT = ("no such manifest", "manifest unknown", "not found")


def tag_suffix(arch):
    return "" if arch == "amd64" else f"-{arch}"


def base_image(sdk, ubuntu, arch):
    return f"cubertgmbh/cuvis_base:{sdk}-ubuntu{ubuntu}{tag_suffix(arch)}"


def exists(image):
    # Only a registry answer of "not there" counts as missing; a transport error would
    # otherwise drop a variant that exists, silently on a pre-release and as a failed
    # release on a final one.
    probe = subprocess.run(["docker", "manifest", "inspect", image], capture_output=True, text=True)
    if probe.returncode == 0:
        return True
    if any(answer in probe.stderr.lower() for answer in ABSENT):
        return False
    sys.exit(f"cannot tell whether {image} exists: {probe.stderr.strip()}")


def wheel_jobs(variants):
    return [
        {
            "ubuntu": ubuntu, "arch": arch, "python": python, "numpy": numpy,
            "runner": RUNNER[ubuntu, arch], "tag_suffix": tag_suffix(arch),
            "platform_tag": f"manylinux_{GLIBC[ubuntu]}_{MACHINE[arch]}",
        }
        for ubuntu, arch in variants
        for python, numpy in PYTHONS.items()
    ]


def image_jobs(variants):
    return [
        {"arch": arch, "runner": IMAGE_RUNNER[arch],
         "targets": ",".join(f"cuvis_pyil-ubuntu{u.replace('.', '-')}{tag_suffix(arch)}" for u, a in variants if a == arch)}
        for arch in ARCHES
        if any(a == arch for _, a in variants)
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", required=True, help="cuvis SDK version of the base images")
    parser.add_argument("--strict", action="store_true", help="fail instead of warn when a base image is missing")
    args = parser.parse_args()

    available = [v for v in IMAGE_VARIANTS if exists(base_image(args.sdk, *v))]
    missing = [v for v in IMAGE_VARIANTS if v not in available]

    for ubuntu, arch in missing:
        products = "no wheels and no cuvis_pyil image" if (ubuntu, arch) in WHEEL_VARIANTS else "no cuvis_pyil image"
        print(f"::warning title=cuvis_base image missing::{base_image(args.sdk, ubuntu, arch)} does not exist; "
              f"{products} for ubuntu{ubuntu} {arch}", file=sys.stderr)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as out:
            out.write("### cuvis_pyil variants\n\n")
            out.writelines(f"- built: ubuntu{u} {a}\n" for u, a in available)
            out.writelines(f"- skipped, no `{base_image(args.sdk, u, a)}`: ubuntu{u} {a}\n" for u, a in missing)
    if missing and args.strict:
        sys.exit(f"a final release needs every cuvis_base variant; release cuvis.docker v{args.sdk} with all of them first")
    if not any(v in WHEEL_VARIANTS for v in available):
        sys.exit(f"no cuvis_base image to build wheels in exists for SDK {args.sdk}; release cuvis.docker v{args.sdk} first")

    print(f"wheel_matrix={json.dumps({'include': wheel_jobs([v for v in available if v in WHEEL_VARIANTS])})}")
    print(f"image_matrix={json.dumps({'include': image_jobs(available)})}")
    print(f"image_tags={' '.join(f'cubertgmbh/cuvis_pyil:{args.sdk}-ubuntu{u}{tag_suffix(a)}' for u, a in available)}")


if __name__ == "__main__":
    main()
