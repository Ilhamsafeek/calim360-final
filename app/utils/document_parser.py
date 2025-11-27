# =====================================================
# FILE: app/utils/document_parser.py
# Extract formatted text from uploaded documents
# =====================================================

import PyPDF2
import docx
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)

class DocumentParser:
    """Extract formatted text from uploaded files"""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from PDF (basic formatting)"""
        try:
            text_content = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                logger.info(f"📄 PDF has {len(pdf_reader.pages)} pages")
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    if text:
                        # Basic formatting preservation
                        formatted_text = DocumentParser._format_pdf_text(text)
                        text_content.append(f'<div class="page" data-page="{page_num}">\n{formatted_text}\n</div>')
            
            result = '\n\n'.join(text_content)
            logger.info(f"✅ Extracted {len(result)} characters from PDF")
            return result
        except Exception as e:
            logger.error(f"❌ PDF extraction error: {e}")
            return f"<p>Error extracting PDF content: {str(e)}</p>"
    
    @staticmethod
    def _format_pdf_text(text: str) -> str:
        """Apply basic HTML formatting to PDF text"""
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect potential headers (all caps, short lines)
            if len(line) < 100 and line.isupper() and len(line.split()) < 10:
                formatted_lines.append(f'<h3 style="margin-top: 20px; margin-bottom: 10px; font-weight: bold; color: #2762cb;">{line}</h3>')
            # Detect numbered/bulleted lists
            elif re.match(r'^[\d]+[\.\)]\s+', line) or re.match(r'^[•\-\*]\s+', line):
                formatted_lines.append(f'<p style="margin-left: 20px; margin-bottom: 5px;">• {line}</p>')
            else:
                formatted_lines.append(f'<p style="margin-bottom: 10px;">{line}</p>')
        
        return '\n'.join(formatted_lines)
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract text from DOCX with full formatting preservation"""
        try:
            doc = docx.Document(file_path)
            html_parts = []
            
            # Process document body elements in order
            for element in doc.element.body:
                if isinstance(element, CT_P):
                    # Paragraph
                    paragraph = Paragraph(element, doc)
                    html = DocumentParser._paragraph_to_html(paragraph)
                    if html:
                        html_parts.append(html)
                elif isinstance(element, CT_Tbl):
                    # Table
                    table = Table(element, doc)
                    html = DocumentParser._table_to_html(table)
                    if html:
                        html_parts.append(html)
            
            result = '\n\n'.join(html_parts)
            logger.info(f"✅ Extracted {len(result)} characters from DOCX with formatting")
            return result
            
        except Exception as e:
            logger.error(f"❌ DOCX extraction error: {e}")
            return f"<p>Error extracting DOCX content: {str(e)}</p>"
    
    @staticmethod
    def _paragraph_to_html(paragraph) -> str:
        """Convert DOCX paragraph to HTML with formatting"""
        if not paragraph.text.strip():
            return ""
        
        # Detect heading level
        if paragraph.style.name.startswith('Heading'):
            level = paragraph.style.name.replace('Heading ', '').strip()
            try:
                level_num = int(level) if level.isdigit() else 3
                level_num = min(level_num, 6)  # Cap at h6
            except:
                level_num = 3
            
            return f'<h{level_num} style="margin-top: 20px; margin-bottom: 10px; font-weight: bold; color: #2762cb;">{paragraph.text}</h{level_num}>'
        
        # Build HTML with inline formatting
        html_text = ""
        for run in paragraph.runs:
            text = run.text
            if not text:
                continue
            
            # Apply formatting
            if run.bold and run.italic:
                text = f'<strong><em>{text}</em></strong>'
            elif run.bold:
                text = f'<strong>{text}</strong>'
            elif run.italic:
                text = f'<em>{text}</em>'
            
            if run.underline:
                text = f'<u>{text}</u>'
            
            # Font color
            if run.font.color and run.font.color.rgb:
                rgb = run.font.color.rgb
                color = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
                text = f'<span style="color: {color};">{text}</span>'
            
            # Font size
            if run.font.size:
                size_pt = run.font.size.pt
                text = f'<span style="font-size: {size_pt}pt;">{text}</span>'
            
            html_text += text
        
        # Determine paragraph alignment
        alignment = ''
        if paragraph.alignment:
            align_map = {
                0: 'left',    # LEFT
                1: 'center',  # CENTER
                2: 'right',   # RIGHT
                3: 'justify'  # JUSTIFY
            }
            alignment = f'text-align: {align_map.get(paragraph.alignment, "left")};'
        
        # Check for list items
        if paragraph.style.name.startswith('List'):
            return f'<p style="margin-left: 20px; margin-bottom: 5px; {alignment}">• {html_text}</p>'
        else:
            return f'<p style="margin-bottom: 10px; {alignment}">{html_text}</p>'
    
    @staticmethod
    def _table_to_html(table) -> str:
        """Convert DOCX table to HTML table"""
        html = '<table style="border-collapse: collapse; width: 100%; margin: 20px 0; border: 1px solid #ddd;">'
        
        for i, row in enumerate(table.rows):
            html += '<tr>'
            for cell in row.cells:
                # Use th for first row (header)
                tag = 'th' if i == 0 else 'td'
                style = 'padding: 8px; border: 1px solid #ddd;'
                if i == 0:
                    style += ' background-color: #f2f2f2; font-weight: bold;'
                
                cell_html = ""
                for paragraph in cell.paragraphs:
                    cell_html += DocumentParser._paragraph_to_html(paragraph)
                
                html += f'<{tag} style="{style}">{cell_html}</{tag}>'
            html += '</tr>'
        
        html += '</table>'
        return html
    
    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract text based on file extension"""
        ext = Path(file_path).suffix.lower()
        
        if ext == '.pdf':
            return DocumentParser.extract_text_from_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return DocumentParser.extract_text_from_docx(file_path)
        elif ext == '.txt':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Convert plain text to HTML with preserved line breaks
                content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                content = content.replace('\n\n', '</p><p>').replace('\n', '<br>')
                result = f'<p>{content}</p>'
                logger.info(f"✅ Read {len(result)} characters from TXT")
                return result
            except Exception as e:
                logger.error(f"❌ TXT read error: {e}")
                return f"<p>Error reading text file: {str(e)}</p>"
        
        return f"<p>Unsupported file type: {ext}</p>"