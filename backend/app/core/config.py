"""Application configuration using Pydantic Settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # API配置
    app_name: str = "AI-Structure-FEA"
    app_version: str = "0.1.0"
    debug: bool = False

    # OpenAI配置
    openai_api_key: str | None = None
    openai_model: str = "gpt-4-turbo-preview"

    # 数据库配置(后续Sprint使用)
    postgres_url: str | None = None
    mongo_url: str | None = None
    chroma_persist_dir: str | None = None

    # 文件上传配置
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: set = {".frd", ".dat", ".vtk"}

    # Agentic FEA Workflow Runtime — M2 (Trigger.dev v4 orchestration).
    # The Trigger.dev SECRET key (tr_sec_*) deliberately does NOT live here: in
    # the M2 topology the Node `trigger/` service holds it and mints the browser's
    # run-scoped public token. Python only (a) authenticates inbound
    # POST /workflow/stage/run calls from the Trigger.dev worker via this shared
    # secret, and (b) POSTs results back to the wait-token callback URL, whose
    # host must match trigger_api_base (SSRF guard).
    trigger_internal_secret: str | None = None  # shared secret for /workflow/stage/run
    trigger_api_base: str = "https://api.trigger.dev"  # allowed callback host
    # SSRF hardening (Codex M2 R0 P1): in production the wait-token callback host
    # is always the Trigger.dev API host, so loopback callbacks are rejected by
    # default. Local fake-orchestrator / self-host testing opts in explicitly
    # (the demo launcher + tests set this True). When True, ONLY loopback hosts
    # become additionally allowed — never arbitrary external hosts.
    trigger_allow_loopback_callback: bool = False

    # M4: when True, the Workflow Monitor's solver_run / post_processing /
    # result_analysis stages run a REAL CalculiX solve of the NAFEMS LE10
    # benchmark (σ_yy@D vs the published −5.38 MPa) instead of synthetic mock
    # numbers. Default False so CI (no ccx), the no-account demo, and the M2/M3
    # contract tests are unchanged. Tier 1 real-solver path; not signed validation.
    workflow_real_solver: bool = False

    # ADR-029 P0/P1 (graph-wiring north star): when True, the graph-wired stages are
    # driven by the REAL LangGraph compiled-graph runtime (a dedicated truncated StateGraph
    # compiled and .invoke()d) instead of a direct node.run() call through the facade —
    # PROJECT_INTAKE via START->architect->END (P0), GEOMETRY_VALIDATION via
    # START->architect->geometry->END (P1, the first cross-node graph data dependency), and
    # MESH_GENERATION via START->architect->geometry->mesh->END (P2, the second cross-node
    # dependency). This is an ARCHITECTURE-wiring proof that the orphaned agents/graph.py
    # machinery can drive live stages. Intake/geometry do NOT change provenance or N/13 (already
    # deterministic_agent off-flag); MESH_GENERATION is the one honest increment — a real mesh
    # node now drives it (scripted_demo -> deterministic_agent, tier_0_dummy with the
    # dummyFidelityInputs guard), so N/13 rises by exactly 1, at DUMMY fidelity (never a
    # validation). The mesh node runs gmsh's hardcoded fallback (no real gmsh kernel) and no
    # solver/human_fallback node (no ccx, no Notion side-effect); outside the triple-dummy regime
    # the mesh stage stays scripted (a real mesh is never mislabeled tier_0). Default False so CI
    # + the contract suite are byte-identical (the branch is dead).
    # (Name retained from P0 for flag stability; it now gates intake + geometry + mesh.)
    workflow_graph_intake: bool = False

    @property
    def gs_root(self):
        from pathlib import Path

        return Path(__file__).parent.parent.parent.parent / "golden_samples"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# 全局配置实例
settings = Settings()
