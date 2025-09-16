import os
import re
import hashlib
import logging
import pandas as pd
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
from datetime import datetime
from typing import Dict, List, Any, Tuple

from .ocr_helper import extract_text_with_ocr
from .pattern_extractor import extract_patterns_from_text

# Setup logging
logger = logging.getLogger(__name__)

def get_pattern(field_info: Any) -> str:
    """Extract pattern from field configuration."""
    if isinstance(field_info, str):
        return field_info
    elif isinstance(field_info, dict):
        return field_info.get("pattern", "")
    return ""

def extract_text_from_page(page: Any) -> str:
    """Extract text from a page with cleanup."""
    try:
        text = page.extract_text()
        if text:
            text = re.sub(r'\s+', ' ', text)
            text = text.replace('\u200b', '')
            return text.strip()
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
    return ""

def extract_tables_from_page(page: Any, vendor_config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract tabular data from a page."""
    entries = []
    try:
        tables = page.extract_tables()
        if not tables:
            return []

        fields = vendor_config["fields"]
        for table in tables:
            if not table or len(table) < 2:
                continue

            # Try to identify field columns
            header_row = [str(h).strip() if h else "" for h in table[0]]
            field_columns = {}

            for field_name, field_info in fields.items():
                pattern = get_pattern(field_info)
                column_name = field_info.get("table_column", "") if isinstance(field_info, dict) else ""

                for idx, header in enumerate(header_row):
                    if column_name and column_name.lower() in header.lower():
                        field_columns[field_name] = idx
                        break
                    if re.search(pattern, header, re.IGNORECASE):
                        field_columns[field_name] = idx
                        break

            # Process each data row
            for row in table[1:]:
                entry = {
                    "PLATE_NO": "NA",
                    "HEAT_NO": "NA",
                    "TEST_CERT_NO": "NA"
                }

                for field_name, col_idx in field_columns.items():
                    if col_idx < len(row) and row[col_idx]:
                        value = str(row[col_idx]).strip()
                        pattern = get_pattern(fields[field_name])
                        
                        # Apply pattern matching
                        match = re.search(pattern, value, re.IGNORECASE)
                        if match:
                            value = match.group(1) if match.lastindex else match.group(0)
                            value = value.strip()

                            # Map to normalized field names
                            if field_name in ["PART_NO", "PRODUCT_NO"]:
                                entry["PLATE_NO"] = value
                            elif field_name in ["CERTIFICATE_NO", "REPORT_NO"]:
                                entry["TEST_CERT_NO"] = value
                            else:
                                entry[field_name] = value

                # Add non-empty entries
                if any(v != "NA" for v in entry.values()):
                    entries.append(entry)

    except Exception as e:
        logger.error(f"Table extraction failed: {e}")
        return []

    return entries

def generate_hash(entry: Dict[str, str], vendor_id: str) -> str:
    """Generate hash for duplicate detection."""
    key = f"{vendor_id}|" + "|".join(str(entry.get(k, "")) for k in ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"])
    return hashlib.md5(key.encode("utf-8")).hexdigest()

def extract_pdf_fields(pdf_path: str, vendor_config: Dict[str, Any], output_folder: str = "extracted_output") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Extract fields from PDF using vendor config."""
    logger.info(f"Starting extraction for {pdf_path}")
    results = []
    stats = {
        "total_pages": 0,
        "successful_pages": 0,
        "ocr_fallback_pages": [],
        "failed_pages": [],
        "extraction_success": False,
        "partial_extraction": False
    }

    vendor_id = vendor_config.get("vendor_id")
    vendor_name = vendor_config.get("vendor_name")
    if not vendor_id or not vendor_name:
        raise ValueError("Invalid vendor configuration: missing vendor_id or vendor_name")

    vendor_output_dir = os.path.join(output_folder, vendor_name.replace(" ", "_"))
    os.makedirs(vendor_output_dir, exist_ok=True)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            reader = PdfReader(pdf_path)
            stats["total_pages"] = len(pdf.pages)

            for idx, page in enumerate(pdf.pages):
                try:
                    entries = []
                    used_ocr = False

                    # Try table extraction first if enabled
                    if vendor_config.get("extraction_mode") == "table":
                        entries = extract_tables_from_page(page, vendor_config)

                    # If no tables found, try text extraction
                    if not entries:
                        text = extract_text_from_page(page)
                        if not text or len(text.strip()) < 50:
                            text = extract_text_with_ocr(pdf_path, idx)
                            used_ocr = True
                            stats["ocr_fallback_pages"].append(idx + 1)

                        if text:
                            entries = extract_patterns_from_text(text, vendor_config)

                    if not entries:
                        logger.warning(f"No entries found on page {idx + 1}")
                        stats["failed_pages"].append(idx + 1)
                        continue

                    stats["successful_pages"] += 1

                    # Process entries
                    for entry in entries:
                        entry["Hash"] = generate_hash(entry, vendor_id)
                        if any(r["Hash"] == entry["Hash"] for r in results):
                            logger.info(f"Skipping duplicate entry: {entry}")
                            continue

                        # Create filename
                        filename_parts = [
                            str(entry.get(k, "NA"))
                            .replace("/", "-")
                            .replace("\\", "-")
                            .replace("\n", " ")
                            .replace("\r", " ")
                            .strip()
                            for k in ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"]
                        ]
                        safe_filename = re.sub(
                            r'[<>:"/\\|?*\n\r\t]+',
                            " ",
                            "_".join(filename_parts)
                        ).strip() + ".pdf"

                        # Save PDF page
                        output_path = os.path.join(vendor_output_dir, safe_filename)
                        writer = PdfWriter()
                        writer.add_page(reader.pages[idx])
                        with open(output_path, "wb") as f:
                            writer.write(f)

                        # Add to results
                        entry.update({
                            "Vendor": vendor_name,
                            "Filename": safe_filename,
                            "Page": idx + 1,
                            "Source PDF": os.path.basename(pdf_path),
                            "Created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "OCR_Used": used_ocr
                        })
                        results.append(entry)
                        
                        logger.info(f"Saved entry: {safe_filename}")

                except Exception as e:
                    logger.error(f"Error processing page {idx + 1}: {e}")
                    stats["failed_pages"].append(idx + 1)

    except Exception as e:
        logger.error(f"Failed to process PDF {pdf_path}: {e}")
        raise

    # Update final statistics
    stats["extraction_success"] = len(results) > 0
    stats["partial_extraction"] = len(results) > 0 and len(stats["failed_pages"]) > 0

    return results, stats