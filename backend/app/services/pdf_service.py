import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

class PDFService:
    """专业工程报告 PDF 生成服务"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """配置专业美观的 PDF 样式"""
        self.title_style = ParagraphStyle(
            'ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor("#3F51B5"), # Indigo 500
            spaceAfter=30,
            alignment=1 # Center
        )
        self.section_style = ParagraphStyle(
            'SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor("#303F9F"), # Indigo 700
            spaceBefore=20,
            spaceAfter=12,
            borderPadding=5,
            borderWidth=1,
            borderColor=colors.HexColor("#303F9F"),
            borderRadius=3
        )
        self.label_style = ParagraphStyle(
            'Label',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=2
        )
        self.value_style = ParagraphStyle(
            'Value',
            parent=self.styles['Normal'],
            fontSize=12,
            fontWeight='BOLD',
            spaceAfter=10
        )

    def generate_report_pdf(self, report_data: Dict[str, Any]) -> io.BytesIO:
        """从报表数据生成 PDF 二进制流"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=inch/2, leftMargin=inch/2, topMargin=inch/2, bottomMargin=inch/2)
        
        elements = []
        
        # 1. 封面与标题
        elements.append(Spacer(1, 1*inch))
        elements.append(Paragraph("STRUCTURE AI - 工程仿真报告", self.title_style))
        elements.append(Spacer(1, 0.5*inch))
        
        # 2. 项目概况
        elements.append(Paragraph("项目概况", self.section_style))
        
        meta_data = [
            ["案例标识:", report_data.get("case_id", "N/A")],
            ["分析类型:", report_data.get("metrics", {}).get("type", "线性静力分析")],
            ["生成时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["安全状态:", report_data.get("metrics", {}).get("status", "UNKNOWN")]
        ]
        
        t = Table(meta_data, colWidths=[1.5*inch, 4*inch])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 12),
            ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor("#3F51B5")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        elements.append(t)
        
        elements.append(Spacer(1, 0.5*inch))
        
        # 3. 核心计算指标
        elements.append(Paragraph("核心计算指标摘要", self.section_style))
        
        metrics = report_data.get("metrics", {})
        metrics_data = [
            ["指标名称", "数值", "判定"],
            ["最大位移", f"{metrics.get('max_displacement', 0):.4f}", "-"],
            ["最大等效应力 (MPa)", f"{metrics.get('max_von_mises', 0):.2f}", "-"],
            ["估算下限安全系数", f"{metrics.get('safety_factor', 0)}", metrics.get('status', 'N/A')]
        ]
        
        mt = Table(metrics_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        mt.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E8EAF6")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#303F9F")),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        elements.append(mt)
        
        # 4. 如果有模态分析
        if "increments" in report_data and report_data["increments"]:
            elements.append(PageBreak())
            elements.append(Paragraph("动力学与稳定性分析结果", self.section_style))
            
            inc_data = [["阶数", "类型", "频率/因子", "最大位移"]]
            for inc in report_data["increments"]:
                inc_data.append([
                    str(inc.get("index")),
                    inc.get("type", "N/A"),
                    f"{inc.get('value', 0):.3f}",
                    f"{inc.get('max_displacement', 0):.4f}"
                ])
                
            it = Table(inc_data, colWidths=[0.8*inch, 1.5*inch, 1.7*inch, 1.5*inch])
            it.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F3F4F6")),
                ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ]))
            elements.append(it)
            
        # 5. 免责声明与页脚
        elements.append(Spacer(1, 1*inch))
        elements.append(Paragraph("注意: 本报告由 AI-Structure Workbench 自动生成。FEA 仿真结果受网格质量、单元类型及边界条件简化的影响。关键工程决策需配合物理试验验证。", 
                                 ParagraphStyle('Disclaimer', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.grey)))

        doc.build(elements)
        buffer.seek(0)
        return buffer

# 单例
_pdf_service = None

def get_pdf_service():
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service
