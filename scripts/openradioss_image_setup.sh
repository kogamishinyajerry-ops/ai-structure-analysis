#!/usr/bin/env bash
# One-time OpenRadioss Docker image setup.
#
# Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.
#
# This script attempts to ensure a usable OpenRadioss Docker image is
# available locally. It tries, in order:
#   1. Pull ${OPENRADIOSS_IMAGE} (default: ghcr.io/openradioss/openradioss-docker:latest)
#   2. If pull fails, fall back to building from a fresh OpenRadioss source
#      checkout under ${OPENRADIOSS_SRC} (default: ~/.cache/openradioss).
#      The OpenRadioss repo provides a Dockerfile at the root.
#
# Notes:
#   * The image build can take 30+ minutes under linux/amd64 emulation on
#     Apple Silicon; pulling a prebuilt image is strongly preferred.
#   * If neither pulling nor building succeeds, the script exits non-zero
#     and the user must install OpenRadioss by hand or supply a custom image
#     name via OPENRADIOSS_IMAGE.
#   * This script does NOT validate that the image actually runs; that is
#     verified by tests/test_openradioss_docker_smoke.py (skip-if-no-binary).
#
# Boundaries:
#   * Does not modify golden_samples/, agents/, schemas/, or any HF1 zone.
#   * Does not run the Tier 1 candidate deck; deck execution is gated by
#     scripts/fm04a_real_pipeline.py (P11+).
#   * Tier 1 only; nothing here promotes any artifact to Tier 2.
#
set -euo pipefail

IMAGE="${OPENRADIOSS_IMAGE:-ghcr.io/openradioss/openradioss-docker:latest}"
PLATFORM="${OPENRADIOSS_PLATFORM:-linux/amd64}"
SRC="${OPENRADIOSS_SRC:-${HOME}/.cache/openradioss}"

if ! command -v docker >/dev/null 2>&1; then
  echo "openradioss_image_setup.sh: docker is not on PATH" >&2
  exit 127
fi

echo "==> attempting to pull ${IMAGE} (platform=${PLATFORM})"
if docker pull --platform="${PLATFORM}" "${IMAGE}" 2>&1; then
  echo "==> pull succeeded; ${IMAGE} is ready"
  exit 0
fi

echo "==> pull failed; attempting source-build fallback under ${SRC}"
if [[ ! -d "${SRC}/.git" ]]; then
  git clone --depth=1 https://github.com/OpenRadioss/OpenRadioss "${SRC}"
fi

cd "${SRC}"
git fetch --depth=1 origin main || true
git reset --hard origin/main || true

if [[ ! -f Dockerfile ]]; then
  echo "==> OpenRadioss checkout has no Dockerfile; cannot fallback-build" >&2
  echo "    Provide a working image via OPENRADIOSS_IMAGE and re-run." >&2
  exit 1
fi

echo "==> building Docker image (this may take 30+ minutes under linux/amd64 emulation)"
docker buildx build \
  --platform="${PLATFORM}" \
  --tag "${IMAGE}" \
  --file Dockerfile \
  .

echo "==> source-build complete; ${IMAGE} is ready"
