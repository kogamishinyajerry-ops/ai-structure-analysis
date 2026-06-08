/**
 * Trigger.dev v4 orchestration of the AI-FEA Mock pipeline (M2).
 *
 * The orchestrator drives the 13 stages in order; each stage is a durable,
 * retryable task that hands work to the Python FastAPI backend via the
 * wait-token HTTP-callback pattern: createToken -> POST /workflow/stage/run with
 * the token URL -> the run SUSPENDS -> FastAPI POSTs the StageState back to the
 * token URL -> forToken resolves. Idempotency keys make an orchestrator retry
 * skip already-completed stages. At M4 the FastAPI stage runner swaps the Mock
 * backend for real CalculiX with no change here.
 */
import { idempotencyKeys, metadata, task, wait } from "@trigger.dev/sdk";

const FEA_API_BASE = process.env.FEA_API_BASE ?? "http://localhost:8000/api/v1";
const INTERNAL_SECRET = process.env.TRIGGER_INTERNAL_SECRET ?? "";

/** The 13 canonical stages — mirrors schemas/workflow_state.WorkflowStage. */
export const FEA_STAGES = [
  "project_intake",
  "cad_import",
  "geometry_validation",
  "material_assignment",
  "boundary_conditions",
  "load_cases",
  "mesh_generation",
  "mesh_quality_check",
  "solver_run",
  "convergence_monitoring",
  "post_processing",
  "result_analysis",
  "report_generation",
] as const;

type StageError = { faultClass: string; message: string };
type StageState = {
  runId: string;
  stage: string;
  status: "pending" | "running" | "success" | "warning" | "failed";
  progress: number;
  warnings: string[];
  errors: StageError[];
  [k: string]: unknown;
};

/** One pipeline stage: suspend on a wait token while FastAPI executes it. */
export const feaStageTask = task({
  id: "fea-stage",
  retry: { maxAttempts: 3, factor: 2, minTimeoutInMs: 1_000 },
  run: async (payload: {
    feaRunId: string;
    stage: string;
    stageIndex: number;
    fail: boolean;
  }): Promise<StageState> => {
    // Report progress up to the orchestrator run so the frontend (useRealtimeRun
    // on the orchestrator) sees the live stage.
    metadata.parent.set("currentStage", payload.stage);
    metadata.parent.set("currentStageIndex", payload.stageIndex);

    // 1. Mint a wait token — token.url is a credential-free callback URL.
    const token = await wait.createToken({ timeout: "30m" });

    // 2. Hand the stage to FastAPI; it will POST the StageState to token.url.
    const resp = await fetch(`${FEA_API_BASE}/workflow/stage/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Token": INTERNAL_SECRET,
      },
      body: JSON.stringify({
        runId: payload.feaRunId,
        stage: payload.stage,
        fail: payload.fail,
        callbackUrl: token.url,
      }),
    });
    if (!resp.ok) {
      throw new Error(`stage/run ${payload.stage} -> HTTP ${resp.status}`);
    }

    // 3. SUSPEND here (zero compute on Cloud) until FastAPI POSTs {data: StageState}.
    const completed = await wait.forToken<{ data: StageState }>(token).unwrap();
    const state = completed.data;

    metadata.parent.set("completedStages", payload.stageIndex + 1);
    metadata.parent.append("stageHistory", { stage: state.stage, status: state.status });

    // A failed stage throws -> the orchestrator's .unwrap() propagates it.
    if (state.status === "failed") {
      throw new Error(
        `stage ${state.stage} failed: ${state.errors?.[0]?.faultClass ?? "unknown"}`,
      );
    }
    return state;
  },
});

/** Drive the 13 stages in order. Idempotency keys dedup on orchestrator retry. */
export const feaPipelineOrchestrator = task({
  id: "fea-pipeline-orchestrator",
  retry: { maxAttempts: 2 },
  run: async (payload: { feaRunId: string; failAtStage?: string | null }) => {
    metadata.set("feaRunId", payload.feaRunId);
    metadata.set("totalStages", FEA_STAGES.length);

    // entries() keeps `stage` typed as string (not string|undefined under
    // noUncheckedIndexedAccess).
    for (const [i, stage] of FEA_STAGES.entries()) {
      // Stable across orchestrator retries: a completed stage is not re-run.
      const iKey = await idempotencyKeys.create(`${payload.feaRunId}-stage-${i}`);
      await feaStageTask
        .triggerAndWait(
          {
            feaRunId: payload.feaRunId,
            stage,
            stageIndex: i,
            fail: payload.failAtStage === stage,
          },
          { idempotencyKey: iKey, idempotencyKeyTTL: "24h" },
        )
        .unwrap();
    }
    return { feaRunId: payload.feaRunId, stages: FEA_STAGES.length };
  },
});
