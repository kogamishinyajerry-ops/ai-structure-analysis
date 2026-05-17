from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...models.persistence import SimulationJob
from ...services.solver import get_solver_service
from ...services.analysis_service import get_analysis_service
# FM-04a Phase 20 A — close the Phase 19 E load-bearing finding:
# RunRequest.material_id was declared in Phase 18 E (round 3 honesty
# fix) but never consumed by the service layer. Both the FEA and UX
# Phase 19 E agents flagged this independently. compose_material_id_inp
# performs the file-system compose step (no ccx subprocess) so the
# (potentially) 30 s ccx invocation remains in the background.
from ...services.tier2_pipeline import (
    compose_material_id_inp,
    Tier2PipelineError,
)
from ...core.config import settings


router = APIRouter(prefix="/solver", tags=["求解控制"])

class RunRequest(BaseModel):
    case_id: str
    inp_path: Optional[str] = None
    analysis_type: str = "static" # static, modal, buckling
    num_modes: int = 5
    # FM-04a Phase 18 E (round 3 honesty fix) — declare the field
    # the frontend already sends so Pydantic stops silently dropping
    # it. The field is received but NOT yet plumbed into the solver
    # pipeline; tier_2_validated INP composition with this material
    # is a Phase 19 priority-0.5 item per the round-3 agent reports
    # (UX_round3.md + FEA_round3.md both flagged the previous
    # frontend-only state as a false claim). Default None preserves
    # back-compat for every pre-Phase-18 caller.
    material_id: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    # FM-04a Phase 20 A — surface what material the route actually
    # used. When material_id was supplied, this carries the resolved
    # citation string (e.g., "EN 10025-2:2019 §7.3"). When the legacy
    # path was taken, the field stays None for back-compat.
    material_reference: Optional[str] = None

@router.post("/run", response_model=JobResponse)
async def run_calculation(request: RunRequest, db: AsyncSession = Depends(get_db)):
    """启动仿真计算并记录到DB"""
    material_reference: Optional[str] = None
    if request.analysis_type == "static":
        # FM-04a Phase 20 A — material_id branch.
        # When the UI supplies a material_id (and does NOT pre-pin an
        # inp_path), compose a fresh Tier 2 minimal-hex INP using the
        # picked material's SSOT properties. The composed INP goes to
        # the case_dir at the same conventional path the legacy
        # fallback uses, so subsequent reads find it identically.
        # When material_id is absent OR an explicit inp_path is given,
        # the route falls through to the Phase 1-17 legacy behaviour
        # (back-compat with every pre-Phase-20 caller).
        if request.material_id and not request.inp_path:
            case_dir = settings.gs_root / request.case_id
            if not case_dir.is_dir():
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到 case 目录: {case_dir}",
                )
            jobname = request.case_id.replace("-", "").lower()
            try:
                composed_inp_path, _material, material_reference = (
                    compose_material_id_inp(
                        case_dir,
                        jobname=jobname,
                        material_id=request.material_id,
                    )
                )
            except Tier2PipelineError as exc:
                # 422 (not 500) per Phase 20 A anti-gaming A:-2:
                # an unknown material_id is a client-input problem,
                # not a server fault. The detail cites the library
                # SSOT so the reviewer knows where to look.
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"material_id 不在 library 中: {exc} "
                        f"(library 位于 backend/app/services/materials/"
                        f"library.json)"
                    ),
                ) from exc
            inp_file = composed_inp_path
        else:
            if request.inp_path:
                inp_file = Path(request.inp_path)
            else:
                inp_file = settings.gs_root / request.case_id / f"{request.case_id.lower()}.inp"

            if not inp_file.exists():
                # 兼容性处理
                inp_file = settings.gs_root / request.case_id / f"{request.case_id.replace('-','').lower()}.inp"

            if not inp_file.exists():
                raise HTTPException(status_code=404, detail=f"找不到输入文件: {inp_file}")

        solver = get_solver_service()
        job_id = await solver.run_simulation(inp_file)
    else:
        # 模态 或 屈曲
        analysis_svc = get_analysis_service()
        job_id = await analysis_svc.run_advanced_analysis(
            request.case_id,
            request.analysis_type,
            request.num_modes
        )

    # 记录到数据库
    new_job = SimulationJob(
        case_id=request.case_id,
        job_id=job_id,
        run_type=request.analysis_type.upper(),
        status="RUNNING"
    )
    db.add(new_job)
    await db.commit()

    return JobResponse(
        job_id=job_id,
        status="RUNNING",
        message="计算已启动并记录",
        material_reference=material_reference,
    )


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """查询计算状态"""
    solver = get_solver_service()
    status = solver.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="未找到任务")
    return status

@router.websocket("/ws/logs/{job_id}")
async def websocket_logs(websocket: WebSocket, job_id: str):
    """通过 WebSocket 实时推送日志 (Event-Driven)"""
    await websocket.accept()
    solver = get_solver_service()
    job = solver.jobs.get(job_id)
    
    if not job:
        await websocket.send_text("Error: Job not found")
        await websocket.close()
        return
        
    # 创建并注册订阅队列
    queue = asyncio.Queue()
    job.queues.add(queue)
    
    # 先推送已有的历史日志
    for log in job.logs:
        await websocket.send_text(log)
        
    try:
        while True:
            # 阻塞等待新日志
            log = await queue.get()
            await websocket.send_text(log)
            
            # 检查任务是否结束 (通过查看日志中的完成标志)
            if "--- Process Finished" in log or "[SYSTEM] Job terminated" in log:
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(f"Socket Error: {str(e)}")
        except:
            pass
    finally:
        # 清理队列订阅
        if job and queue in job.queues:
            job.queues.remove(queue)

@router.post("/stop/{job_id}")
async def stop_job(job_id: str):
    """停止正在运行的任务"""
    solver = get_solver_service()
    success = await solver.stop_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法停止任务 (任务可能已结束或不存在)")
    return {"status": "SUCCESS", "message": "任务已停止"}
