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
