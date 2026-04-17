import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .solver import get_solver_service
from .sensitivity import get_sensitivity_service
from ..core.config import settings

logger = logging.getLogger(__name__)

class CopilotService:
    """设计副驾驶服务 - 执行由自然语言解析出的动作"""

    def __init__(self):
        self.solver = get_solver_service()
        self.sensitivity = get_sensitivity_service()

    async def execute_action(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行特定动作
        
        Args:
            action: 动作定义 {action_type, parameters, description}
            context: 上下文 {case_id, ...}
            
        Returns:
            执行结果
        """
        action_type = action.get("action_type")
        params = action.get("parameters", {})
        case_id = context.get("case_id") if context else None

        if not case_id:
            return {"success": False, "message": "缺失 case_id 上下文"}

        try:
            if action_type == "run_simulation":
                # 单次模拟
                # 如果有参数修改，需要先生成临时 .inp
                base_inp = settings.gs_root / case_id / f"{case_id.lower()}.inp"
                target_param = params.get("target_param")
                value = params.get("value")
                
                if target_param and value:
                    # 复用 sensitivity 中的修改逻辑，但只运行一次
                    # 先生成一个临时文件
                    temp_inp = settings.gs_root / case_id / "experiments" / f"copilot_temp_{int(value)}.inp"
                    temp_inp.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 我们需要引用 sensitivity_service 的修改函数
                    self.sensitivity._modify_inp(base_inp, temp_inp, target_param, float(value))
                    job_id = await self.solver.run_simulation(temp_inp)
                else:
                    job_id = await self.solver.run_simulation(base_inp)
                    
                return {
                    "success": True, 
                    "action": "run_simulation",
                    "job_id": job_id,
                    "message": f"计算任务已启动 (ID: {job_id})"
                }

            elif action_type == "run_study" or action_type == "optimize":
                # 敏感性研究
                target_param = params.get("target_param") or "load"
                val_range = params.get("range") # [min, max, steps]
                
                if not val_range or len(val_range) < 2:
                    return {"success": False, "message": "缺少范围参数"}
                
                min_val = float(val_range[0])
                max_val = float(val_range[1])
                steps = int(val_range[2]) if len(val_range) > 2 else 3
                
                step_size = (max_val - min_val) / (steps - 1) if steps > 1 else 0
                values = [min_val + step_size * i for i in range(steps)]
                
                base_inp = settings.gs_root / case_id / f"{case_id.lower()}.inp"
                exp_id = await self.sensitivity.run_study(base_inp, target_param, values)
                
                return {
                    "success": True,
                    "action": "run_study",
                    "experiment_id": exp_id,
                    "message": f"敏感性研究已启动 (Exp ID: {exp_id})"
                }
            
            else:
                return {"success": False, "message": f"未知的动作类型: {action_type}"}

        except Exception as e:
            logger.error(f"执行动作失败: {e}")
            return {"success": False, "message": f"执行失败: {str(e)}"}

# 单例
_copilot_service = None

def get_copilot_service():
    global _copilot_service
    if _copilot_service is None:
        _copilot_service = CopilotService()
    return _copilot_service
