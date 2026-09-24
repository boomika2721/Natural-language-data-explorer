import os
import io
import datetime
import pandas as pd
from typing import Dict, Any, List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from config import REPORTS_DIR

def export_to_csv(df: pd.DataFrame) -> bytes:
    """
    Exports a DataFrame into standard UTF-8 CSV bytes with BOM for Excel compatibility.
    """
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, encoding='utf-8')
    return buffer.getvalue().encode('utf-8-sig')

def export_to_excel(df: pd.DataFrame, report_title: str = "Query Results") -> bytes:
    """
    Generates a beautifully styled Excel workbook using OpenPyXL.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "NLDE Results"
    
    # Enable grid lines
    ws.views.sheetView[0].showGridLines = True
    
    # Title Banner
    ws.merge_cells("A1:H1")
    title_cell = ws["A1"]
    title_cell.value = f"Natural-Language Data Explorer (NLDE) - {report_title}"
    title_cell.font = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36
    
    # Subtitle with Timestamp
    ws.merge_cells("A2:H2")
    sub_cell = ws["A2"]
    sub_cell.value = f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total Records: {len(df)}"
    sub_cell.font = Font(name="Segoe UI", size=9, italic=True, color="64748B")
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20
    
    # Blank row 3
    ws.row_dimensions[3].height = 10
    
    # Table Header Row (Row 4)
    headers = list(df.columns)
    header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
    header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    header_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='medium', color='1E293B'),
        bottom=Side(style='medium', color='1E293B')
    )
    
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=col_idx, value=header.replace('_', ' ').title())
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = header_border
        
    ws.row_dimensions[4].height = 25
    
    # Data Rows
    row_alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    cell_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )
    
    for r_idx, row in enumerate(df.itertuples(index=False), start=5):
        ws.row_dimensions[r_idx].height = 20
        is_even = (r_idx % 2 == 0)
        for c_idx, val in enumerate(row, start=1):
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.font = Font(name="Segoe UI", size=9.5)
            cell.border = cell_border
            if is_even:
                cell.fill = row_alt_fill
            # Align numbers right, text left
            if isinstance(val, (int, float)):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
    # Auto-fit Column Widths with padding
    for col in ws.columns:
        max_len = 0
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        for cell in col:
            # Skip merged banner row in width calculation
            if cell.row in (1, 2, 3):
                continue
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

def generate_pdf_report(
    user_query: str,
    sql_query: str,
    explanation: str,
    confidence_score: int,
    language: str,
    insights: List[str],
    df: pd.DataFrame
) -> bytes:
    """
    Generates a PDF report using ReportLab with:
    - User Question
    - SQL Query
    - Query Explanation
    - Confidence Score
    - Date & Time
    - AI Insights
    - Result Data Table
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=12
    )
    
    section_h2 = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=10,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    
    sql_code_style = ParagraphStyle(
        'SQLCode',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )
    
    insight_bullet = ParagraphStyle(
        'InsightBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1e3a8a')
    )
    
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1e293b')
    )
    
    table_cell_header = ParagraphStyle(
        'TableCellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )
    
    elements = []
    
    # Header Banner
    elements.append(Paragraph("Natural-Language Data Explorer (NLDE)", title_style))
    now_str = datetime.datetime.now().strftime("%B %d, %Y - %I:%M %p")
    elements.append(Paragraph(f"Executive Query & Analytics Report | Generated: {now_str}", meta_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3b82f6'), spaceAfter=14))
    
    # Query Verification Block
    verif_data = [
        [
            Paragraph("<b>User Question:</b>", body_style),
            Paragraph(f"<b>{user_query}</b>", body_style)
        ],
        [
            Paragraph("<b>Detected Language:</b>", body_style),
            Paragraph(f"{language} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Confidence Score:</b> {confidence_score}%", body_style)
        ],
        [
            Paragraph("<b>Generated SQL:</b>", body_style),
            Paragraph(f"<code>{sql_query}</code>", sql_code_style)
        ],
        [
            Paragraph("<b>Query Explanation:</b>", body_style),
            Paragraph(explanation, body_style)
        ]
    ]
    
    verif_table = Table(verif_data, colWidths=[1.8 * inch, 5.5 * inch])
    verif_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(verif_table)
    elements.append(Spacer(1, 12))
    
    # AI Insights Callout Box
    if insights:
        elements.append(Paragraph("AI-Powered Analytical Insights", section_h2))
        insights_data = []
        for ins in insights:
            insights_data.append([
                Paragraph("•", insight_bullet),
                Paragraph(ins, insight_bullet)
            ])
            
        ins_table = Table(insights_data, colWidths=[0.3 * inch, 7.0 * inch])
        ins_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eff6ff')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#93c5fd')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(ins_table)
        elements.append(Spacer(1, 14))
        
    # Result Data Table
    elements.append(Paragraph(f"Query Result Records ({len(df)} total records)", section_h2))
    
    if df.empty:
        elements.append(Paragraph("No records found matching the query criteria.", body_style))
    else:
        # Limit rows in PDF preview to 50 for clean rendering, noting if truncated
        display_df = df.head(50)
        
        headers = [Paragraph(f"<b>{col.replace('_', ' ').title()}</b>", table_cell_header) for col in display_df.columns]
        table_rows = [headers]
        
        for _, row in display_df.iterrows():
            row_cells = []
            for col_val in row:
                text_val = str(col_val)
                row_cells.append(Paragraph(text_val, table_cell))
            table_rows.append(row_cells)
            
        # Calculate dynamic column widths
        num_cols = len(display_df.columns)
        avail_width = 7.3 * inch
        col_width = avail_width / num_cols
        
        res_table = Table(table_rows, colWidths=[col_width] * num_cols)
        res_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(res_table)
        
        if len(df) > 50:
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"<i>* Note: Displaying top 50 rows of {len(df)} total matching records. Full dataset available via Excel or CSV export.</i>", meta_style))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

if __name__ == '__main__':
    # Self-test report generation
    test_df = pd.DataFrame([
        {"id": 1, "name": "Karthik Raj", "department": "IT", "year": 3, "cgpa": 9.72, "city": "Erode", "gender": "Male"},
        {"id": 2, "name": "Divya Bharathi", "department": "CSE", "year": 4, "cgpa": 9.85, "city": "Chennai", "gender": "Female"}
    ])
    
    pdf_bytes = generate_pdf_report(
        user_query="Show students from Erode",
        sql_query="SELECT * FROM students WHERE city = 'Erode';",
        explanation="This query retrieves all students whose city is Erode.",
        confidence_score=98,
        language="English",
        insights=["Average CGPA is 8.2", "IT Department has maximum students"],
        df=test_df
    )
    print(f"Generated PDF report: {len(pdf_bytes)} bytes")
    
    excel_bytes = export_to_excel(test_df)
    print(f"Generated Excel workbook: {len(excel_bytes)} bytes")
    
    csv_bytes = export_to_csv(test_df)
    print(f"Generated CSV content: {len(csv_bytes)} bytes")
