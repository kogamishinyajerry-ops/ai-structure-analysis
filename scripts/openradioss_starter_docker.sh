#!/usr/bin/env bash
# OpenRadioss starter wrapper that shells out to a linux/amd64 Docker image.
#
# Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.
#
# Why this wrapper exists:
#   * macOS Apple Silicon does not have native OpenRadioss prebuilt binaries.
#   * The FM-04a P4 OpenRadioss AERON adapter probes PATH for
#     ``starter_linux64_gf`` / ``openradioss_starter`` / ``starter`` /
#     ``radioss_starter``. If THIS script (or a symlink to it named
#     ``starter_linux64_gf``) is on PATH, the adapter discovers it and the
#     adapter's existing subprocess-shell-out path does the rest.
#   * This wrapper translates the adapter call into a ``docker run
#     --platform=linux/amd64`` invocation against a pre-built OpenRadioss
#     image and mounts the case directory at /work.
#
# Configuration (environment variables):
#   OPENRADIOSS_IMAGE   — Docker image to run. Defaults to
#                         "ghcr.io/openradioss/openradioss-docker:latest".
#                         Override with your own image as needed.
#   OPENRADIOSS_PLATFORM — Docker --platform flag. Defaults to "linux/amd64".
#   OPENRADIOSS_NPROC   — Optional thread count (sets OMP_NUM_THREADS inside
#                         the container).
#
# Usage (matches the OpenRadioss native CLI):
#   openradioss_starter_docker.sh -i model_00_0000.rad
#
# Boundaries:
#   * This script does NOT install OpenRadioss; the image must be available
#     locally or pullable. Run scripts/openradioss_image_setup.sh once to
#     pull / build the image.
#   * This script does NOT promote any output to Tier 2. Output discovery
#     and metric extraction happen in the FM-04a P4 adapter + P6 extractor.
#
set -euo pipefail

IMAGE="${OPENRADIOSS_IMAGE:-ghcr.io/openradioss/openradioss-docker:latest}"
PLATFORM="${OPENRADIOSS_PLATFORM:-linux/amd64}"

if ! command -v docker >/dev/null 2>&1; then
  echo "openradioss_starter_docker.sh: docker is not on PATH" >&2
  exit 127
fi

case_dir="$(pwd)"

env_args=()
if [[ -n "${OPENRADIOSS_NPROC:-}" ]]; then
  env_args+=("-e" "OMP_NUM_THREADS=${OPENRADIOSS_NPROC}")
fi

exec docker run --rm \
  --platform="${PLATFORM}" \
  -v "${case_dir}:/work" \
  -w /work \
  "${env_args[@]}" \
  "${IMAGE}" \
  starter_linux64_gf "$@"
