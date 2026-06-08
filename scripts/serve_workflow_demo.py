"""Standalone demo server for the Agentic FEA Workflow Runtime (M1).

Mounts ONLY the workflow router, so the 13-stage Mock pipeline + the Monitor UI
run without the rest of the FastAPI app (and without the optional OpenAI/NLParser
import path). Use this to watch the flow run end-to-end:

    python scripts/serve_workflow_demo.py            # serves on http://localhost:8077
    open docs/demo/workflow_monitor.html             # point it at the same base

The real app exposes the identical surface under /api/v1/workflow/* once the
router is registered in app.main (already wired). This launcher just gives a
dependency-light way to demo it.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))  # schemas/, aeron/
sys.path.insert(0, str(_REPO / "backend"))  # app/

# Mirror the CI condition (OPENAI_API_KEY unset -> NLParser client is None) so the
# app.api package import is clean regardless of the local env. See the workflow
# test for the same note.
from app.core.config import settings  # noqa: E402

settings.openai_api_key = None
# Demo-only internal secret so POST /workflow/stage/run (the M2 external path)
# is usable without extra config. Real deployments set TRIGGER_INTERNAL_SECRET.
if not settings.trigger_internal_secret:
    settings.trigger_internal_secret = "demo-internal-secret"
# Allow loopback wait-token callbacks for local fake-orchestrator testing (the
# SSRF guard rejects loopback by default; production callbacks are on the
# Trigger.dev host). Demo/self-host only.
settings.trigger_allow_loopback_callback = True

import uvicorn  # noqa: E402
from app.api.routes import workflow  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app = FastAPI(title="AI-FEA Workflow Runtime — demo", docs_url="/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(workflow.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "workflow-runtime-demo"}


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8077
    print(f"Workflow demo server: http://localhost:{port}/api/v1/workflow/stages")
    uvicorn.run(app, host="127.0.0.1", port=port)
