import re
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import asyncio

from .solver import get_solver_service

logger = logging.getLogger(__name__)

class SensitivityService:
    """参数敏感性分析服务"""

    def __init__(self):
        self.solver = get_solver_service()
        self.experiments: Dict[str, Any] = {}

    async def run_study(self, base_inp: Path, parameter: str, values: List[float]) -> str:
        """运行敏感性研究
        
        Args:
            base_inp: 基础 .inp 文件路径
            parameter: 参数类型 ('load', 'elastic_modulus')
            values: 参数值序列
            
        Returns:
            experiment_id: 实验唯一标识符
        """
        experiment_id = f"EXP_{base_inp.stem}_{parameter}"
        runs = []
        
        # 创建实验目录
        exp_dir = base_inp.parent / "experiments" / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        
        for i, val in enumerate(values):
            # 1. 生成新的 .inp 文件
            new_name = f"{base_inp.stem}_v{i}.inp"
            new_path = exp_dir / new_name
            self._modify_inp(base_inp, new_path, parameter, val)
            
            # 2. 提交到求解器
            job_id = await self.solver.run_simulation(new_path)
            runs.append({
                "iteration": i,
                "value": val,
                "job_id": job_id,
                "inp_path": str(new_path)
            })
            
        self.experiments[experiment_id] = {
            "id": experiment_id,
            "parameter": parameter,
            "base_case": base_inp.stem,
            "runs": runs,
            "status": "RUNNING"
        }
        
        return experiment_id

    def _modify_inp(self, src: Path, dest: Path, param: str, value: float):
        """修改 .inp 文件中的核心参数"""
        content = src.read_text(encoding='utf-8')
        
        if param == 'load':
            # 简化版: 替换 *CLOAD 下的所有负数值 (假设是 Y 向负载)
            # 寻找 *CLOAD 下面的行
            lines = content.split('\n')
            new_lines = []
            in_cload = False
            for line in lines:
                if line.startswith('*CLOAD'):
                    in_cload = True
                    new_lines.append(line)
                    continue
                if in_cload:
                    if line.startswith('*') or not line.strip():
                        in_cload = False
                    else:
                        # 替换该行的最后一个数值 (通常是载荷大小)
                        parts = line.split(',')
                        if len(parts) >= 3:
                            parts[-1] = f" {value}"
                            line = ",".join(parts)
                new_lines.append(line)
            content = "\n".join(new_lines)
            
        elif param == 'elastic_modulus':
            # 替换 *ELASTIC 下的第一行第一个数值
            lines = content.split('\n')
            new_lines = []
            in_elastic = False
            for line in lines:
                if line.startswith('*ELASTIC'):
                    in_elastic = True
                    new_lines.append(line)
                    continue
                if in_elastic:
                    parts = line.split(',')
                    parts[0] = f"{value}"
                    line = ",".join(parts)
                    in_elastic = False # 只在第一行替换
                new_lines.append(line)
            content = "\n".join(new_lines)
            
        dest.write_text(content, encoding='utf-8')

    def get_experiment_status(self, exp_id: str) -> Optional[Dict]:
        """合并所有 Job 状态"""
        exp = self.experiments.get(exp_id)
        if not exp: return None
        
        completed_count = 0
        all_metrics = []
        
        for run in exp["runs"]:
            job_id = run["job_id"]
            job_info = self.solver.get_job_status(job_id)
            if job_info:
                run["status"] = job_info["status"]
                if job_info["status"] == "COMPLETED":
                    completed_count += 1
                    # 可以在这里尝试增量解析结果以获取趋势
                    
        if completed_count == len(exp["runs"]):
            exp["status"] = "COMPLETED"
            
        return exp

# 单例
_sensitivity_service = None

def get_sensitivity_service():
    global _sensitivity_service
    if _sensitivity_service is None:
        _sensitivity_service = SensitivityService()
    return _sensitivity_service
