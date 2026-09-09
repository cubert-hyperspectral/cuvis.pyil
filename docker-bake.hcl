# Packages the wheels in ./dist on top of cuvis_base, one architecture group per native runner:
#   CUVIS_VERSION=3.5.3 CUVIS_IL_VERSION=3.5.3.3 docker buildx bake amd64
variable "CUVIS_VERSION" {
  default = ""
  validation {
    condition     = CUVIS_VERSION != ""
    error_message = "Set CUVIS_VERSION to the cuvis SDK release of the base image, e.g. CUVIS_VERSION=3.5.3"
  }
}

variable "CUVIS_IL_VERSION" {
  default = ""
  validation {
    condition     = CUVIS_IL_VERSION != ""
    error_message = "Set CUVIS_IL_VERSION to the wheel version in ./dist, e.g. CUVIS_IL_VERSION=3.5.3.3"
  }
}

variable "variants" {
  default = [
    { ubuntu = "22.04", arch = "amd64" },
    { ubuntu = "24.04", arch = "amd64" },
    { ubuntu = "26.04", arch = "amd64" },
    { ubuntu = "22.04", arch = "arm64" },
    { ubuntu = "24.04", arch = "arm64" },
  ]
}

function "tag_suffix" {
  params = [v]
  result = v.arch == "amd64" ? "" : "-${v.arch}"
}

function "target_name" {
  params = [v]
  result = "cuvis_pyil-ubuntu${replace(v.ubuntu, ".", "-")}${tag_suffix(v)}"
}

group "default" { targets = ["amd64", "arm64"] }
group "amd64"   { targets = [for v in variants : target_name(v) if v.arch == "amd64"] }
group "arm64"   { targets = [for v in variants : target_name(v) if v.arch == "arm64"] }

target "cuvis_pyil" {
  name       = target_name(v)
  matrix     = { v = variants }
  context    = "."
  dockerfile = "docker/Dockerfile"
  platforms  = ["linux/${v.arch}"]

  args = {
    UBUNTU_VERSION   = v.ubuntu
    CUVIS_VERSION    = CUVIS_VERSION
    CUVIS_IL_VERSION = CUVIS_IL_VERSION
    TAG_SUFFIX       = tag_suffix(v)
  }

  tags = ["cubertgmbh/cuvis_pyil:${CUVIS_VERSION}-ubuntu${v.ubuntu}${tag_suffix(v)}"]
}
