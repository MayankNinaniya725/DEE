"""
Vendor Detection Utility for PDF Processing

This module provides functionality to detect the vendor from PDF content
using OCR and template matching logic.
"""

import os
import re
import logging
from typing import Tuple, Optional, Dict, Any

import pdfplumber
from .ocr_helper import extract_text_with_ocr
from .extractor import detect_multilingual_content
from ..models import Vendor

logger = logging.getLogger('extractor.vendor_detection')


def extract_pdf_text(pdf_path: str, max_pages: int = 3) -> str:
    """
    Extract text from the first few pages of a PDF for vendor detection.
    
    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to process (default: 3)
    
    Returns:
        Combined text from the specified pages
    """
    try:
        combined_text = ""
        
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_check = min(len(pdf.pages), max_pages)
            
            for page_idx in range(pages_to_check):
                page = pdf.pages[page_idx]
                
                # Try to extract text normally first
                text = page.extract_text()
                
                # If no text or very little text, use OCR
                if not text or len(text.strip()) < 50:
                    logger.info(f"Page {page_idx + 1}: Using OCR fallback for text extraction")
                    text = extract_text_with_ocr(pdf_path, page_idx)
                
                if text:
                    combined_text += f"\n--- Page {page_idx + 1} ---\n{text}\n"
        
        return combined_text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
        return ""


def detect_vendor_from_text(text: str) -> Tuple[Optional[str], float]:
    """
    Detect vendor from extracted PDF text using pattern matching.
    
    Args:
        text: Extracted text from PDF
    
    Returns:
        Tuple of (vendor_id, confidence_score)
        vendor_id: The detected vendor ID or None if no match
        confidence_score: Confidence level (0.0 to 1.0)
    """
    if not text:
        return None, 0.0
    
    text_lower = text.lower()
    
    # Vendor detection patterns with their confidence weights
    vendor_patterns = {
        'posco': {
            'patterns': [
                (r'posco\s+international', 0.9),
                (r'posco', 0.7),
                (r'pohang\s+iron\s+&?\s*steel', 0.8),
                (r'포스코', 0.9),  # POSCO in Korean
            ],
            'negative_patterns': [
                r'not\s+posco',
                r'ex-posco',
            ]
        },
        'tata_steel': {
            'patterns': [
                (r'tata\s+steel', 0.9),
                (r'tata\s+group', 0.6),
                (r'jamshedpur', 0.7),
            ],
            'negative_patterns': [
                r'not\s+tata',
                r'ex-tata',
            ]
        },
        'citic_steel': {
            'patterns': [
                (r'citic\s+steel', 0.9),
                (r'citic\s+group', 0.7),
                (r'中信钢铁', 0.9),  # CITIC Steel in Chinese
                (r'中信集团', 0.7),  # CITIC Group in Chinese
            ],
            'negative_patterns': [
                r'not\s+citic',
            ]
        },
        'jfe_steel': {
            'patterns': [
                (r'jfe\s+steel', 0.9),
                (r'jfe\s+holdings', 0.8),
                (r'japan\s+iron\s+&?\s*steel', 0.7),
                (r'川崎製鉄', 0.8),  # Kawasaki Steel in Japanese
                (r'JFE', 0.6),
            ],
            'negative_patterns': [
                r'not\s+jfe',
                r'ex-jfe',
            ]
        },
        'nippon_steel': {
            'patterns': [
                (r'nippon\s+steel', 0.9),
                (r'新日本製鐵', 0.9),  # Nippon Steel in Japanese
                (r'新日鐵', 0.8),     # Short form in Japanese
            ],
            'negative_patterns': [
                r'not\s+nippon',
                r'ex-nippon',
            ]
        },
        'baosteel': {
            'patterns': [
                (r'baosteel', 0.9),
                (r'bao\s+steel', 0.8),
                (r'宝钢', 0.9),      # Baosteel in Chinese
                (r'宝山钢铁', 0.9),  # Baoshan Iron & Steel in Chinese
            ],
            'negative_patterns': [
                r'not\s+baosteel',
                r'ex-baosteel',
            ]
        }
    }
    
    vendor_scores = {}
    
    # Check each vendor's patterns
    for vendor_id, config in vendor_patterns.items():
        score = 0.0
        match_count = 0
        
        # Check positive patterns
        for pattern, weight in config['patterns']:
            matches = re.findall(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            if matches:
                score += weight * len(matches)
                match_count += len(matches)
                logger.debug(f"Vendor {vendor_id}: Found {len(matches)} matches for '{pattern}' (weight: {weight})")
        
        # Check negative patterns (reduce score)
        for neg_pattern in config.get('negative_patterns', []):
            neg_matches = re.findall(neg_pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            if neg_matches:
                score -= 0.5 * len(neg_matches)
                logger.debug(f"Vendor {vendor_id}: Found {len(neg_matches)} negative matches for '{neg_pattern}'")
        
        # Normalize score based on text length and match count
        if match_count > 0:
            # Bonus for multiple matches
            if match_count > 1:
                score *= 1.2
            
            # Normalize by text length (longer texts might have more false positives)
            text_length_factor = min(1.0, 1000 / len(text)) if len(text) > 1000 else 1.0
            score *= text_length_factor
            
            vendor_scores[vendor_id] = min(score, 1.0)  # Cap at 1.0
    
    # Find the vendor with the highest score
    if vendor_scores:
        best_vendor = max(vendor_scores.items(), key=lambda x: x[1])
        vendor_id, confidence = best_vendor
        
        # Only return if confidence is above threshold
        if confidence >= 0.4:  # Minimum confidence threshold
            logger.info(f"Detected vendor: {vendor_id} (confidence: {confidence:.2f})")
            return vendor_id, confidence
    
    logger.info("No vendor detected with sufficient confidence")
    return None, 0.0


def detect_vendor_from_pdf(pdf_path: str) -> Tuple[Optional[str], float, Dict[str, Any]]:
    """
    Main function to detect vendor from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        Tuple of (vendor_id, confidence_score, metadata)
        vendor_id: The detected vendor ID or None if no match
        confidence_score: Confidence level (0.0 to 1.0)
        metadata: Additional information about the detection process
    """
    metadata = {
        'multilingual_detected': False,
        'fragmentation_detected': False,
        'pages_processed': 0,
        'text_length': 0,
        'detection_method': 'pattern_matching'
    }
    
    try:
        # Extract text from the first few pages
        text = extract_pdf_text(pdf_path, max_pages=3)
        metadata['text_length'] = len(text)
        metadata['pages_processed'] = text.count('--- Page') if text else 0
        
        if not text:
            logger.warning(f"No text extracted from PDF: {pdf_path}")
            return None, 0.0, metadata
        
        # Check for multilingual content
        is_multilingual, has_fragmentation = detect_multilingual_content(text)
        metadata['multilingual_detected'] = is_multilingual
        metadata['fragmentation_detected'] = has_fragmentation
        
        if is_multilingual:
            logger.info("Multilingual content detected - using enhanced detection")
            metadata['detection_method'] = 'multilingual_pattern_matching'
        
        # Detect vendor using pattern matching
        vendor_id, confidence = detect_vendor_from_text(text)
        
        return vendor_id, confidence, metadata
        
    except Exception as e:
        logger.error(f"Error detecting vendor from PDF {pdf_path}: {str(e)}")
        metadata['error'] = str(e)
        return None, 0.0, metadata


def validate_vendor_selection(pdf_path: str, selected_vendor_id: str) -> Dict[str, Any]:
    """
    Validate if the selected vendor matches the detected vendor from the PDF.
    
    Args:
        pdf_path: Path to the PDF file
        selected_vendor_id: Vendor ID selected by the user
    
    Returns:
        Dictionary containing validation results:
        {
            'is_valid': bool,
            'detected_vendor': str or None,
            'confidence': float,
            'message': str,
            'metadata': dict
        }
    """
    try:
        # Get the selected vendor object to validate it exists
        try:
            selected_vendor = Vendor.objects.get(id=selected_vendor_id)
            selected_vendor_key = getattr(selected_vendor, 'vendor_id', selected_vendor.id)
        except Vendor.DoesNotExist:
            return {
                'is_valid': False,
                'detected_vendor': None,
                'confidence': 0.0,
                'message': 'Selected vendor not found in database',
                'metadata': {'error': 'vendor_not_found'}
            }
        
        # Detect vendor from PDF
        detected_vendor, confidence, metadata = detect_vendor_from_pdf(pdf_path)
        
        # If no vendor could be detected
        if not detected_vendor:
            return {
                'is_valid': True,  # Allow processing if we can't detect vendor
                'detected_vendor': None,
                'confidence': confidence,
                'message': 'Could not detect vendor from PDF - proceeding with selected vendor',
                'metadata': metadata
            }
        
        # Check if detected vendor matches selected vendor
        # Handle both cases: vendor.id and vendor.vendor_id
        vendor_matches = (
            str(detected_vendor).lower() == str(selected_vendor_key).lower() or
            str(detected_vendor).lower() == str(selected_vendor.id).lower() or
            detected_vendor in str(selected_vendor.name).lower()
        )
        
        if vendor_matches:
            return {
                'is_valid': True,
                'detected_vendor': detected_vendor,
                'confidence': confidence,
                'message': f'Vendor validation successful (confidence: {confidence:.1%})',
                'metadata': metadata
            }
        else:
            # High confidence mismatch should block processing
            if confidence >= 0.7:
                return {
                    'is_valid': False,
                    'detected_vendor': detected_vendor,
                    'confidence': confidence,
                    'message': f'Vendor mismatch detected. PDF appears to be from {detected_vendor} (confidence: {confidence:.1%})',
                    'metadata': metadata
                }
            else:
                # Low confidence - allow processing but warn
                return {
                    'is_valid': True,
                    'detected_vendor': detected_vendor,
                    'confidence': confidence,
                    'message': f'Possible vendor mismatch detected ({detected_vendor}, confidence: {confidence:.1%}) - proceeding with selected vendor',
                    'metadata': metadata
                }
        
    except Exception as e:
        logger.error(f"Error validating vendor selection: {str(e)}")
        return {
            'is_valid': True,  # Default to allowing processing on error
            'detected_vendor': None,
            'confidence': 0.0,
            'message': f'Vendor validation error: {str(e)} - proceeding with selected vendor',
            'metadata': {'error': str(e)}
        }