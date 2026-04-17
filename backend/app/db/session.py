from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

# SQLite 异步连接字符串
# 使用本地文件 structural_workbench.db
DATABASE_URL = "sqlite+aiosqlite:///./structural_workbench.db"

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # 对于 SQLite, StaticPool 有助于异步环境下的稳定性
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 声明式基类
class Base(DeclarativeBase):
    pass

# 依赖项: 获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """初始化数据库表 (在 main.py 调用)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
