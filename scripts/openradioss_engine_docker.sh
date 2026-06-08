#!/usr/bin/env bash
# OpenRadioss engine wrapper that shells out to a linux/amd64 Docker image.
#
# Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.
#
# Companion to scripts/openradioss_starter_docker.sh — see that script's
# header for full context. This wrapper invokes ``engine_linux64_gf`` inside
# the same Docker image after the starter has produced restart files.
#
# Configuration (environment variables):
#   OPENRADIOSS_IMAGE / OPENRADIOSS_PLATFORM / OPENRADIOSS_NPROC
#     match the starter wrapper.
#
# Usage:
#   openradioss_engine_docker.sh -i model_00_0001.rad
#
set -euo pipefail

IMAGE="${OPENRADIOSS_IMAGE:-ghcr.io/openradioss/openradioss-docker:latest}"
PLATFORM="${OPENRADIOSS_PLATFORM:-linux/amd64}"

if ! command -v docker >/dev/null 2>&1; then
  echo "openradioss_engine_docker.sh: docker is not on PATH" >&2
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
  engine_linux64_gf "$@"
