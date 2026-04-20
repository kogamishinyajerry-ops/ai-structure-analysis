"""VTP (VTK PolyData) exporter for ParaView visualization.

Converts parsed FRD nodal/elemental data into VTP files
that can be opened in ParaView for interactive 3-D exploration.

This module is a stub (AI-FEA-P0-01).  Logic will be filled in P0-09.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def export_vtp(results: dict[str, Any], output_dir: Path) -> Path:
    """Export FEA results as a VTP file.

    Parameters
    ----------
    results : dict
        Parsed FRD data (nodes, elements, fields).
    output_dir : Path
        Directory to write the VTP file into.

    Returns
    -------
    Path
        Path to the generated ``.vtp`` file.
    """
    nodes = results.get("nodes", {})
    fields = results.get("fields", [])

    if not nodes:
        logger.warning("No nodes found, VTP exporter returning None.")
        return Path("")

    output_dir.mkdir(parents=True, exist_ok=True)
    vtp_path = output_dir / "results.vtp"

    num_points = len(nodes)
    node_ids = sorted(nodes.keys())
    
    # 1. Build Points array
    points_buffer = []
    for nid in node_ids:
        c = nodes[nid]
        points_buffer.append(f"{float(c[0]):.6g} {float(c[1]):.6g} {float(c[2]):.6g}")
    points_data = " ".join(points_buffer)

    # 2. Build Vertex topology (so points are rendered as Glyphs inherently in some modes)
    connectivity_data = " ".join(str(i) for i in range(num_points))
    offsets_data = " ".join(str(i + 1) for i in range(num_points))

    # 3. Build PointData arrays
    point_data_xml = []
    for field in fields:
        name = field["name"]
        comp_names = field["component_names"]
        num_comp = len(comp_names) if comp_names else 1
        
        # We need to map standard displacement/stress to 3 or 6 components if possible
        if name == "displacement" and num_comp > 3:
            num_comp = 3
        elif name == "stress" and num_comp > 6:
            num_comp = 6 # standard symmetrical tensor (Sxx, Syy, Szz, Sxy, Syz, Szx)
        
        field_buffer = []
        values = field["values"]
        
        for nid in node_ids:
            arr = values.get(nid)
            if arr is not None:
                # pad or truncate array to match num_comp
                vals = [float(v) for v in arr]
                if len(vals) < num_comp:
                    vals = vals + [0.0] * (num_comp - len(vals))
                elif len(vals) > num_comp:
                    vals = vals[:num_comp]
                
                field_buffer.append(" ".join(f"{v:.6g}" for v in vals))
            else:
                field_buffer.append(" ".join(["0"] * num_comp))
                
        pdata_str = " ".join(field_buffer)
        
        da_xml = f"""
        <DataArray type="Float32" Name="{name}" NumberOfComponents="{num_comp}" format="ascii">
          {pdata_str}
        </DataArray>"""
        point_data_xml.append(da_xml)

    pd_blocks = "".join(point_data_xml)

    # Assemble XML
    xml = f"""<?xml version="1.0"?>
<VTKFile type="PolyData" version="0.1" byte_order="LittleEndian">
  <PolyData>
    <Piece NumberOfPoints="{num_points}" NumberOfVerts="{num_points}" NumberOfLines="0" NumberOfStrips="0" NumberOfPolys="0">
      <Points>
        <DataArray type="Float32" Name="Points" NumberOfComponents="3" format="ascii">
          {points_data}
        </DataArray>
      </Points>
      <Verts>
        <DataArray type="Int32" Name="connectivity" format="ascii">
          {connectivity_data}
        </DataArray>
        <DataArray type="Int32" Name="offsets" format="ascii">
          {offsets_data}
        </DataArray>
      </Verts>
      <PointData>
          {pd_blocks}
      </PointData>
    </Piece>
  </PolyData>
</VTKFile>"""

    vtp_path.write_text(xml, encoding="utf-8")
    import logging
    logger = logging.getLogger(__name__)
    logger.info("VTP exported to %s", vtp_path)
    return vtp_path
