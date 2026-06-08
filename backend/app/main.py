"""FastAPI主应用"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import nl_router

# RFC-001 §6.1 Bucket B: routes.knowledge moved to _frozen/sprint2/route_knowledge.py.
# The /api/v1/knowledge/* surface is unregistered until post-MVP redesign.
from .api.routes import (
    acceptance_packet,
    advisor_critique,
    archived_packet_diff,
    candidate_cases,
    case_comparison,
    case_completeness,
    cases,
    cohort_anomalies,
    cohort_executive_summary,
    cohort_overview,
    cohort_snapshot_diff,
    cohort_snapshots,
    cohort_trend_anomalies,
    convergence_study,
    frd,
    materials,
    projects,
    report,
    reproducibility_manifest,
    reviewer_bundle,
    sensitivity,
    signoff_history,
    snapshot_narrative,
    solver,
    tier1_report,
    trust_score,
    trust_score_alerts,
    trust_score_provenance,
    trust_score_timeline,
    visualization,
    workflow,
)
from .core.config import settings
from .db.session import init_db
from .services.case_service import get_case_service

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="有限元分析后处理智能助手API",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库并导入样本"""
    await init_db()

    # 自动导入黄金样本
    from .db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        case_svc = get_case_service()
        await case_svc.auto_import_golden_samples(db)


# CORS配置
# allow_credentials=False: the frontend uses bare fetch (no cookies/credentials),
# and the wildcard-origin + allow_credentials=True combination is rejected by
# browsers anyway (Fetch spec) — fixed per M2 threat model (P3).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制来源
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
# RFC-001 §6.1 Bucket C: result_router removed (replaced by /projects/{id}/results in W4+)
app.include_router(nl_router, prefix="/api/v1")
# knowledge.router unregistered — see import note above (RFC-001 §6.1 Bucket B)
app.include_router(visualization.router, prefix="/api/v1")
app.include_router(frd.router, prefix="/api/v1")
app.include_router(report.router, prefix="/api/v1")
app.include_router(cases.router, prefix="/api/v1")
app.include_router(solver.router, prefix="/api/v1")
app.include_router(sensitivity.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
# FM-04a Phase 2 C — Tier 1 candidate-case picker (golden_samples/*-candidate/)
app.include_router(candidate_cases.router, prefix="/api/v1")
# FM-04a Phase 2 E — Tier 1 candidate report packet downloader.
app.include_router(tier1_report.router, prefix="/api/v1")
# FM-04a Phase 3 A — Tier 1 candidate acceptance evidence packet.
app.include_router(acceptance_packet.router, prefix="/api/v1")
# FM-04a Phase 3 B — Tier 1 candidate case-vs-case comparison.
app.include_router(case_comparison.router, prefix="/api/v1")
# FM-04a Phase 3 D — Tier 1 candidate convergence study sidecar.
app.include_router(convergence_study.router, prefix="/api/v1")
# FM-04a Phase 4 A — Tier 1 candidate evidence completeness score.
app.include_router(case_completeness.router, prefix="/api/v1")
# FM-04a Phase 4 B — Tier 1 candidate cohort overview.
app.include_router(cohort_overview.router, prefix="/api/v1")
# FM-04a Phase 4 C — Tier 1 reviewer bundle (multi-case zip).
app.include_router(reviewer_bundle.router, prefix="/api/v1")
# FM-04a Phase 4 D — Tier 1 archived acceptance packet diff.
app.include_router(archived_packet_diff.router, prefix="/api/v1")
# FM-04a Phase 5 B — Tier 1 reproducibility manifest per case.
app.include_router(reproducibility_manifest.router, prefix="/api/v1")
# FM-04a Phase 5 C — Tier 1 cohort snapshot listing.
app.include_router(cohort_snapshots.router, prefix="/api/v1")
# FM-04a Phase 5 D — Tier 1 cohort snapshot diff.
app.include_router(cohort_snapshot_diff.router, prefix="/api/v1")
# FM-04a Phase 6 B — Tier 1 evidence trust score.
app.include_router(trust_score.router, prefix="/api/v1")
# FM-04a Phase 6 C — Tier 1 snapshot drift narrative.
app.include_router(snapshot_narrative.router, prefix="/api/v1")
# FM-04a Phase 6 D — Tier 1 trust score timeline.
app.include_router(trust_score_timeline.router, prefix="/api/v1")
# FM-04a Phase 7 C — Tier 1 trust score regression alarms.
app.include_router(trust_score_alerts.router, prefix="/api/v1")
# FM-04a Phase 8 B — Tier 1 reviewer signoff history.
app.include_router(signoff_history.router, prefix="/api/v1")
# FM-04a Phase 8 C — Tier 1 trust score provenance trace.
app.include_router(trust_score_provenance.router, prefix="/api/v1")
# FM-04a Phase 8 D — Tier 1 cohort executive summary scorecard.
app.include_router(cohort_executive_summary.router, prefix="/api/v1")
# FM-04a Phase 8 E — Tier 1 cohort anomaly detection.
app.include_router(cohort_anomalies.router, prefix="/api/v1")
# FM-04a Phase 9 D — Tier 1 cohort trend-slope anomaly detection.
app.include_router(cohort_trend_anomalies.router, prefix="/api/v1")
# FM-04a Phase 11 D — Tier 1 candidate AI advisor critique surface.
app.include_router(advisor_critique.router, prefix="/api/v1")
# FM-04a Phase 18 C/E — Materials library (steel-S355, aluminium-6061-T6,
# titanium-Ti-6Al-4V). Read-only GET surface exposed for the
# MaterialPickerPanel front-end + downstream Tier 2 INP composition.
app.include_router(materials.router, prefix="/api/v1")
# Agentic FEA Workflow Runtime (plan .planning/AGENTIC-FEA-RUNTIME-PLAN.md) M1 —
# Mock pipeline: 13-stage observable flow with synthetic solver data + StageState
# events, driving the Workflow Monitor. Trigger.dev v4 fronts this at M2.
app.include_router(workflow.router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
