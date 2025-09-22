"""
Document Preprocessor for PDF Orientation and Layout Correction
Handles document rotation, orientation detection, and layout normalization
"""

import os
import re
import logging
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
from typing import Dict, List, Tuple, Any
import tempfile

logger = logging.getLogger(__name__)

class DocumentPreprocessor:
    """Handles document preprocessing for optimal extraction"""
    
    def __init__(self):
        self.temp_files = []
    
    def cleanup(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
        self.temp_files.clear()
    
    def detect_document_orientation(self, pdf_path: str) -> Dict[str, Any]:
        """
        Detect document orientation and suggest corrections
        Returns orientation info for each page
        """
        orientation_info = {
            'needs_correction': False,
            'pages': [],
            'suggested_rotation': {},
            'confidence': 0.0
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_info = self._analyze_page_orientation(page, page_num)
                    orientation_info['pages'].append(page_info)
                    
                    if page_info['suggested_rotation'] != 0:
                        orientation_info['needs_correction'] = True
                        orientation_info['suggested_rotation'][page_num] = page_info['suggested_rotation']
                        
            # Calculate overall confidence
            if orientation_info['pages']:
                avg_confidence = sum(p['confidence'] for p in orientation_info['pages']) / len(orientation_info['pages'])
                orientation_info['confidence'] = avg_confidence
                
        except Exception as e:
            logger.error(f"Error detecting document orientation: {e}")
            
        return orientation_info
    
    def _analyze_page_orientation(self, page, page_num: int) -> Dict[str, Any]:
        """Analyze individual page orientation"""
        page_info = {
            'page_num': page_num,
            'width': page.width,
            'height': page.height,
            'aspect_ratio': page.width / page.height if page.height > 0 else 1.0,
            'is_landscape': page.width > page.height,
            'suggested_rotation': 0,
            'confidence': 0.0,
            'table_indicators': []
        }
        
        try:
            # Extract text to analyze content patterns
            text = page.extract_text() or ""
            
            # Look for table structure indicators
            table_patterns = [
                r'Size\s+Product\s+No\.',
                r'Heat\s+No\.',
                r'Plate\s+No\.',
                r'Certificate\s+No\.',
                r'\|\s*Size\s*\|',
                r'\|\s*Product\s+No\.\s*\|',
                r'\|\s*Heat\s+No\.\s*\|'
            ]
            
            table_matches = 0
            for pattern in table_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    table_matches += 1
                    page_info['table_indicators'].append(pattern)
            
            # Check for POSCO specific indicators
            posco_indicators = [
                r'POSCO\s+INTERNATIONAL',
                r'Mill\s+Test\s+Certificate',
                r'Chemical\s+Composition',
                r'Tensile\s+Test'
            ]
            
            posco_matches = 0
            for pattern in posco_indicators:
                if re.search(pattern, text, re.IGNORECASE):
                    posco_matches += 1
            
            # Determine if document needs rotation
            confidence = 0.0
            suggested_rotation = 0
            
            # If document is in portrait but has table indicators, suggest landscape
            if not page_info['is_landscape'] and table_matches > 2:
                suggested_rotation = 90  # Rotate to landscape
                confidence = min(0.8, table_matches * 0.2)
            
            # If document is landscape but text flow suggests portrait
            elif page_info['is_landscape'] and table_matches < 2:
                # Check if rotating to portrait would help
                if posco_matches > 0:
                    suggested_rotation = -90  # Rotate to portrait
                    confidence = min(0.6, posco_matches * 0.15)
            
            # High confidence if we find clear table structure in landscape
            elif page_info['is_landscape'] and table_matches >= 3:
                confidence = min(0.9, table_matches * 0.25)
            
            page_info['suggested_rotation'] = suggested_rotation
            page_info['confidence'] = confidence
            
        except Exception as e:
            logger.error(f"Error analyzing page {page_num} orientation: {e}")
            
        return page_info
    
    def correct_document_orientation(self, pdf_path: str, orientation_info: Dict[str, Any]) -> str:
        """
        Create a corrected version of the PDF with proper orientation
        Returns path to corrected PDF
        """
        if not orientation_info.get('needs_correction', False):
            return pdf_path
        
        try:
            # Create temporary file for corrected PDF
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='corrected_')
            os.close(temp_fd)
            self.temp_files.append(temp_path)
            
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            for page_num, page in enumerate(reader.pages):
                rotation_angle = orientation_info['suggested_rotation'].get(page_num, 0)
                
                if rotation_angle != 0:
                    # Apply rotation
                    page.rotate(rotation_angle)
                    logger.info(f"Rotated page {page_num} by {rotation_angle} degrees")
                
                writer.add_page(page)
            
            # Write corrected PDF
            with open(temp_path, 'wb') as output_file:
                writer.write(output_file)
            
            logger.info(f"Created orientation-corrected PDF: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error correcting document orientation: {e}")
            return pdf_path
    
    def preprocess_document(self, pdf_path: str) -> str:
        """
        Main preprocessing function - detects and corrects orientation
        Returns path to preprocessed document
        """
        logger.info(f"Preprocessing document: {pdf_path}")
        
        # Detect orientation issues
        orientation_info = self.detect_document_orientation(pdf_path)
        
        if orientation_info['needs_correction']:
            logger.info(f"Document needs orientation correction (confidence: {orientation_info['confidence']:.2f})")
            corrected_path = self.correct_document_orientation(pdf_path, orientation_info)
            return corrected_path
        else:
            logger.info("Document orientation is correct, no preprocessing needed")
            return pdf_path

def preprocess_pdf_for_extraction(pdf_path: str) -> Tuple[str, DocumentPreprocessor]:
    """
    Convenience function to preprocess a PDF for extraction
    Returns (preprocessed_path, preprocessor_instance)
    """
    preprocessor = DocumentPreprocessor()
    try:
        preprocessed_path = preprocessor.preprocess_document(pdf_path)
        return preprocessed_path, preprocessor
    except Exception as e:
        logger.error(f"Error preprocessing PDF: {e}")
        preprocessor.cleanup()
        raise