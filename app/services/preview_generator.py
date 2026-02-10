"""
Preview Generator Service - Creates image previews of resumes
"""

import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import os
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import tempfile


class PreviewGenerator:
    """Generate preview images from resume documents"""
    
    def generate_preview(self, file_path: str, max_width: int = 800) -> str:
        """
        Generate a base64 encoded preview image of the document.
        
        Args:
            file_path: Path to the document
            max_width: Maximum width of the preview image
            
        Returns:
            Base64 encoded PNG image string
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".pdf":
            return self._preview_pdf(file_path, max_width)
        elif ext == ".docx":
            return self._preview_docx(file_path, max_width)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def _preview_pdf(self, file_path: str, max_width: int) -> str:
        """Generate preview from PDF"""
        doc = fitz.open(file_path)
        
        # Get first page
        page = doc[0]
        
        # Render at higher resolution for clarity
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Resize if needed
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        
        doc.close()
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _preview_docx(self, file_path: str, max_width: int) -> str:
        """Generate preview from DOCX - create a simple visual representation"""
        from PIL import Image, ImageDraw, ImageFont
        
        doc = Document(file_path)
        
        # Create a white image
        img_width = max_width
        img_height = 1100  # Approximate letter page ratio
        img = Image.new('RGB', (img_width, img_height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a system font, fall back to default
        try:
            font = ImageFont.truetype("arial.ttf", 11)
            font_bold = ImageFont.truetype("arialbd.ttf", 12)
            font_heading = ImageFont.truetype("arialbd.ttf", 14)
        except:
            font = ImageFont.load_default()
            font_bold = font
            font_heading = font
        
        y_pos = 30
        margin = 40
        line_height = 16
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                y_pos += 8
                continue
            
            if y_pos > img_height - 50:
                break
            
            # Determine style
            current_font = font
            color = (30, 30, 30)
            
            style_name = para.style.name if para.style else ''
            if 'Heading' in style_name or text.isupper():
                current_font = font_heading
                color = (20, 50, 100)
                y_pos += 5
            elif para.runs and para.runs[0].bold:
                current_font = font_bold
            
            # Word wrap
            words = text.split()
            line = ""
            for word in words:
                test_line = f"{line} {word}".strip()
                bbox = draw.textbbox((0, 0), test_line, font=current_font)
                if bbox[2] > img_width - margin * 2:
                    if line:
                        draw.text((margin, y_pos), line, fill=color, font=current_font)
                        y_pos += line_height
                    line = word
                else:
                    line = test_line
            
            if line:
                draw.text((margin, y_pos), line, fill=color, font=current_font)
                y_pos += line_height
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def generate_diff_html(self, original: str, optimized: str) -> str:
        """
        Generate HTML showing only the differences between original and optimized text.
        Shows changed sections with context, not the entire document.
        
        Returns:
            HTML string with highlighted differences
        """
        from diff_match_patch import diff_match_patch
        
        dmp = diff_match_patch()
        diffs = dmp.diff_main(original, optimized)
        dmp.diff_cleanupSemantic(diffs)
        
        # Build a list of changes with context
        changes = []
        context_chars = 50  # Characters of context around each change
        
        i = 0
        while i < len(diffs):
            op, text = diffs[i]
            
            if op != 0:  # This is a change (addition or deletion)
                # Get context before
                before_context = ""
                if i > 0 and diffs[i-1][0] == 0:
                    before_text = diffs[i-1][1]
                    before_context = before_text[-context_chars:] if len(before_text) > context_chars else before_text
                    if len(before_text) > context_chars:
                        before_context = "..." + before_context
                
                # Collect consecutive changes
                change_parts = []
                while i < len(diffs) and diffs[i][0] != 0:
                    change_op, change_text = diffs[i]
                    change_parts.append((change_op, change_text))
                    i += 1
                
                # Get context after
                after_context = ""
                if i < len(diffs) and diffs[i][0] == 0:
                    after_text = diffs[i][1]
                    after_context = after_text[:context_chars] if len(after_text) > context_chars else after_text
                    if len(after_text) > context_chars:
                        after_context = after_context + "..."
                
                changes.append({
                    'before': before_context,
                    'changes': change_parts,
                    'after': after_context
                })
            else:
                i += 1
        
        if not changes:
            return '<p class="no-changes">No text changes detected. The AI may have restructured or rephrased content.</p>'
        
        # Build HTML for each change
        html_parts = [f'<p class="change-count">Found <strong>{len(changes)}</strong> change(s):</p>']
        
        for idx, change in enumerate(changes, 1):
            html_parts.append(f'<div class="change-block">')
            html_parts.append(f'<div class="change-number">Change {idx}</div>')
            html_parts.append('<div class="change-content">')
            
            # Context before
            if change['before']:
                safe_before = self._escape_html(change['before'])
                html_parts.append(f'<span class="diff-context">{safe_before}</span>')
            
            # The actual changes
            for op, text in change['changes']:
                safe_text = self._escape_html(text)
                if op == -1:  # Deletion
                    html_parts.append(f'<span class="diff-removed">{safe_text}</span>')
                elif op == 1:  # Insertion
                    html_parts.append(f'<span class="diff-added">{safe_text}</span>')
            
            # Context after
            if change['after']:
                safe_after = self._escape_html(change['after'])
                html_parts.append(f'<span class="diff-context">{safe_after}</span>')
            
            html_parts.append('</div></div>')
        
        return ''.join(html_parts)
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters and convert newlines"""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('\n', '<br>')
        return text
