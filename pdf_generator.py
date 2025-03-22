import os
import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import datetime

logger = logging.getLogger(__name__)

def create_pdf(title, transcription, summary, output_path):
    """
    Creates a PDF document containing transcription and summary information.
    
    Args:
        title (str): Title of the transcription
        transcription (str): Full transcription text
        summary (str): Summary text
        output_path (str): Path where the PDF will be saved
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create the PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=18,
            textColor=colors.darkblue,
            spaceAfter=12
        )
        
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=6,
            spaceBefore=12
        )
        
        normal_style = ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=10
        )
        
        # Create document elements
        elements = []
        
        # Add title
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 0.25 * inch))
        
        # Add date
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        elements.append(Paragraph(f"Generated on: {current_date}", styles['Italic']))
        elements.append(Spacer(1, 0.25 * inch))
        
        # Add summary section
        elements.append(Paragraph("Summary", heading_style))
        elements.append(Paragraph(summary, normal_style))
        elements.append(Spacer(1, 0.25 * inch))
        
        # Add transcription section
        elements.append(Paragraph("Full Transcription", heading_style))
        
        # Split transcription into paragraphs
        paragraphs = transcription.split('\n\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                elements.append(Paragraph(paragraph, normal_style))
        
        # Build the PDF
        doc.build(elements)
        
        logger.info(f"PDF created successfully: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating PDF: {str(e)}")
        return False
