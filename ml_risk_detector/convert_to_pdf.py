#!/usr/bin/env python3
"""Convert PRESENTATION_SCRIPT.md to PDF using reportlab."""

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.lib import colors
except ImportError:
    print("ERROR: reportlab not installed. Run: pip install reportlab")
    exit(1)

# Read the markdown file
with open("PRESENTATION_SCRIPT.md", "r", encoding="utf-8") as f:
    content = f.read()

# Create PDF
pdf_path = "PRESENTATION_SCRIPT.pdf"
doc = SimpleDocTemplate(pdf_path, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)

# Container for PDF elements
elements = []

# Define styles
styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#1f4788'),
    spaceAfter=12,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

heading_style = ParagraphStyle(
    'CustomHeading',
    parent=styles['Heading2'],
    fontSize=14,
    textColor=colors.HexColor('#1f4788'),
    spaceAfter=6,
    spaceBefore=6,
    fontName='Helvetica-Bold'
)

body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['BodyText'],
    fontSize=11,
    alignment=TA_JUSTIFY,
    spaceAfter=8,
    leading=14
)

# Parse and add content
lines = content.split('\n')
i = 0

while i < len(lines):
    line = lines[i].strip()
    
    # Skip empty lines
    if not line:
        elements.append(Spacer(1, 0.1*inch))
        i += 1
        continue
    
    # Title
    if line.startswith('# ') and not line.startswith('## '):
        title = line.replace('# ', '').strip('*')
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 0.2*inch))
        i += 1
        continue
    
    # Section headings
    if line.startswith('## **'):
        heading = line.replace('## **', '').replace('**', '').strip()
        elements.append(Paragraph(heading, heading_style))
        i += 1
        continue
    
    # Regular text (quotes)
    if line.startswith('"'):
        text = line.strip('"\n')
        elements.append(Paragraph(text, body_style))
        elements.append(Spacer(1, 0.1*inch))
        i += 1
        continue
    
    # Code/preformatted blocks
    if line.startswith('```'):
        i += 1
        code_lines = []
        while i < len(lines) and not lines[i].strip().startswith('```'):
            code_lines.append(lines[i])
            i += 1
        i += 1  # skip closing ```
        
        code_text = '\n'.join(code_lines).strip()
        if code_text:
            elements.append(Paragraph(f"<font color='gray'><b>{code_text}</b></font>", body_style))
            elements.append(Spacer(1, 0.1*inch))
        continue
    
    # Bullet points
    if line.startswith('- '):
        bullet = line.replace('- ', '', 1).strip()
        elements.append(Paragraph(f"• {bullet}", body_style))
        i += 1
        continue
    
    # Regular paragraph
    if line and not line.startswith('#'):
        elements.append(Paragraph(line, body_style))
        i += 1
        continue
    
    i += 1

# Build PDF
doc.build(elements)
print(f"✓ PDF created successfully: {pdf_path}")
