"""报告生成API路由
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from ...services.report_generator import ReportGenerator, ReportContent
from ...services.pdf_service import get_pdf_service
from ...db.session import get_db
from ...models.persistence import SimulationJob
from ...core.config import settings
from fastapi.responses import StreamingResponse


router = APIRouter(prefix="/report", tags=["报告生成"])

# 初始化生成器
report_gen = ReportGenerator()

class ReportResponse(BaseModel):
    success: bool
    summary: str
    metrics: dict
    validation: dict
    markdown: str

@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    file: UploadFile = File(...),
    case_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """生成分析报告
    
    上传CalculiX结果文件并生成自动分析报告
    """
    import tempfile
    from pathlib import Path
    
    suffix = Path(file.filename).suffix if file.filename else ".frd"
    
    try:
        # 1. 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # 2. 解析文件
            from ...parsers.frd_parser import FRDParser
            parser = FRDParser()
            result = parser.parse(tmp_path)
            
            if not result.success:
                raise HTTPException(status_code=400, detail=f"解析失败: {result.error_message}")
            
            # 3. 生成报告
            report = report_gen.generate(result, case_id=case_id)
            
            # 4. 持久化指标到 DB (Sprint 9)
            if case_id:
                # 寻找该 case 的最新 Job 或创建摘要 Job
                stmt = select(SimulationJob).where(SimulationJob.case_id == case_id).order_by(SimulationJob.created_at.desc()).limit(1)
                res = await db.execute(stmt)
                latest_job = res.scalar_one_or_none()
                
                if latest_job:
                    latest_job.metrics = report.metrics
                    latest_job.status = "COMPLETED"
                else:
                    new_job = SimulationJob(
                        case_id=case_id,
                        job_id="manual_upload",
                        run_type="REPORT_UPLOAD",
                        status="COMPLETED",
                        metrics=report.metrics
                    )
                    db.add(new_job)
                await db.commit()

            return ReportResponse(
                success=True,
                summary=report.summary,
                metrics=report.metrics,
                validation=report.validation,
                markdown=report.markdown
            )

            
        finally:
            # 清理
            Path(tmp_path).unlink(missing_ok=True)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/pdf/{case_id}")
async def export_report_pdf(case_id: str, db: AsyncSession = Depends(get_db)):
    """一键导出专业 PDF 报告"""
    # 1. 寻找结果文件 (.frd)
    # 基于 Sprint 9 的 Golden Sample 路径
    case_dir = settings.gs_root / case_id
    frd_file = case_dir / f"{case_id.lower()}.frd"
    
    if not frd_file.exists():
        # 兼容性处理
        frd_file = case_dir / f"{case_id.replace('-','').lower()}.frd"
        
    if not frd_file.exists():
        raise HTTPException(status_code=404, detail="未找到结果文件，请先运行仿真")
        
    try:
        # 2. 解析与生成数据
        from ...parsers.frd_parser import FRDParser
        parser = FRDParser()
        result = parser.parse(str(frd_file))
        
        report = report_gen.generate(result, case_id=case_id)
        
        # 3. 构造 PDF 数据对象
        pdf_data = {
            "case_id": case_id,
            "metrics": report.metrics,
            "increments": report.increments if hasattr(report, 'increments') else [],
            "markdown": report.markdown
        }
        
        # 4. 生成 PDF 流
        pdf_svc = get_pdf_service()
        pdf_buffer = pdf_svc.generate_report_pdf(pdf_data)
        
        filename = f"Report_{case_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")
