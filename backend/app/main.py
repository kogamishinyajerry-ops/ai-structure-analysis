"""FastAPI主应用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api import result_router, nl_router
from .api.routes import knowledge, visualization, frd, report, cases, solver, sensitivity, projects

from .db.session import init_db, get_db
from .models import persistence # Ensure models are loaded for create_all
from .services.case_service import get_case_service



# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="有限元分析后处理智能助手API",
    docs_url="/docs",
    redoc_url="/redoc"
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(result_router, prefix="/api/v1")
app.include_router(nl_router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(visualization.router, prefix="/api/v1")
app.include_router(frd.router, prefix="/api/v1")
app.include_router(report.router, prefix="/api/v1")
app.include_router(cases.router, prefix="/api/v1")
app.include_router(solver.router, prefix="/api/v1")
app.include_router(sensitivity.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
