"""HTML Dashboard Generator for AIEvolver Scientific Reports.

Produces a premium, dark-mode interactive report with SVG visualizations
of the FEA results.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIEvolver Research Report - {case_id}</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --primary: #38bdf8;
            --success: #22c55e;
            --warning: #f59e0b;
            --error: #ef4444;
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
            --border: #334155;
        }}

        body {{
            background: var(--bg);
            color: var(--text-main);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 2rem;
            line-height: 1.5;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 2rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 3rem;
        }}

        .logo {{
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: -0.05rem;
            color: var(--primary);
        }}

        .status-badge {{
            padding: 0.5rem 1rem;
            border-radius: 2rem;
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .status-accept {{ background: rgba(34, 197, 94, 0.2); color: var(--success); border: 1px solid var(--success); }}
        .status-review {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }}
        .status-fail {{ background: rgba(239, 68, 68, 0.2); color: var(--error); border: 1px solid var(--error); }}

        .grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }}

        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}

        .card-title {{
            font-size: 0.875rem;
            font-weight: 700;
            color: var(--text-dim);
            text-transform: uppercase;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .metric-value {{
            font-size: 2.5rem;
            font-weight: 800;
            margin: 0.5rem 0;
        }}

        .metric-label {{
            font-size: 0.875rem;
            color: var(--text-dim);
        }}

        .viz-container {{
            background: #020617;
            border-radius: 0.75rem;
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 1rem;
            border: 1px solid var(--border);
            position: relative;
            overflow: hidden;
        }}

        .viz-legend {{
            position: absolute;
            bottom: 1rem;
            right: 1rem;
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(4px);
            padding: 0.5rem;
            border-radius: 0.5rem;
            font-size: 0.75rem;
            border: 1px solid var(--border);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}

        th {{
            text-align: left;
            font-size: 0.75rem;
            color: var(--text-dim);
            padding: 0.75rem;
            border-bottom: 1px solid var(--border);
        }}

        td {{
            padding: 0.75rem;
            font-size: 0.875rem;
            border-bottom: 1px solid rgba(51, 65, 85, 0.5);
        }}

        .delta-bar {{
            height: 8px;
            background: var(--border);
            border-radius: 4px;
            overflow: hidden;
            width: 100px;
        }}

        .delta-fill {{
            height: 100%;
            background: var(--primary);
        }}

        footer {{
            margin-top: 4rem;
            text-align: center;
            font-size: 0.75rem;
            color: var(--text-dim);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <div class="logo">AIEVOLVER RESEARCH</div>
                <div style="font-size: 0.875rem; color: var(--text-dim); margin-top: 0.25rem;">Automated Structural Analysis Report</div>
            </div>
            <div class="status-badge status-{verdict_class}">{verdict}</div>
        </header>

        <div class="grid">
            <div class="card">
                <div class="card-title">RESULT VISUALIZATION (SCHEMATIC)</div>
                <div class="viz-container">
                    <svg viewBox="0 0 400 200" width="100%" height="80%">
                        <!-- Fixed Boundary -->
                        <line x1="50" y1="50" x2="50" y2="150" stroke="#94a3b8" stroke-width="4" stroke-dasharray="2,2"/>
                        
                        <!-- Undeformed beam shape -->
                        <rect x="50" y="90" width="300" height="20" fill="transparent" stroke="#334155" stroke-width="1" stroke-dasharray="4,4"/>
                        
                        <!-- Deformed beam (Beziér curve) -->
                        <path d="M 50 100 C 150 100, 250 100, 350 140" fill="none" stroke="url(#stressGradient)" stroke-width="12" stroke-linecap="round"/>
                        
                        <!-- Load arrow -->
                        <path d="M 350 110 L 350 160 M 345 150 L 350 160 L 355 150" fill="none" stroke="#ef4444" stroke-width="2"/>
                        
                        <defs>
                            <linearGradient id="stressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" style="stop-color:#38bdf8;stop-opacity:1" />
                                <stop offset="100%" style="stop-color:#ef4444;stop-opacity:1" />
                            </linearGradient>
                        </defs>
                    </svg>
                    <div class="viz-legend">
                        <div style="display: flex; align-items:center; gap: 0.5rem; margin-bottom: 0.25rem;">
                            <div style="width: 10px; height: 10px; background: #38bdf8; border-radius: 2px;"></div>
                            <span>Min Stress</span>
                        </div>
                        <div style="display: flex; align-items:center; gap: 0.5rem;">
                            <div style="width: 10px; height: 10px; background: #ef4444; border-radius: 2px;"></div>
                            <span>Max Stress</span>
                        </div>
                    </div>
                </div>
                <p style="font-size: 0.875rem; color: var(--text-dim); margin-top: 1rem;">
                    {description}
                </p>
            </div>

            <div class="card">
                <div class="card-title">EXECUTION METRICS</div>
                <div>
                    <div class="metric-label">Max Von-Mises</div>
                    <div class="metric-value" style="color: var(--primary);">{max_stress} <span style="font-size: 1rem;">MPa</span></div>
                </div>
                <hr style="border: 0; border-top: 1px solid var(--border); margin: 1.5rem 0;">
                <div>
                    <div class="metric-label">Max Displacement</div>
                    <div class="metric-value">{max_disp} <span style="font-size: 1rem;">mm</span></div>
                </div>
                {solver_info}
            </div>
        </div>

        <div class="card" style="margin-bottom: 2rem;">
            <div class="card-title">REFERENCE VALIDATION</div>
            <table>
                <thead>
                    <tr>
                        <th>QUANTITY</th>
                        <th>REFERENCE</th>
                        <th>COMPUTED</th>
                        <th>DISCREPANCY (%)</th>
                        <th>STATUS</th>
                    </tr>
                </thead>
                <tbody>
                    {comparison_rows}
                </tbody>
            </table>
        </div>

        {mesh_quality_section}

        <footer>
            Report ID: {case_id} &middot; Generated by AIEvolver Engine &middot; {timestamp}
        </footer>
    </div>
</body>
</html>
"""

def generate_dashboard(results: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "dashboard.html"

    case_id = results.get("case_id", "UNKNOWN")
    description = results.get("description", "No description provided.")
    verdict = results.get("verdict", "review")
    fields = results.get("fields", [])
    refs = results.get("reference_values", {})
    mesh_q = results.get("mesh_quality")
    wall_time = results.get("wall_time_s")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Map verdict classes
    verdict_map = {"pass": "accept", "fail": "fail", "review": "review"}
    v_class = verdict_map.get(verdict, "review")

    # Extract metrics
    max_stress = "N/A"
    max_disp = "N/A"
    for f in fields:
        fname = f.get("field", "").lower()
        if "stress" in fname or "von_mises" in fname:
            v = f.get("max_magnitude")
            if v is not None: max_stress = f"{v:.2f}"
        if "displacement" in fname or "u" == fname:
            v = f.get("max_magnitude")
            if v is not None: max_disp = f"{v:.4f}"

    # Solver info
    solver_info = ""
    if wall_time:
        solver_info = f'<div style="margin-top: 1.5rem;"><div class="metric-label">Solve Time</div><div style="font-size: 1.25rem; font-weight: 700;">{wall_time:.1f} s</div></div>'

    # Comparison rows
    comparison_rows = ""
    if refs:
        for key, ref_val in refs.items():
            computed = None
            for f in fields:
                if f.get("field") == key:
                    computed = f.get("max_magnitude")
                    break
            
            error_pct = 0.0
            status_dot = "var(--success)"
            if computed is not None and ref_val != 0:
                error_pct = abs(computed - ref_val) / abs(ref_val) * 100
                if error_pct > 10: status_dot = "var(--error)"
                elif error_pct > 5: status_dot = "var(--warning)"
                
                c_val_str = f"{computed:.4f}"
                pct_str = f"{error_pct:.1f}%"
            else:
                c_val_str = "N/A"
                pct_str = "—"
                status_dot = "var(--border)"

            comparison_rows += f"""
                <tr>
                    <td style="font-weight: 700;">{key}</td>
                    <td>{ref_val:.4f}</td>
                    <td>{c_val_str}</td>
                    <td>
                        <div style="display: flex; align-items:center; gap: 0.5rem;">
                            <div class="delta-bar"><div class="delta-fill" style="width: {min(error_pct, 100)}%; background: {status_dot};"></div></div>
                            <span>{pct_str}</span>
                        </div>
                    </td>
                    <td><div style="width: 8px; height: 8px; border-radius: 50%; background: {status_dot};"></div></td>
                </tr>
            """
    else:
        comparison_rows = '<tr><td colspan="5" style="text-align: center; color: var(--text-dim);">No reference data provided</td></tr>'

    # Mesh quality section
    mesh_quality_section = ""
    if mesh_q:
        mj = mesh_q.get("min_jacobian", "N/A")
        ma = mesh_q.get("max_aspect_ratio", "N/A")
        mj_status = "var(--success)" if isinstance(mj, (int, float)) and mj >= 0.2 else "var(--error)"
        ma_status = "var(--success)" if isinstance(ma, (int, float)) and ma <= 10 else "var(--error)"

        mesh_quality_section = f"""
        <div class="card">
            <div class="card-title">MESH GEOMETRY HEALTH</div>
            <div style="display: flex; gap: 3rem; margin-top: 1rem;">
                <div>
                    <div class="metric-label">Min Jacobian</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: {mj_status}">{mj}</div>
                </div>
                <div>
                    <div class="metric-label">Max Aspect Ratio</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: {ma_status}">{ma}</div>
                </div>
            </div>
        </div>
        """

    # Render template
    html = HTML_TEMPLATE.format(
        case_id=case_id,
        description=description,
        verdict=verdict.upper(),
        verdict_class=v_class,
        max_stress=max_stress,
        max_disp=max_disp,
        solver_info=solver_info,
        comparison_rows=comparison_rows,
        mesh_quality_section=mesh_quality_section,
        timestamp=timestamp
    )

    report_path.write_text(html, encoding="utf-8")
    logger.info("HTML Dashboard written → %s", report_path)
    return report_path
