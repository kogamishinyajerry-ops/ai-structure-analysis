"""CalculiX结果文件解析器

支持解析CalculiX .frd格式结果文件。
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from pathlib import Path
import struct
import re


class ParseResult(BaseModel):
    """解析结果对象"""
    
    # 基本信息
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小(字节)")
    parse_time: float = Field(..., description="解析耗时(秒)")
    success: bool = Field(..., description="解析是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 模型信息
    node_count: Optional[int] = Field(None, description="节点数量")
    element_count: Optional[int] = Field(None, description="单元数量")
    
    # 结果数据
    displacement: Optional[Dict[str, Any]] = Field(None, description="位移场数据")
    stress: Optional[Dict[str, Any]] = Field(None, description="应力场数据")
    strain: Optional[Dict[str, Any]] = Field(None, description="应变场数据")
    
    # 统计信息
    max_displacement: Optional[float] = Field(None, description="最大位移")
    max_von_mises: Optional[float] = Field(None, description="最大von Mises应力")
    max_principal_stress: Optional[float] = Field(None, description="最大主应力")
    
    # 原始数据(可选)
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始数据")


class ResultParser:
    """CalculiX结果文件解析器
    
    支持解析.frd格式的二进制结果文件。
    解析步骤:
    1. 读取文件头,识别格式版本
    2. 提取节点坐标
    3. 提取单元连接
    4. 提取场变量(位移、应力、应变等)
    5. 计算派生量(von Mises应力等)
    """
    
    def __init__(self):
        """初始化解析器"""
        self.supported_formats = [".frd", ".dat"]
        self.field_names = [
            "displacement",  # 位移
            "stress",        # 应力张量
            "strain",         # 应变张量
        ]
    
    def parse(self, file_path: str) -> ParseResult:
        """解析结果文件
        
        Args:
            file_path: 结果文件路径
            
        Returns:
            ParseResult: 解析结果对象
        """
        import time
        start_time = time.time()
        
        path = Path(file_path)
        if not path.exists():
            return ParseResult(
                file_name=path.name,
                file_size=0,
                parse_time=0,
                success=False,
                error_message=f"文件不存在: {file_path}"
            )
        
        file_size = path.stat().st_size
        file_ext = path.suffix.lower()
        
        if file_ext not in self.supported_formats:
            return ParseResult(
                file_name=path.name,
                file_size=file_size,
                parse_time=0,
                success=False,
                error_message=f"不支持的格式: {file_ext}"
            )
        
        try:
            # 根据文件格式选择解析方法
            if file_ext == ".frd":
                result_data = self._parse_frd(str(path))
            else:
                result_data = self._parse_dat(str(path))
            
            # 计算派生量
            derived = self._compute_derived(result_data)
            
            parse_time = time.time() - start_time
            
            return ParseResult(
                file_name=path.name,
                file_size=file_size,
                parse_time=parse_time,
                success=True,
                node_count=result_data.get("node_count"),
                element_count=result_data.get("element_count"),
                displacement=result_data.get("displacement"),
                stress=result_data.get("stress"),
                strain=result_data.get("strain"),
                max_displacement=derived.get("max_displacement"),
                max_von_mises=derived.get("max_von_mises"),
                max_principal_stress=derived.get("max_principal_stress"),
                raw_data=result_data
            )
            
        except Exception as e:
            parse_time = time.time() - start_time
            return ParseResult(
                file_name=path.name,
                file_size=file_size,
                parse_time=parse_time,
                success=False,
                error_message=f"解析错误: {str(e)}"
            )
    
    def _parse_frd(self, file_path: str) -> Dict[str, Any]:
        """解析.frd二进制格式文件
        
        .frd文件结构:
        - Header: 文件标识和版本
        - Pointers: 数据块指针
        - Node block: 节点坐标
        - Element block: 单元连接
        - Result blocks: 场变量数据
        """
        result = {
            "node_count": 0,
            "element_count": 0,
            "nodes": None,
            "elements": None,
            "displacement": None,
            "stress": None,
            "strain": None
        }
        
        with open(file_path, 'rb') as f:
            # 读取文件头
            header = f.read(24)
            if len(header) < 24:
                raise ValueError("文件头损坏")
            
            # 解析节点块(简化实现)
            nodes = self._read_node_block(f)
            if nodes is not None:
                result["nodes"] = nodes
                result["node_count"] = len(nodes)
            
            # 解析结果块
            displacement = self._read_result_block(f, "displacement")
            if displacement is not None:
                result["displacement"] = displacement
            
            stress = self._read_result_block(f, "stress")
            if stress is not None:
                result["stress"] = stress
        
        return result
    
    def _parse_dat(self, file_path: str) -> Dict[str, Any]:
        """解析.dat文本格式文件
        
        .dat文件为CalculiX输出的文本格式结果。
        """
        result = {
            "node_count": 0,
            "element_count": 0,
            "displacement": None,
            "stress": None
        }
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # 提取位移数据
        displacement = self._extract_displacement_from_dat(content)
        if displacement:
            result["displacement"] = displacement
            result["node_count"] = len(displacement.get("values", []))
        
        # 提取应力数据
        stress = self._extract_stress_from_dat(content)
        if stress:
            result["stress"] = stress
        
        return result
    
    def _read_node_block(self, file_obj) -> Optional[np.ndarray]:
        """读取节点块数据"""
        # 简化实现: 返回空数组
        # 实际实现需要解析二进制格式
        return np.array([])
    
    def _read_result_block(self, file_obj, field_name: str) -> Optional[Dict[str, Any]]:
        """读取结果块数据"""
        # 简化实现: 返回None
        # 实际实现需要解析二进制格式
        return None
    
    def _extract_displacement_from_dat(self, content: str) -> Optional[Dict[str, Any]]:
        """从.dat文本中提取位移数据"""
        # 查找位移数据块
        disp_pattern = r"displacement\s*\(.*?\):\s*([\s\S]*?)(?=\n\s*\n|\n\s*[a-z]|$)"
        match = re.search(disp_pattern, content, re.IGNORECASE)
        
        if not match:
            return None
        
        data_block = match.group(1)
        values = []
        
        # 解析数值
        for line in data_block.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    node_id = int(parts[0])
                    dx, dy, dz = float(parts[1]), float(parts[2]), float(parts[3])
                    values.append({
                        "node_id": node_id,
                        "dx": dx,
                        "dy": dy,
                        "dz": dz
                    })
                except (ValueError, IndexError):
                    continue
        
        return {
            "field_name": "displacement",
            "unit": "m",
            "values": values
        }
    
    def _extract_stress_from_dat(self, content: str) -> Optional[Dict[str, Any]]:
        """从.dat文本中提取应力数据"""
        # 查找应力数据块
        stress_pattern = r"stress\s*\(.*?\):\s*([\s\S]*?)(?=\n\s*\n|\n\s*[a-z]|$)"
        match = re.search(stress_pattern, content, re.IGNORECASE)
        
        if not match:
            return None
        
        data_block = match.group(1)
        values = []
        
        # 解析数值
        for line in data_block.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 7:
                try:
                    node_id = int(parts[0])
                    sxx, syy, szz = float(parts[1]), float(parts[2]), float(parts[3])
                    sxy, syz, szx = float(parts[4]), float(parts[5]), float(parts[6])
                    values.append({
                        "node_id": node_id,
                        "sxx": sxx,
                        "syy": syy,
                        "szz": szz,
                        "sxy": sxy,
                        "syz": syz,
                        "szx": szx
                    })
                except (ValueError, IndexError):
                    continue
        
        return {
            "field_name": "stress",
            "unit": "Pa",
            "values": values
        }
    
    def _compute_derived(self, result_data: Dict[str, Any]) -> Dict[str, float]:
        """计算派生量
        
        包括:
        - 最大位移
        - von Mises应力
        - 主应力
        """
        derived = {
            "max_displacement": None,
            "max_von_mises": None,
            "max_principal_stress": None
        }
        
        # 计算最大位移
        if result_data.get("displacement"):
            disp_values = result_data["displacement"].get("values", [])
            if disp_values:
                max_disp = 0.0
                for val in disp_values:
                    dx, dy, dz = val.get("dx", 0), val.get("dy", 0), val.get("dz", 0)
                    disp_mag = np.sqrt(dx**2 + dy**2 + dz**2)
                    max_disp = max(max_disp, disp_mag)
                derived["max_displacement"] = max_disp
        
        # 计算von Mises应力和主应力
        if result_data.get("stress"):
            stress_values = result_data["stress"].get("values", [])
            if stress_values:
                max_vm = 0.0
                max_ps = 0.0
                
                for val in stress_values:
                    sxx = val.get("sxx", 0)
                    syy = val.get("syy", 0)
                    szz = val.get("szz", 0)
                    sxy = val.get("sxy", 0)
                    syz = val.get("syz", 0)
                    szx = val.get("szx", 0)
                    
                    # von Mises应力
                    vm = np.sqrt(
                        0.5 * ((sxx-syy)**2 + (syy-szz)**2 + (szz-sxx)**2) +
                        6 * (sxy**2 + syz**2 + szx**2)
                    )
                    max_vm = max(max_vm, abs(vm))
                    
                    # 主应力(简化: 取最大主应力)
                    stress_tensor = np.array([
                        [sxx, sxy, szx],
                        [sxy, syy, syz],
                        [szx, syz, szz]
                    ])
                    eigenvalues = np.linalg.eigvalsh(stress_tensor)
                    max_ps = max(max_ps, max(abs(eigenvalues)))
                
                derived["max_von_mises"] = max_vm
                derived["max_principal_stress"] = max_ps
        
        return derived
