"""
FastAPI主应用入口
"""
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from agents.orchestrator import orchestrator
from models.schemas import AsyncSessionLocal, init_db
from api.routes_agents import router as agents_router
from api.routes_indicators import router as indicators_router
from api.routes_cases import router as cases_router
from api.routes_policy_documents import router as policy_documents_router
from runtime_config import get_app_port, get_cors_allow_origins, get_docs_url, get_reload_enabled


load_dotenv()


async def policy_crawl_job():
    """定时抓取任务：自动抓取政策/标准文档。"""
    async with AsyncSessionLocal() as db:
        await orchestrator.policy_agent.crawl_latest_documents(db=db)


async def periodic_policy_crawl(interval_minutes: int):
    """后台循环任务：按固定间隔执行政策抓取。"""
    while True:
        try:
            await policy_crawl_job()
        except asyncio.CancelledError:
            # Graceful shutdown/reload: stop loop quietly.
            break
        except Exception as exc:
            print(f"[WARN] 政策抓取任务异常: {exc}")
        try:
            await asyncio.sleep(interval_minutes * 60)
        except asyncio.CancelledError:
            break

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()

    # 启动定时抓取（默认每6小时，可通过环境变量关闭）。
    crawl_enabled = os.getenv("POLICY_CRAWL_ENABLED", "true").lower() == "true"
    interval_minutes = int(os.getenv("POLICY_CRAWL_INTERVAL_MINUTES", "360"))
    periodic_task = None
    if crawl_enabled:
        periodic_task = asyncio.create_task(periodic_policy_crawl(interval_minutes))

    print("[OK] 数据库初始化完成")
    if crawl_enabled:
        print(f"[OK] 政策抓取定时任务已启动：每 {interval_minutes} 分钟执行一次")
    else:
        print("[INFO] 政策抓取定时任务已禁用（POLICY_CRAWL_ENABLED=false）")
    print("[OK] 应用启动成功")
    print(f"API文档: {get_docs_url()}")
    yield
    if periodic_task:
        periodic_task.cancel()
    print("[INFO] 应用关闭")

app = FastAPI(
    title="面向主流价值的多维度数据评估指标自动构建工具",
    description="基于多智能体协同的数据评估指标挖掘系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(agents_router)
app.include_router(indicators_router)
app.include_router(cases_router)
app.include_router(policy_documents_router)

@app.get("/")
async def root():
    return {
        "message": "面向主流价值的多维度数据评估指标自动构建工具",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn

    reload_enabled = get_reload_enabled()
    print(f"[INFO] Uvicorn reload: {'enabled' if reload_enabled else 'disabled'}")

    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=get_app_port(),
        reload=reload_enabled
    )
