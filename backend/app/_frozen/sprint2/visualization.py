"""PyVista可视化服务

提供有限元结果的可视化功能:
- 位移云图
- 应力云图
- 变形图
- 剖面图
"""
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import logging
import os
import numpy as np

logger = logging.getLogger(__name__)


class VisualizationService:
    """PyVista可视化服务"""

    def __init__(self):
        """初始化可视化服务"""
        self._check_pyvista()

    def _check_pyvista(self) -> None:
        """检查PyVista是否可用"""
        try:
            import pyvista
            self.pyvista = pyvista
            self._available = True
        except ImportError:
            logger.warning("PyVista未安装,可视化功能不可用")
            self._available = False
            self.pyvista = None

    @property
    def is_available(self) -> bool:
        """检查可视化是否可用"""
        return self._available

    def create_displacement_plot(
        self,
        nodes: Dict[int, Tuple[float, float, float]],
        displacements: Dict[int, Tuple[float, float, float]],
        title: str = "位移分布",
        output_path: Optional[str] = None,
        component: str = "magnitude"
    ) -> Optional[str]:
        """创建位移云图

        Args:
            nodes: 节点字典 {node_id: (x, y, z)}
            displacements: 位移字典 {node_id: (dx, dy, dz)}
            title: 图表标题
            output_path: 输出文件路径
            component: 位移分量 ('x', 'y', 'z', 'magnitude')

        Returns:
            生成的文件路径,失败返回None
        """
        if not self._available:
            logger.error("PyVista不可用")
            return None

        try:
            pv = self.pyvista

            # 创建点数据
            points = []
            values = []

            for node_id, coords in nodes.items():
                points.append(coords)
                if node_id in displacements:
                    disp = displacements[node_id]
                    if component == "magnitude":
                        val = (disp[0]**2 + disp[1]**2 + disp[2]**2)**0.5
                    elif component == "x":
                        val = abs(disp[0])
                    elif component == "y":
                        val = abs(disp[1])
                    elif component == "z":
                        val = abs(disp[2])
                    else:
                        val = (disp[0]**2 + disp[1]**2 + disp[2]**2)**0.5
                else:
                    val = 0.0
                values.append(val)

            # 创建点云
            point_cloud = pv.PointData()
            point_cloud["displacement"] = values

            # 使用Plotter
            plotter = pv.Plotter(off_screen=output_path is not None)
            plotter.add_points(points, scalars="displacement", cmap="jet")
            plotter.add_title(title)
            plotter.add_scalar_bar(title=f"{component}位移")

            if output_path:
                plotter.screenshot(output_path)
                plotter.close()
                return output_path
            else:
                # 返回base64编码的图像
                import base64
                from io import BytesIO

                plotter.show(auto_close=False)
                buffer = BytesIO()
                plotter.screenshot(buffer, return_img=False)
                plotter.close()

                return base64.b64encode(buffer.getvalue()).decode()

        except Exception as e:
            logger.error(f"创建位移云图失败: {e}")
            return None

    def create_stress_plot(
        self,
        nodes: Dict[int, Tuple[float, float, float]],
        stresses: Dict[int, Any],
        title: str = "应力分布",
        output_path: Optional[str] = None,
        stress_component: str = "von_mises"
    ) -> Optional[str]:
        """创建应力云图

        Args:
            nodes: 节点字典
            stresses: 应力字典 {node_id: FRDStress}
            title: 图表标题
            output_path: 输出文件路径
            stress_component: 应力分量 ('von_mises', 'max_principal', 'min_principal')

        Returns:
            生成的文件路径
        """
        if not self._available:
            logger.error("PyVista不可用")
            return None

        try:
            pv = self.pyvista

            # 提取节点坐标和应力值
            points = []
            values = []

            for node_id, coords in nodes.items():
                points.append(coords)
                if node_id in stresses:
                    stress = stresses[node_id]
                    if stress_component == "von_mises":
                        val = stress.von_mises or 0.0
                    elif stress_component == "max_principal":
                        val = stress.max_principal or 0.0
                    elif stress_component == "min_principal":
                        val = stress.min_principal or 0.0
                    else:
                        val = stress.von_mises or 0.0
                else:
                    val = 0.0
                values.append(val)

            # 创建可视化
            plotter = pv.Plotter(off_screen=output_path is not None)
            plotter.add_points(points, scalars=values, cmap="RdYlBu_r")
            plotter.add_title(title)
            plotter.add_scalar_bar(title=f"{stress_component}应力(Pa)")

            if output_path:
                plotter.screenshot(output_path)
                plotter.close()
                return output_path
            else:
                return None

        except Exception as e:
            logger.error(f"创建应力云图失败: {e}")
            return None

    def create_deformed_shape(
        self,
        nodes: Dict[int, Tuple[float, float, float]],
        displacements: Dict[int, Tuple[float, float, float]],
        elements: Dict[int, List[int]],
        deformation_scale: float = 1.0,
        title: str = "变形图",
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """创建变形形状图

        Args:
            nodes: 原始节点坐标
            displacements: 节点位移
            elements: 单元连接
            deformation_scale: 变形放大系数
            title: 图表标题
            output_path: 输出文件路径

        Returns:
            生成的文件路径
        """
        if not self._available:
            logger.error("PyVista不可用")
            return None

        try:
            pv = self.pyvista

            # 计算变形后的坐标
            deformed_points = {}
            for node_id, coords in nodes.items():
                if node_id in displacements:
                    disp = displacements[node_id]
                    deformed_points[node_id] = (
                        coords[0] + disp[0] * deformation_scale,
                        coords[1] + disp[1] * deformation_scale,
                        coords[2] + disp[2] * deformation_scale
                    )
                else:
                    deformed_points[node_id] = coords

            # 创建原始和变形后的网格
            original_grid = pv.StructuredGrid(
                *zip(*[nodes.get(i, (0, 0, 0)) for i in range(len(nodes))])
            )

            deformed_grid = pv.StructuredGrid(
                *zip(*[deformed_points.get(i, (0, 0, 0)) for i in range(len(nodes))])
            )

            # 可视化
            plotter = pv.Plotter(off_screen=output_path is not None)

            # 原始形状(半透明)
            if elements:
                # 使用单元创建网格
                cells = []
                cell_types = []
                for elem_id, elem_nodes in elements.items():
                    cells.extend([len(elem_nodes)] + elem_nodes)
                    cell_types.append(pv.CELL_TYPE.HEXAHEDRON if len(elem_nodes) == 8 else pv.CELL_TYPE.TETRA)

                grid = pv.UnstructuredGrid(cells, cell_types, list(nodes.values()))
                plotter.add_mesh(grid, style="wireframe", color="gray", opacity=0.3)

            # 变形后形状
            if elements:
                deformed_cells = []
                for elem_id, elem_nodes in elements.items():
                    deformed_cells.extend([len(elem_nodes)] + elem_nodes)

                deformed_grid = pv.UnstructuredGrid(
                    deformed_cells, cell_types, list(deformed_points.values())
                )
                plotter.add_mesh(deformed_grid, cmap="viridis")

            plotter.add_title(title)

            if output_path:
                plotter.screenshot(output_path)
                plotter.close()
                return output_path
            else:
                return None

        except Exception as e:
            logger.error(f"创建变形图失败: {e}")
            return None

    def create_contour_plot(
        self,
        grid_data: Dict[Tuple[int, int], float],
        title: str = "等值线图",
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """创建等值线图

        Args:
            grid_data: 2D网格数据 {(i, j): value}
            title: 图表标题
            output_path: 输出文件路径

        Returns:
            生成的文件路径
        """
        if not self._available:
            logger.error("PyVista不可用")
            return None

        try:
            pv = self.pyvista

            # 提取网格坐标和值
            x_coords = sorted(set(k[0] for k in grid_data.keys()))
            y_coords = sorted(set(k[1] for k in grid_data.keys()))

            values = []
            for y in y_coords:
                row = []
                for x in x_coords:
                    row.append(grid_data.get((x, y), 0.0))
                values.append(row)

            # 创建2D网格
            grid = pv.StructuredGrid()
            grid.points = [(x, y, 0) for y in y_coords for x in x_coords]
            grid.dimensions = (len(x_coords), len(y_coords), 1)

            plotter = pv.Plotter(off_screen=output_path is not None)
            plotter.add_mesh(grid, scalars="values", contours=True)
            plotter.add_title(title)

            if output_path:
                plotter.screenshot(output_path)
                plotter.close()
                return output_path
            else:
                return None

        except Exception as e:
            logger.error(f"创建等值线图失败: {e}")
            return None

    def create_unstructured_grid(self, parse_result: Any) -> Optional['pyvista.UnstructuredGrid']:
        """
        Converts the FRD parsed structures into a PyVista UnstructuredGrid.
        """
        if not self._available or not parse_result.success or not parse_result.nodes or not parse_result.elements:
            return None

        pv = self.pyvista
        import vtk

        node_ids = sorted(list(parse_result.nodes.keys()))
        node_id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
        
        points = np.zeros((len(node_ids), 3))
        for nid, idx in node_id_to_idx.items():
            points[idx] = parse_result.nodes[nid].coords

        cells = []
        cell_types = []
        for elem in parse_result.elements.values():
            if elem.element_type == "C3D8" and len(elem.nodes) == 8:
                cells.append(8)
                cells.extend([node_id_to_idx.get(n, 0) for n in elem.nodes])
                cell_types.append(vtk.VTK_HEXAHEDRON)

        if not cells:
            return None

        grid = pv.UnstructuredGrid(cells, cell_types, points)

        if parse_result.displacements:
            disp_data = np.zeros((len(node_ids), 3))
            for nid, disp in parse_result.displacements.items():
                if nid in node_id_to_idx:
                    disp_data[node_id_to_idx[nid]] = disp
            grid.point_data["Displacement"] = disp_data

        if parse_result.stresses:
            vm_data = np.zeros(len(node_ids))
            for nid, stress in parse_result.stresses.items():
                if nid in node_id_to_idx and stress.von_mises is not None:
                    vm_data[node_id_to_idx[nid]] = stress.von_mises
            grid.point_data["VonMises"] = vm_data

        return grid

    def export_scene_as_html(self, parse_result: Any, field: str = "VonMises") -> Optional[str]:
        """
        Generate a standalone HTML scene.
        """
        if not self._available:
            return None

        pv = self.pyvista
        grid = self.create_unstructured_grid(parse_result)
        if grid is None:
            return None

        if "Displacement" in grid.point_data:
            grid = grid.warp_by_vector("Displacement", factor=1.0)

        plotter = pv.Plotter(off_screen=True)
        if field in grid.point_data:
            plotter.add_mesh(grid, scalars=field, cmap="jet", show_edges=True)
        else:
            plotter.add_mesh(grid, show_edges=True)

        temp_html_path = "/tmp/temp_mesh_export.html"
        plotter.export_html(temp_html_path)
        plotter.close()

        with open(temp_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
            
        return html_content


# 全局实例
_viz_service: Optional[VisualizationService] = None


def get_visualization_service() -> VisualizationService:
    """获取可视化服务单例"""
    global _viz_service
    if _viz_service is None:
        _viz_service = VisualizationService()
    return _viz_service