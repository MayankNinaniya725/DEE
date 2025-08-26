import os
import re
import hashlib
import logging
import pandas as pd
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
from datetime import datetime
from .ocr_helper import extract_text_with_ocr

# Setup directories
LOG_FILE = "logs/master_log.xlsx"
ERROR_LOG_FILE = "logs/errors.log"
os.makedirs("logs", exist_ok=True)

# Get logger
logger = logging.getLogger("extractor.utils")

def generate_hash(entry, vendor_id):
    """Generate MD5 hash for duplicate detection."""
    key = f"{vendor_id}|" + "|".join(str(entry.get(k, "")) for k in ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"])
    return hashlib.md5(key.encode("utf-8")).hexdigest()

def load_master_log():
    """Load master log Excel file."""
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(columns=[
            "Vendor", "PLATE_NO", "HEAT_NO", "TEST_CERT_NO",
            "Filename", "Page", "Source PDF", "Created", "Hash"
        ])
    return pd.read_excel(LOG_FILE)

def save_to_log(entry):
    """Save entry into Excel log (avoid duplicates)."""
    df = load_master_log()
    if entry["Hash"] in df["Hash"].values:
        return
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    try:
        df.to_excel(LOG_FILE, index=False)
    except PermissionError:
        print("❌ Please close 'logs/master_log.xlsx' and run again.")

def extract_entries_from_text(text, vendor_config):
    """
    Extract multiple entries (Plate + Heat + Test Cert).
    Insert dummy entries if nothing is matched (for debugging).
    """
    fields = vendor_config["fields"]

    # Log preview of raw text
    logger.info("🔍 Raw text preview:\n" + (text[:1000] if text else "⚠️ No text extracted"))

    # Run regex matches
    plates = re.findall(fields["PLATE_NO"], text, re.IGNORECASE) if text else []
    heats = re.findall(fields["HEAT_NO"], text, re.IGNORECASE) if text else []
    certs = re.findall(fields["TEST_CERT_NO"], text, re.IGNORECASE) if text else []

    # Usually one certificate per page → apply same cert to all
    test_cert_no = certs[0] if certs else None

    entries = []
    if test_cert_no:  # Only proceed if certificate exists
        max_len = max(len(plates), len(heats))
        for i in range(max_len):
            plate = plates[i] if i < len(plates) else None
            heat = heats[i] if i < len(heats) else None

            if plate and heat and test_cert_no:
                entries.append({
                    "PLATE_NO": plate.strip(),
                    "HEAT_NO": heat.strip(),
                    "TEST_CERT_NO": test_cert_no.strip()
                })

    # 🔹 DEBUG MODE: if nothing matched, insert dummy entry
    if not entries:
        logger.warning("⚠️ No matches found — inserting dummy debug entry")
        entries = [{
            "PLATE_NO": "DEBUG_PLATE",
            "HEAT_NO": "DEBUG_HEAT",
            "TEST_CERT_NO": "DEBUG_CERT"
        }]

    return entries

def extract_multi_entries(pdf_path, vendor_config, output_folder):
    """Main extraction pipeline with safe filename handling."""
    logger = logging.getLogger(__name__)
    logger.info("=== Starting PDF Extraction ===")
    logger.info(f"PDF Path: {pdf_path}")
    logger.info(f"Vendor Config: {vendor_config}")
    logger.info(f"Output Folder: {output_folder}")
    
    results = []
    vendor_id = vendor_config.get("vendor_id")
    vendor_name = vendor_config.get("vendor_name")
    
    if not vendor_id or not vendor_name:
        logger.error("Missing vendor_id or vendor_name in config")
        raise ValueError("Invalid vendor configuration: missing vendor_id or vendor_name")

    vendor_output_dir = os.path.join(output_folder, vendor_name.replace(" ", "_"))
    os.makedirs(vendor_output_dir, exist_ok=True)

    reader = PdfReader(pdf_path)

    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages):
            try:
                # Extract text (OCR fallback)
                text = page.extract_text()
                if not text or len(text.strip()) < 50:
                    text = extract_text_with_ocr(pdf_path, idx)

                # Extract fields using vendor patterns (with debug fallback)
                entries = extract_entries_from_text(text, vendor_config)

                for entry in entries:
                    entry["Hash"] = generate_hash(entry, vendor_id)
                    if entry["Hash"] in load_master_log()["Hash"].values:
                        print(f"[SKIPPED] Duplicate: {entry}")
                        continue

                    # Build filename dynamically & sanitize it
                    filename_parts = [
                        entry.get(k, "NA")
                        .replace("/", "-")
                        .replace("\\", "-")
                        .replace("\n", " ")
                        .replace("\r", " ")
                        .strip()
                        for k in vendor_config["fields"].keys()
                    ]
                    raw_filename = "_".join(filename_parts)
                    safe_filename = re.sub(r'[<>:"/\\|?*\n\r\t]+', " ", raw_filename).strip() + ".pdf"

                    # Save extracted PDF page
                    writer = PdfWriter()
                    writer.add_page(reader.pages[idx])
                    file_path = os.path.join(vendor_output_dir, safe_filename)
                    with open(file_path, "wb") as f:
                        writer.write(f)

                    # Save log entry
                    log_entry = {
                        "Vendor": vendor_name,
                        "Filename": safe_filename,
                        "Page": idx + 1,
                        "Source PDF": os.path.basename(pdf_path),
                        "Created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Hash": entry["Hash"],
                        **entry
                    }
                    save_to_log(log_entry)
                    results.append(log_entry)
                    print(f"[✔] Saved: {safe_filename}")

            except Exception as e:
                logging.error(f"Error processing page {idx+1} in {pdf_path}: {e}")
                print(f"[!] Error processing page {idx+1}: {e}")

    return results

def extract_pdf_fields(pdf_path, vendor_config, output_folder="extracted_output"):
    """
    Wrapper for views.py: extracts entries from a PDF using vendor config
    and returns the results.
    """
    return extract_multi_entries(pdf_path, vendor_config, output_folder)
