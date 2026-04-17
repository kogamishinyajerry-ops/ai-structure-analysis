"""CalculiX .frd格式完整解析器

支持CalculiX result文件中所有数据块的解析
"""
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class FRDNode:
    """FRD节点数据"""
    node_id: int
    coords: Tuple[float, float, float]
    displacement: Optional[Tuple[float, float, float]] = None


@dataclass
class FRDElement:
    """FRD单元数据"""
    element_id: int
    element_type: str
    nodes: List[int]


@dataclass
class FRDStress:
    """FRD应力数据"""
    node_id: int
    S11: Optional[float] = None
    S22: Optional[float] = None
    S33: Optional[float] = None
    S12: Optional[float] = None
    S13: Optional[float] = None
    S23: Optional[float] = None
    max_principal: Optional[float] = None
    mid_principal: Optional[float] = None
    min_principal: Optional[float] = None
    von_mises: Optional[float] = None


@dataclass
class FRDIncrement:
    """FRD 增量/模态数据"""
    index: int
    step: int
    type: str # 'static', 'vibration', 'buckling'
    value: float # 频率 or 载荷因子
    displacements: Dict[int, Tuple[float, float, float]] = field(default_factory=dict)
    stresses: Dict[int, FRDStress] = field(default_factory=dict)
    max_displacement: float = 0.0
    max_von_mises: float = 0.0

@dataclass
class FRDParseResult:
    """FRD解析结果"""
    file_name: str
    file_size: int
    parse_time: float
    nodes: Dict[int, FRDNode] = field(default_factory=dict)
    elements: Dict[int, FRDElement] = field(default_factory=dict)
    # 兼容性字段 (保留最后一个增量)
    displacements: Dict[int, Tuple[float, float, float]] = field(default_factory=dict)
    stresses: Dict[int, FRDStress] = field(default_factory=dict)
    strains: Dict[int, Any] = field(default_factory=dict)
    max_displacement: Optional[float] = None
    max_von_mises: Optional[float] = None
    # 多增量支持
    increments: List[FRDIncrement] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    is_binary: bool = False


class FRDParser:
    """CalculiX .frd文件解析器"""

    def __init__(self):
        """初始化解析器"""
        self._reset_state()

    def _reset_state(self) -> None:
        """重置解析状态，避免跨文件污染。"""
        self.nodes: Dict[int, FRDNode] = {}
        self.elements: Dict[int, FRDElement] = {}
        self.displacements: Dict[int, Tuple[float, float, float]] = {}
        self.stresses: Dict[int, FRDStress] = {}
        self.strains: Dict[int, FRDStress] = {}
        self.latest_displacements: Dict[int, Tuple[float, float, float]] = {}
        self.latest_stresses: Dict[int, FRDStress] = {}
        self.latest_strains: Dict[int, FRDStress] = {}
        self.increments: List[FRDIncrement] = []
        self.current_inc_meta: Dict[str, Any] = {}
        self.is_binary = False

    def parse(self, file_path: str) -> FRDParseResult:
        """解析.frd文件"""
        import time
        start_time = time.time()
        self._reset_state()

        path = Path(file_path)
        if not path.exists():
            return FRDParseResult(
                file_name=path.name,
                file_size=0,
                parse_time=0,
                success=False,
                error_message=f"文件不存在: {file_path}"
            )

        file_size = path.stat().st_size
        
        try:
            raw_data = path.read_bytes()
            if b'\x00' in raw_data[:1024]:
                self.is_binary = True
                content = raw_data.decode('latin-1')  # Fallback decode to scan text headers anyway
            else:
                content = raw_data.decode('utf-8', errors='replace')
        except Exception as e:
            return FRDParseResult(
                file_name=path.name,
                file_size=file_size,
                parse_time=time.time() - start_time,
                success=False,
                error_message=f"读取文件失败: {str(e)}"
            )

        try:
            self._parse_content(content)
            self._calculate_maxima()
        except Exception as e:
            logger.error(f"FRD解析错误: {e}")
            return FRDParseResult(
                file_name=path.name,
                file_size=file_size,
                parse_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )

        return FRDParseResult(
            file_name=path.name,
            file_size=file_size,
            parse_time=time.time() - start_time,
            nodes=self.nodes,
            elements=self.elements,
            displacements=self.latest_displacements or self.displacements,
            stresses=self.latest_stresses or self.stresses,
            strains=self.latest_strains or self.strains,
            max_displacement=self._calc_max_displacement(
                self.latest_displacements or self.displacements
            ),
            max_von_mises=self._calc_max_von_mises(self.latest_stresses or self.stresses),
            increments=self.increments,
            is_binary=self.is_binary
        )

    def _parse_content(self, content: str) -> None:
        """解析FRD文件内容"""
        lines = content.split('\n')
        i = 0
        current_step = 1

        while i < len(lines):
            line = lines[i].strip()

            # 跳过空行
            if not line:
                i += 1
                continue

            # 优先解析块标识符 (2C, 3C, -4, -5, 1P)
            # 这些是精确的块开头，不应该被其他内容匹配覆盖
            if line.startswith('2C') or line.startswith('2 '):
                # 节点坐标块
                i = self._parse_node_block(lines, i)

            elif line.startswith('3C') or line.startswith('3 '):
                # 单元块
                i = self._parse_element_block(lines, i)

            elif line.startswith('-4 '):
                # 数据块开头 (-4 DISP, -4 STRESS, etc.)
                # 提取块类型
                parts = line.split()
                if len(parts) >= 2:
                    block_type = parts[1].upper()
                    if block_type == 'DISP':
                        i = self._parse_disp_block(lines, i)
                    elif block_type == 'STRESS':
                        i = self._parse_stress_block(lines, i)
                    elif 'STRAIN' in block_type or block_type == 'TOST':
                        i = self._parse_strain_block(lines, i)
                    else:
                        i = self._skip_block(lines, i)
                else:
                    i += 1

            elif line.startswith('-5 '):
                # 字段定义行 - 跳过
                i += 1

            elif line.startswith('1P'):
                # Step信息
                parts = line.replace('1PSTEP', '').split()
                if parts:
                    try:
                        current_step = int(parts[0])
                    except:
                        pass
                i += 1

            elif line.startswith('100CL'):
                # 增量/模态 头部信息
                # 格式: 100CL <value> <type> <step> <inc> <val>
                try:
                    # 先保存上一个增量 (如果存在数据)
                    if self.displacements or self.stresses:
                        self._save_current_increment()

                    parts = line.split()
                    if len(parts) >= 3:
                        self.current_inc_meta = {
                            'step': current_step,
                            'index': len(self.increments) + 1,
                            'value': float(parts[2]),
                            'type': 'static',
                        }
                        # 重置当前增量数据
                        self.displacements = {}
                        self.stresses = {}
                except:
                    pass
                i += 1

            elif line.startswith('1C'):
                # 增量结束
                if self.displacements or self.stresses:
                    self._save_current_increment()
                i += 1

            # 以下是旧的宽松匹配逻辑，保留作为fallback
            elif 'DISP' in line.upper() and not line.startswith('1'):
                # 位移块 (避免匹配1UDISPLAY等)
                i = self._parse_disp_block(lines, i)

            elif 'STRESS' in line.upper() and not line.startswith('1'):
                # 应力块 (避免匹配1U...Stress...)
                i = self._parse_stress_block(lines, i)

            elif 'STRAIN' in line.upper() and not line.startswith('1'):
                # 应变块
                i = self._parse_strain_block(lines, i)

            else:
                i += 1

        if self.displacements or self.stresses:
            self._save_current_increment()

    def _save_current_increment(self) -> None:
        """保存当前解析到的增量数据到列表"""
        if not self.displacements and not self.stresses:
            return

        current_idx = self.current_inc_meta.get('index', len(self.increments) + 1)
        step = self.current_inc_meta.get('step', 1)

        inc = FRDIncrement(
            index=current_idx,
            step=step,
            type=self.current_inc_meta.get('type', 'static'),
            value=self.current_inc_meta.get('value', 0.0),
            displacements=self.displacements.copy(),
            stresses=self.stresses.copy(),
            max_displacement=self._calc_max_displacement(self.displacements) or 0.0,
            max_von_mises=self._calc_max_von_mises(self.stresses) or 0.0
        )
        self.increments.append(inc)
        if self.displacements:
            self.latest_displacements = self.displacements.copy()
        if self.stresses:
            self.latest_stresses = self.stresses.copy()

    def _parse_node_block(self, lines: List[str], start_idx: int) -> int:
        """解析节点坐标块

        格式:
        2C                            44                                     1
        -1         1 0.00000E+00 0.00000E+00 0.00000E+00
        ...
        -3
        """
        i = start_idx + 1

        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('-3'):
                # 块结束
                break

            if line.startswith('-1'):
                # 节点数据行
                # 格式: -1 NODE_ID X Y Z
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        node_id = int(float(parts[1]))
                        x = float(parts[2])
                        y = float(parts[3])
                        z = float(parts[4])
                        self.nodes[node_id] = FRDNode(
                            node_id=node_id,
                            coords=(x, y, z)
                        )
                    except (ValueError, IndexError):
                        pass

            i += 1

        return i

    def _parse_element_block(self, lines: List[str], start_idx: int) -> int:
        """解析单元块"""
        i = start_idx + 1
        current_element_id: Optional[int] = None
        current_element_type = "UNKNOWN"
        current_nodes: List[int] = []

        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('-1') and current_element_id is not None:
                self.elements[current_element_id] = FRDElement(
                    element_id=current_element_id,
                    element_type=current_element_type,
                    nodes=current_nodes.copy(),
                )
                current_element_id = None
                current_nodes = []

            if line.startswith('-3'):
                if current_element_id is not None:
                    self.elements[current_element_id] = FRDElement(
                        element_id=current_element_id,
                        element_type=current_element_type,
                        nodes=current_nodes.copy(),
                    )
                break

            if line.startswith('-1'):
                # 单元头
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        current_element_id = int(float(parts[1]))
                        current_element_type = parts[2] if len(parts) >= 3 else "UNKNOWN"
                        current_nodes = []
                    except (ValueError, IndexError):
                        pass
            elif line.startswith('-2') and current_element_id is not None:
                parts = line.split()
                try:
                    current_nodes.extend(int(float(p)) for p in parts[2:] if p)
                except (ValueError, IndexError):
                    pass

            i += 1

        return i

    def _parse_disp_block(self, lines: List[str], start_idx: int) -> int:
        """解析位移块

        格式:
        -4  DISP        4    1
        -5  D1          1    2    1    0
        -5  D2          1    2    2    0
        -5  D3          1    2    3    0
        -5  ALL         1    2    0    0    1ALL
        -1         1 0.00000E+00 0.00000E+00 0.00000E+00
        OR (no space between node_id and values):
        -1         2-6.72393E-03-7.21917E-03-1.35275E-03
        ...
        -3
        """
        i = start_idx + 1

        # 跳过字段定义行
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('-1') or line.startswith('-3'):
                break
            i += 1

        # 解析位移数据
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('-3'):
                break

            if line.startswith('-1'):
                # 解析位移行
                # 格式: -1 NODE_ID UX UY UZ (可能没有空格分隔)
                try:
                    # 去掉-1前缀
                    data = line[2:].strip()
                    
                    import re
                    # 先找节点ID (整数)
                    node_match = re.match(r'(\d+)', data)
                    if node_match:
                        node_id = int(node_match.group(1))
                        # 剩余部分找科学计数法数值
                        remaining = data[node_match.end():]
                        pattern = r'([\-\+]?\d+\.?\d*[eE][\-\+]?\d+)'
                        values = re.findall(pattern, remaining)
                        
                        if len(values) >= 3:
                            ux = float(values[0])
                            uy = float(values[1])
                            uz = float(values[2])
                            self.displacements[node_id] = (ux, uy, uz)

                            # 更新节点数据
                            if node_id in self.nodes:
                                self.nodes[node_id].displacement = (ux, uy, uz)
                except Exception as e:
                    pass

            i += 1

        return i

    def _parse_stress_block(self, lines: List[str], start_idx: int) -> int:
        """解析应力块

        格式:
        -4  STRESS      6    1
        -5  SXX         1    4    1    1
        -5  SYY         1    4    2    2
        -5  SZZ         1    4    3    3
        -5  SXY         1    4    1    2
        -5  SYZ         1    4    2    3
        -5  SZX         1    4    3    1
        -1         1-1.90079E+02-8.14624E+01-8.14622E+01-5.83082E+01 7.75047E-05-1.09259E+01
        ...
        -3
        """
        i = start_idx + 1

        # 跳过字段定义行
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('-1') or line.startswith('-3'):
                break
            i += 1

        # 解析应力数据
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('-3'):
                break

            if line.startswith('-1'):
                # 解析应力行 - 使用正则表达式处理科学计数法
                import re
                # 先找节点ID (整数)
                data = line[2:].strip()
                node_match = re.match(r'(\d+)', data)
                
                if node_match:
                    try:
                        node_id = int(node_match.group(1))
                        remaining = data[node_match.end():]
                        pattern = r'([\-\+]?\d+\.?\d*[eE][\-\+]?\d+)'
                        values = re.findall(pattern, remaining)
                        
                        if len(values) >= 6:
                            sxx = float(values[0])
                            syy = float(values[1])
                            szz = float(values[2])
                            sxy = float(values[3])
                            syz = float(values[4])
                            szx = float(values[5])

                            self.stresses[node_id] = FRDStress(
                                node_id=node_id,
                                S11=sxx,
                                S22=syy,
                                S33=szz,
                                S12=sxy,
                                S13=szx,
                                S23=syz
                            )
                    except (ValueError, IndexError):
                        pass

            i += 1

        return i

    def _parse_strain_block(self, lines: List[str], start_idx: int) -> int:
        """解析应变块, 复用应力数据结构"""
        self.strains = {}
        i = start_idx + 1
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('-1') or line.startswith('-3'): break
            i += 1
            
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('-3'): break
            if line.startswith('-1'):
                import re
                data = line[2:].strip()
                node_match = re.match(r'(\d+)', data)
                if node_match:
                    try:
                        node_id = int(node_match.group(1))
                        remaining = data[node_match.end():]
                        values = re.findall(r'([\-\+]?\d+\.?\d*[eE][\-\+]?\d+)', remaining)
                        if len(values) >= 6:
                            self.strains[node_id] = FRDStress(
                                node_id=node_id,
                                S11=float(values[0]), S22=float(values[1]), S33=float(values[2]),
                                S12=float(values[3]), S23=float(values[4]), S13=float(values[5])
                            )
                    except (ValueError, IndexError): pass
            i += 1
        if self.strains:
            self.latest_strains = self.strains.copy()
        return i

    def _skip_block(self, lines: List[str], start_idx: int) -> int:
        """跳过块"""
        i = start_idx + 1
        while i < len(lines):
            if lines[i].strip().startswith('-3'):
                i += 1
                break
            i += 1
        return i

    def _calc_max_displacement(
        self,
        displacements: Optional[Dict[int, Tuple[float, float, float]]] = None,
    ) -> Optional[float]:
        """计算最大位移"""
        target = self.displacements if displacements is None else displacements
        if not target:
            return None
        max_mag = 0.0
        for disp in target.values():
            mag = (disp[0]**2 + disp[1]**2 + disp[2]**2)**0.5
            if mag > max_mag:
                max_mag = mag
        return max_mag

    def _calc_max_von_mises(
        self,
        stresses: Optional[Dict[int, FRDStress]] = None,
    ) -> Optional[float]:
        """计算最大von Mises应力"""
        target = self.stresses if stresses is None else stresses
        if not target:
            return None

        try:
            import numpy as np
            max_vm = 0.0
            for stress in target.values():
                s = np.array([
                    [stress.S11 or 0, stress.S12 or 0, stress.S13 or 0],
                    [stress.S12 or 0, stress.S22 or 0, stress.S23 or 0],
                    [stress.S13 or 0, stress.S23 or 0, stress.S33 or 0]
                ])
                eigenvalues = np.linalg.eigvals(s)
                eigenvalues = sorted(eigenvalues, reverse=True)
                vm = np.sqrt(0.5 * (
                    (eigenvalues[0] - eigenvalues[1])**2 +
                    (eigenvalues[1] - eigenvalues[2])**2 +
                    (eigenvalues[2] - eigenvalues[0])**2
                ))
                if vm > max_vm:
                    max_vm = vm
                stress.von_mises = vm
            return max_vm
        except ImportError:
            return None

    def _calculate_maxima(self) -> None:
        """计算所有最大值"""
        self._calc_max_displacement()
        self._calc_max_von_mises()


def parse_frd(file_path: str) -> FRDParseResult:
    """解析.frd文件的便捷函数"""
    parser = FRDParser()
    return parser.parse(file_path)
