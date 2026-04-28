# OpenRadioss runtime container — linux/arm64 native (Apple Silicon).
# RFC-001 W7a env probe. The OpenRadioss release ships ELF aarch64
# binaries (starter_linuxa64 + engine_linuxa64), so on Apple Silicon
# we run them in a NATIVE arm64 Linux container — no Rosetta x86
# emulation, full speed.
#
# debian:12-slim chosen over ubuntu:22.04 because the deb.debian.org
# CDN was reachable when ports.ubuntu.com hit a 502 Bad Gateway, and
# the runtime surface we need is small (bash + perl + libgomp).
#
# Build: docker build -t openradioss:arm64 .
# Probe: docker run --rm openradioss:arm64 starter_linuxa64 -help
FROM debian:12-slim

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        bash perl procps libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY OpenRadioss /opt/OpenRadioss

ENV OPENRADIOSS_PATH=/opt/OpenRadioss
ENV PATH=/opt/OpenRadioss/exec:$PATH
ENV LD_LIBRARY_PATH=/opt/OpenRadioss/extlib/hm_reader/linuxa64:/opt/OpenRadioss/extlib/h3d/lib/linuxa64:/opt/OpenRadioss/extlib/ArmFlang_runtime/linuxa64:${LD_LIBRARY_PATH:-}
ENV RAD_H3D_PATH=/opt/OpenRadioss/extlib/h3d/lib/linuxa64
ENV RAD_CFG_PATH=/opt/OpenRadioss/hm_cfg_files

WORKDIR /work
CMD ["/bin/bash"]
