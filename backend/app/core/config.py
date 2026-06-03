"""Application configuration using Pydantic Settings"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # API配置
    app_name: str = "AI-Structure-FEA"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # OpenAI配置
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    
    # 数据库配置(后续Sprint使用)
    postgres_url: Optional[str] = None
    mongo_url: Optional[str] = None
    chroma_persist_dir: Optional[str] = None
    
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
    trigger_internal_secret: Optional[str] = None  # shared secret for /workflow/stage/run
    trigger_api_base: str = "https://api.trigger.dev"  # allowed callback host
    # SSRF hardening (Codex M2 R0 P1): in production the wait-token callback host
    # is always the Trigger.dev API host, so loopback callbacks are rejected by
    # default. Local fake-orchestrator / self-host testing opts in explicitly
    # (the demo launcher + tests set this True). When True, ONLY loopback hosts
    # become additionally allowed — never arbitrary external hosts.
    trigger_allow_loopback_callback: bool = False

    @property
    def gs_root(self):
        from pathlib import Path
        return Path(__file__).parent.parent.parent.parent / "golden_samples"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


# 全局配置实例
settings = Settings()
