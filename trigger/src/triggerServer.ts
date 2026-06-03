/**
 * Thin Node trigger endpoint (M2). The browser Monitor cannot mint a Trigger.dev
 * public access token, and neither can the Python backend (REST returns only a
 * run id). So this tiny server — the ONLY place the Trigger.dev SECRET key lives
 * at runtime — triggers the orchestrator via the JS SDK (which returns a
 * run-scoped public token) and hands {feaRunId, orchRunId, publicAccessToken}
 * to the browser for useRealtimeRun. It never exposes the secret key.
 *
 *   POST /trigger-pipeline { failAtStage?: string }
 *     -> { feaRunId, orchRunId, publicAccessToken }
 */
import http from "node:http";
import { timingSafeEqual } from "node:crypto";

import { tasks } from "@trigger.dev/sdk";

import { feaPipelineOrchestrator } from "./feaPipeline.js";

const FEA_API_BASE = process.env.FEA_API_BASE ?? "http://localhost:8000/api/v1";
const PORT = Number(process.env.TRIGGER_SERVER_PORT ?? 3033);
// Local-only by default: this process holds TRIGGER_SECRET_KEY and can mint
// public tokens, so it binds to loopback and (optionally) requires a shared
// token. Set HOST=0.0.0.0 only behind your own auth/network policy. (Codex M2 R0/R1 P2.)
const HOST = process.env.TRIGGER_SERVER_HOST ?? "127.0.0.1";
// No CORS header by default: a cross-origin browser page then CANNOT read the
// minted publicAccessToken (its preflight/response is blocked). curl/Node (the
// fake orchestrator + the M3 React app via an explicit origin) are unaffected.
const CORS_ORIGIN = process.env.TRIGGER_SERVER_CORS_ORIGIN ?? "";
const SERVER_TOKEN = process.env.TRIGGER_SERVER_TOKEN ?? "";

const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);

/** Host-header hostname (strips :port + trailing FQDN dot; handles bracketed IPv6). */
function hostHeaderName(hostHeader: string): string {
  const h = hostHeader.trim().toLowerCase();
  const name = h.startsWith("[")
    ? h.slice(0, h.indexOf("]") + 1) // [::1]
    : h.slice(0, h.lastIndexOf(":") >= 0 ? h.lastIndexOf(":") : h.length);
  // Normalise a trailing-dot FQDN (localhost. / 127.0.0.1.) so it still matches
  // loopback (Codex M2 R2 P3 — was fail-closed, not a bypass).
  return name.endsWith(".") ? name.slice(0, -1) : name;
}

/** DNS-rebinding guard: reject requests whose Host is not loopback, so a page
 *  at attacker.com (rebound to 127.0.0.1) cannot reach this loopback service. */
function hostAllowed(req: http.IncomingMessage): boolean {
  return LOOPBACK_HOSTS.has(hostHeaderName(req.headers.host ?? ""));
}

/** Constant-time bearer check; allow-all only when no token is configured. */
function authorized(req: http.IncomingMessage): boolean {
  if (!SERVER_TOKEN) return true;
  const got = req.headers["x-trigger-server-token"];
  const supplied = Array.isArray(got) ? got[0] ?? "" : got ?? "";
  const a = Buffer.from(supplied);
  const b = Buffer.from(SERVER_TOKEN);
  return a.length === b.length && timingSafeEqual(a, b);
}

function readJson(req: http.IncomingMessage): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => (data += chunk));
    req.on("end", () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on("error", reject);
  });
}

const server = http.createServer(async (req, res) => {
  // CORS only when an origin is explicitly configured (default: none, so a
  // cross-origin page cannot read the minted token).
  if (CORS_ORIGIN) {
    res.setHeader("Access-Control-Allow-Origin", CORS_ORIGIN);
    res.setHeader("Access-Control-Allow-Headers", "content-type,x-trigger-server-token");
    res.setHeader("Access-Control-Allow-Methods", "POST,OPTIONS");
  }
  if (!hostAllowed(req)) {
    res.writeHead(403, { "Content-Type": "application/json" });
    return res.end(JSON.stringify({ error: "host not allowed (loopback only)" }));
  }
  if (req.method === "OPTIONS") {
    res.writeHead(204);
    return res.end();
  }
  if (req.method !== "POST" || !req.url?.startsWith("/trigger-pipeline")) {
    res.writeHead(404, { "Content-Type": "application/json" });
    return res.end(JSON.stringify({ error: "POST /trigger-pipeline only" }));
  }
  if (!authorized(req)) {
    res.writeHead(401, { "Content-Type": "application/json" });
    return res.end(JSON.stringify({ error: "invalid or missing X-Trigger-Server-Token" }));
  }

  try {
    const body = await readJson(req);
    const failAtStage = (body.failAtStage as string | undefined) ?? null;

    // 1. Create the FastAPI run (external mode -> PENDING, no self-advance).
    const created = (await fetch(`${FEA_API_BASE}/workflow/trigger`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ triggerMode: "external", failAtStage, label: "trigger-dev" }),
    }).then((r) => r.json())) as { runId: string };
    const feaRunId = created.runId;

    // 2. Trigger the Trigger.dev orchestrator; handle.publicAccessToken is
    //    auto-scoped (read) to this run — safe to hand to the browser.
    const handle = await tasks.trigger<typeof feaPipelineOrchestrator>(
      "fea-pipeline-orchestrator",
      { feaRunId, failAtStage },
    );

    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        feaRunId,
        orchRunId: handle.id,
        publicAccessToken: handle.publicAccessToken,
      }),
    );
  } catch (err) {
    res.writeHead(500, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: String(err) }));
  }
});

server.listen(PORT, HOST, () => {
  // eslint-disable-next-line no-console
  console.log(
    `trigger server: http://${HOST}:${PORT}/trigger-pipeline  (FEA API ${FEA_API_BASE})` +
      (SERVER_TOKEN ? "  [token-gated]" : "  [local-only, no token]"),
  );
});
