from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle, StyleSheet1
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import os
from datetime import datetime
import re
from io import BytesIO

def create_pdf(sop_id: str, topic: str, details: str, company_name="Your Company") -> str:
    pdf_directory = "pdfs"
    os.makedirs(pdf_directory, exist_ok=True)
    
    pdf_path = os.path.join(pdf_directory, f"{sop_id}.pdf")

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch
    )

    styles = _create_custom_stylesheet()
    
    doc._company_name = company_name
    doc._sop_id = sop_id
    doc._topic = topic

    story = _build_document_story(topic, sop_id, details, styles, company_name)

    try:
        doc.build(story, 
                 onFirstPage=_add_first_page_header_footer, 
                 onLaterPages=_add_later_pages_header_footer)
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return ""

    return pdf_path

def _create_custom_stylesheet() -> StyleSheet1:
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        'SOPTitle',
        parent=styles['Heading1'],
        fontSize=18,
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        spaceAfter=12,
        spaceBefore=6
    ))
    
    styles.add(ParagraphStyle(
        'SOPDocID',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica',
        textColor=colors.darkgrey,
        alignment=TA_CENTER,
        spaceAfter=20
    ))

    styles.add(ParagraphStyle(
        'SOPHeading',
        parent=styles['Heading2'],
        fontSize=13,
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
        borderWidth=0,
        borderRadius=0,
        borderPadding=0,
        borderColor=colors.darkblue
    ))

    styles.add(ParagraphStyle(
        'SOPNormal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceBefore=4,
        spaceAfter=4,
        leading=14
    ))
    
    styles.add(ParagraphStyle(
        'MarkdownH1',
        parent=styles['Heading1'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
        borderWidth=0,
        borderPadding=0,
        leftIndent=0
    ))
    
    styles.add(ParagraphStyle(
        'MarkdownH2',
        parent=styles['Heading2'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
        leftIndent=5
    ))
    
    styles.add(ParagraphStyle(
        'MarkdownH3',
        parent=styles['Heading3'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
        leftIndent=10
    ))
    
    # Add styles for heading levels 4 and 5
    styles.add(ParagraphStyle(
        'MarkdownH4',
        parent=styles['Heading3'],
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True,
        leftIndent=15
    ))

    styles.add(ParagraphStyle(
        'MarkdownH5',
        parent=styles['Heading3'],
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        spaceBefore=4,
        spaceAfter=2,
        keepWithNext=True,
        leftIndent=20
    ))
    
    # Primary level numbered list (1., 2., 3., etc.) - Adjusted with more spacing
    styles.add(ParagraphStyle(
        'NumberedLevel1',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',  # Bold for level 1
        leftIndent=20,              # Increased indent
        firstLineIndent=-20,        # Adjusted for proper hanging indent
        spaceBefore=18,              # Increased spacing
        spaceAfter=6,
        leading=14
    ))
    
    # Secondary level numbered list (1.1., 1.2., etc.) - Adjusted with more spacing and indent
    styles.add(ParagraphStyle(
        'NumberedLevel2',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=50,              # Increased indent for level 2
        firstLineIndent=-30,        # Adjusted for proper hanging indent
        spaceBefore=6,
        spaceAfter=4,
        leading=14
    ))
    
    # Third level numbered list (1.1.1., 1.1.2., etc.) - Adjusted with more spacing and indent
    styles.add(ParagraphStyle(
        'NumberedLevel3',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=80,              # Increased indent for level 3
        firstLineIndent=-40,        # Adjusted for proper hanging indent
        spaceBefore=4,
        spaceAfter=4,
        leading=14
    ))
    
    styles.add(ParagraphStyle(
        'BulletPoint',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=25,
        firstLineIndent=-15,
        spaceBefore=2,
        spaceAfter=2,
        leading=14
    ))
    
    styles.add(ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        textColor=colors.white
    ))
    
    styles.add(ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT
    ))

    return styles

def _format_markdown_content(content: str, styles) -> list:
    """Format markdown content into proper ReportLab elements with multi-level numbering"""
    story = []
    
    # Split the content by lines
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Handle headings with multiple hash symbols (###, ####, #####)
        hash_match = re.match(r'^(#{1,5})\s+(.*?)$', line)
        if hash_match:
            # Count the number of hash symbols to determine heading level
            num_hashes = len(hash_match.group(1))
            heading_text = hash_match.group(2).strip()
            
            # Choose style based on heading level
            if num_hashes == 1:
                story.append(Paragraph(heading_text, styles['MarkdownH1']))
            elif num_hashes == 2:
                story.append(Paragraph(heading_text, styles['MarkdownH2']))
            elif num_hashes == 3:
                story.append(Paragraph(heading_text, styles['MarkdownH3']))
            elif num_hashes == 4:
                story.append(Paragraph(heading_text, styles['MarkdownH4']))
            elif num_hashes == 5:
                story.append(Paragraph(heading_text, styles['MarkdownH5']))
        # Handle numbered lists with up to 3 levels (e.g., 1., 1.1., 1.1.1.)
        elif re.match(r'^\d+\.\s', line):  # Main level (1., 2., etc.)
            # Extract number and text
            match = re.match(r'^(\d+)\.(.*)$', line)
            if match:
                number = match.group(1)
                list_text = match.group(2).strip()
                
                # Process bold text within list items
                list_text = _process_bold_text(list_text)
                
                # Create a primary level numbered list item with proper tab spacing
                story.append(Paragraph(f"{number}. {list_text}", styles['NumberedLevel1']))
        elif re.match(r'^\d+\.\d+\.\s', line):  # Second level (1.1., 1.2., etc.)
            # Extract number and text
            match = re.match(r'^(\d+\.\d+)\.(.*)$', line)
            if match:
                number = match.group(1)
                list_text = match.group(2).strip()
                
                # Process bold text within list items
                list_text = _process_bold_text(list_text)
                
                # Create a secondary level numbered list item with proper tab spacing
                story.append(Paragraph(f"{number}. {list_text}", styles['NumberedLevel2']))
        elif re.match(r'^\d+\.\d+\.\d+\.\s', line):  # Third level (1.1.1., 1.1.2., etc.)
            # Extract number and text
            match = re.match(r'^(\d+\.\d+\.\d+)\.(.*)$', line)
            if match:
                number = match.group(1)
                list_text = match.group(2).strip()
                
                # Process bold text within list items
                list_text = _process_bold_text(list_text)
                
                # Create a tertiary level numbered list item with proper tab spacing
                story.append(Paragraph(f"{number}. {list_text}", styles['NumberedLevel3']))
        # Handle dash or bullet lists
        elif line.startswith('- ') or line.startswith('* ') or line.startswith('• '):
            # Remove the bullet character and any leading space
            if line.startswith('- '):
                list_text = line[2:].strip()
            elif line.startswith('* '):
                list_text = line[2:].strip()
            elif line.startswith('• '):
                list_text = line[2:].strip()
                
            list_text = _process_bold_text(list_text)
            story.append(Paragraph(f"• {list_text}", styles['BulletPoint']))
        # Handle bold text
        elif '**' in line:
            formatted_text = _process_bold_text(line)
            story.append(Paragraph(formatted_text, styles['SOPNormal']))
        # Regular text - might be part of a paragraph
        elif line:
            # Collect lines until we hit an empty line or a heading
            paragraph_lines = [line]
            j = i + 1
            while j < len(lines) and lines[j].strip() and not (
                lines[j].strip().startswith(('#', '- ', '* ', '• ')) or 
                re.match(r'^\d+(\.\d+)*\.', lines[j].strip())
            ):
                paragraph_lines.append(lines[j].strip())
                j += 1
            
            # Join the paragraph lines and process any bold text
            paragraph_text = ' '.join(paragraph_lines)
            paragraph_text = _process_bold_text(paragraph_text)
            
            story.append(Paragraph(paragraph_text, styles['SOPNormal']))
            
            # Update index to skip processed lines
            i = j - 1
        
        i += 1
    
    return story

def _process_bold_text(text: str) -> str:
    """Process bold text marked with ** in markdown"""
    # Replace **text** with <b>text</b> for ReportLab formatting
    return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

def _build_document_story(topic: str, sop_id: str, details: str, styles, company_name) -> list:
    story = []
    
    # Add title
    story.append(Paragraph("STANDARD OPERATING PROCEDURE", styles['SOPTitle']))
    story.append(Paragraph(f"Document ID: {sop_id}", styles['SOPDocID']))
    
    # Add metadata table with more professional styling
    metadata = [
        ["Document Title:", topic],
        ["Document ID:", sop_id],
        ["Effective Date:", datetime.now().strftime("%Y-%m-%d")],
        ["Status:", "Official"]
    ]
    
    metadata_table = Table(metadata, colWidths=[1.5*inch, 5*inch])
    metadata_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('BACKGROUND', (1,0), (1,-1), colors.white),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BOX', (0,0), (-1,-1), 1, colors.darkblue)
    ]))
    story.append(metadata_table)
    story.append(Spacer(1, 20))

    # Add approval section
    approval_data = [
        ["", "Name", "Position", "Date", "Signature"],
        ["Prepared by:", "", "", "", ""],
        ["Reviewed by:", "", "", "", ""],
        ["Approved by:", "", "", "", ""]
    ]
    
    approval_table = Table(approval_data, colWidths=[1.3*inch, 1.5*inch, 1.5*inch, 1*inch, 1.2*inch])
    approval_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BOX', (0,0), (-1,-1), 1, colors.darkblue),
        ('ALIGN', (0,1), (0,-1), 'LEFT')
    ]))
    story.append(approval_table)
    story.append(Spacer(1, 20))

    # Add sections with better styling
    sections = [
        ("PROCEDURE", details),
    ]

    for title, content in sections:
        story.append(Paragraph(title, styles['SOPHeading']))
        
        # Add a thin line under each main section heading
        story.append(Spacer(1, 1))
        
        # Special handling for PROCEDURE section
        if "PROCEDURE" in title:
            procedure_content = _format_markdown_content(content, styles)
            story.extend(procedure_content)
        else:
            story.append(Paragraph(content, styles['SOPNormal']))
            
        story.append(Spacer(1, 12))

    return story

def _add_first_page_header_footer(canvas, doc):
    canvas.saveState()
    
    # Header with logo placeholder and company name
    canvas.setFont('Helvetica-Bold', 18)
    canvas.setFillColor(colors.darkblue)
    
    # Company logo placeholder (could be replaced with actual logo)
    canvas.rect(36, letter[1] - 90, 100, 50, stroke=1, fill=0)
    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawCentredString(86, letter[1] - 60, "COMPANY LOGO")
    
    # Company name
    canvas.setFont('Helvetica-Bold', 18)
    canvas.drawRightString(letter[0] - 36, letter[1] - 60, doc._company_name)

    # Footer with document info and page number
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.black)
    
    # Draw footer line
    canvas.setStrokeColor(colors.darkblue)
    canvas.line(36, 50, letter[0] - 36, 50)
    
    # Draw footer text
    canvas.drawString(36, 36, f"Document ID: {doc._sop_id}")
    canvas.drawString(36, 24, f"Confidential")
    
    canvas.drawCentredString(letter[0]/2, 36, f"© {datetime.now().year} {doc._company_name}")
    
    page_number_text = f"Page {doc.page} of DRAFT"
    canvas.drawRightString(letter[0] - 36, 36, page_number_text)
    
    canvas.restoreState()

def _add_later_pages_header_footer(canvas, doc):
    canvas.saveState()
    
    # Header with title and document ID
    canvas.setFont('Helvetica-Bold', 10)
    canvas.setFillColor(colors.darkblue)
    canvas.drawString(36, letter[1] - 50, doc._company_name)
    
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(colors.black)
    canvas.drawRightString(letter[0] - 36, letter[1] - 50, f"SOP: {doc._topic}")
    
    # Draw header line
    canvas.setStrokeColor(colors.darkblue)
    canvas.line(36, letter[1] - 60, letter[0] - 36, letter[1] - 60)
    
    # Footer with document info and page number
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.black)
    
    # Draw footer line
    canvas.setStrokeColor(colors.darkblue)
    canvas.line(36, 50, letter[0] - 36, 50)
    
    # Draw footer text
    canvas.drawString(36, 36, f"Document ID: {doc._sop_id}")
    canvas.drawString(36, 24, f"Confidential")
    
    canvas.drawCentredString(letter[0]/2, 36, f"© {datetime.now().year} {doc._company_name}")
    
    page_number_text = f"Page {doc.page} of DRAFT"
    canvas.drawRightString(letter[0] - 36, 36, page_number_text)
    
    canvas.restoreState()