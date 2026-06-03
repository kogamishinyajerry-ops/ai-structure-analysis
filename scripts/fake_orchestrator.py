"""Drive the FULL M2 external-orchestration contract — WITHOUT Trigger.dev.

This does exactly what the Trigger.dev `feaPipelineOrchestrator` task does, in
plain Python over HTTP, so the M2 backend contract is provable end-to-end with
no account, no Node, no network egress:

    create an external (PENDING) run -> POST /workflow/stage/run per stage
    (with the X-Internal-Token header) -> read the terminal run.

Usage:
    python scripts/serve_workflow_demo.py            # terminal 1 (:8077)
    python scripts/fake_orchestrator.py              # terminal 2 (happy run)
    python scripts/fake_orchestrator.py --fail solver_run
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request

DEFAULT_API = "http://localhost:8077/api/v1"
DEFAULT_SECRET = "demo-internal-secret"  # matches serve_workflow_demo.py default


def _req(method: str, url: str, body: dict | None = None, headers: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=DEFAULT_API)
    ap.add_argument("--secret", default=DEFAULT_SECRET)
    ap.add_argument("--fail", default=None, help="stage id to inject a failure at")
    args = ap.parse_args()

    stages = [s["stage"] for s in _req("GET", f"{args.api}/workflow/stages")["stages"]]
    created = _req("POST", f"{args.api}/workflow/trigger", {"triggerMode": "external"})
    run_id = created["runId"]
    print(f"created external run {run_id} (status={created['status']})\n")

    for stage in stages:
        fail = stage == args.fail
        st = _req(
            "POST",
            f"{args.api}/workflow/stage/run",
            {"runId": run_id, "stage": stage, "fail": fail},
            headers={"X-Internal-Token": args.secret},
        )
        warn = f"  ⚠ {st['warnings'][0]}" if st["warnings"] else ""
        err = f"  ✗ {st['errors'][0]['faultClass']}" if st["errors"] else ""
        print(f"  {stage:24} {st['status']:8}{warn}{err}")
        if st["status"] == "failed":
            break

    final = _req("GET", f"{args.api}/workflow/runs/{run_id}")
    print(f"\nrun terminal status: {final['status']}  finishedAt={final['finishedAt']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as exc:
        print(f"backend not reachable — start `python scripts/serve_workflow_demo.py` first ({exc})")
        raise SystemExit(1) from exc
