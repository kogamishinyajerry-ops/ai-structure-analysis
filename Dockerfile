# syntax=docker/dockerfile:1.7
#
# P1-01 base image for AI-FEA Engine (ADR-008 N-3).
#
# Fixes the solver / CAD / mesher stack so that hot-smoke, GS-001 and
# downstream P1 tasks run on a reproducible toolchain:
#
#   * CalculiX 2.21 (via Debian ``calculix-ccx`` package, ADR-002)
#   * FreeCAD 0.22 line (Debian ``freecad-python3`` package, ADR-001 GMSA-1/2)
#   * gmsh Python bindings (pip ``gmsh`` wheel; ADR-001 GMSA-3)
#   * Python 3.11 + project editable install with ``agents`` + ``solvers`` + ``viz`` extras
#
# The image is published to GHCR by ``.github/workflows/docker-base.yml``
# as ``ghcr.io/kogamishinyajerry-ops/ai-fea-engine:p1-base`` and consumed
# by the hot-smoke CI lane added in later P1 phases.

FROM python:3.11-slim-bookworm AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AI_FEA_IN_CONTAINER=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        ca-certificates \
        calculix-ccx \
        freecad-python3 \
        libgl1 \
        libglu1-mesa \
        libxrender1 \
        libxext6 \
        libsm6 \
        libxcursor1 \
        libxi6 \
        libxft2 \
        libxinerama1 \
        libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

# FreeCAD ships Python modules to /usr/lib/freecad-python3/lib; expose
# them to our Python 3.11 interpreter.
ENV PYTHONPATH=/usr/lib/freecad-python3/lib:/usr/share/freecad/lib:${PYTHONPATH}

WORKDIR /workspace

# Install the project first (dependency-only layer) for cache friendliness.
COPY pyproject.toml ./pyproject.toml
COPY README.md ./README.md
ENV PIP_DEFAULT_TIMEOUT=180 \
    PIP_RETRIES=5

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -e ".[dev,agents,solvers,viz]" \
    && python -m pip install --no-cache-dir gmsh

# Finally copy the rest of the repo.
COPY . .

# Smoke-check the toolchain at build time so broken base images never ship.
RUN ccx -v 2>&1 | head -n 5 \
    && python -c "import gmsh; gmsh.initialize(); gmsh.finalize(); print('gmsh OK')" \
    && python -c "import FreeCAD; print('FreeCAD', FreeCAD.Version())"

CMD ["bash"]
