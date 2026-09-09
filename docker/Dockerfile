ARG CUVIS_VERSION
ARG UBUNTU_VERSION=24.04
ARG TAG_SUFFIX=""

FROM cubertgmbh/cuvis_base:${CUVIS_VERSION}-ubuntu${UBUNTU_VERSION}${TAG_SUFFIX}
LABEL maintainer="birkholz@cubert-gmbh.de"

ARG CUVIS_IL_VERSION
ENV DEBIAN_FRONTEND=noninteractive

# python3-dev for libpython3.X.so: the wheel's extension module is linked against it.
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-venv python3-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# The build context holds the wheels of this release; pip picks the one matching the
# system interpreter and glibc (26.04 takes the 24.04 build) and pulls numpy from PyPI.
COPY dist/ /tmp/dist/
RUN pip install --no-cache-dir --find-links /tmp/dist "cuvis_il==${CUVIS_IL_VERSION}" && \
    rm -rf /tmp/dist

RUN python -c "from cuvis_il import cuvis_il; print(cuvis_il.cuvis_version_swig())" | grep -q "CUBERT SDK"
