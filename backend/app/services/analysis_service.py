import re
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import asyncio

from .solver import get_solver_service
from ..core.config import settings

logger = logging.getLogger(__name__)

class AnalysisService:
    """高级分析服务 (模态、振型、稳定性)"""

    def __init__(self):
        self.solver = get_solver_service()

    async def run_advanced_analysis(self, case_id: str, analysis_type: str, num_modes: int = 5) -> str:
        """运行高级分析 (模态或位移)
        
        Args:
            case_id: 案例标识
            analysis_type: 'modal' or 'buckling'
            num_modes: 提取的模态数量
            
        Returns:
            job_id: 求解器任务ID
        """
        # 1. 寻找基础 inp
        base_dir = settings.gs_root / case_id
        src_inp = base_dir / f"{case_id.lower()}.inp"
        
        if not src_inp.exists():
            # 兼容性处理
            src_inp = base_dir / f"{case_id.replace('-','').lower()}.inp"
            
        # 2. 创建实验目录
        work_dir = base_dir / "analysis" / analysis_type
        work_dir.mkdir(parents=True, exist_ok=True)
        dest_inp = work_dir / f"{analysis_type}_analysis.inp"
        
        # 3. 变换 inp
        self._transform_inp(src_inp, dest_inp, analysis_type, num_modes)
        
        # 4. 执行
        job_id = await self.solver.run_simulation(dest_inp)
        return job_id

    def _transform_inp(self, src: Path, dest: Path, analysis_type: str, num_modes: int):
        """将静态分析 .inp 转换为 模态 or 屈曲分析"""
        content = src.read_text(encoding='utf-8')
        
        # 移除原有的 STEP 块 (贪婪匹配第一个 *STEP 到最后一个 *END STEP)
        # 实际 CCX 可能会有多个 STEP，这里简化处理只保留模型定义
        header = content.split("*STEP")[0]
        
        # 确保材料有密度 (模态分析必需)
        if analysis_type == 'modal' and '*DENSITY' not in header.upper():
            # 尝试在 *MATERIAL 后注入一个默认密度 (Steel)
            header = re.sub(
                r'(\*MATERIAL, NAME=.*?\n)', 
                r'\1*DENSITY\n7.85E-9\n', 
                header, 
                flags=re.IGNORECASE
            )

        new_step = ""
        if analysis_type == 'modal':
            new_step = f"""*STEP
*FREQUENCY
{num_modes}
*NODE FILE
U
*END STEP
"""
        elif analysis_type == 'buckling':
            # 屈曲分析需要一个初始载荷步
            # 这里简化处理，直接使用 *BUCKLE
            new_step = f"""*STEP
*BUCKLE
{num_modes}
*NODE FILE
U
*END STEP
"""

        dest.write_text(header + new_step, encoding='utf-8')

# 单例
_analysis_service = None

def get_analysis_service():
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service
