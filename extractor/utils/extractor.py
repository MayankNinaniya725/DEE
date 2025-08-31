# import os
# import re
# import hashlib
# import logging
# import pandas as pd
# import pdfplumber
# from PyPDF2 import PdfReader, PdfWriter
# from datetime import datetime
# from .ocr_helper import extract_text_with_ocr

# # Setup directories
# LOG_FILE = "logs/master_log.xlsx"
# ERROR_LOG_FILE = "logs/errors.log"
# os.makedirs("logs", exist_ok=True)

# # Get logger
# logger = logging.getLogger("extractor.utils")

# def generate_hash(entry, vendor_id):
#     """Generate MD5 hash for duplicate detection."""
#     key = f"{vendor_id}|" + "|".join(str(entry.get(k, "")) for k in ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"])
#     return hashlib.md5(key.encode("utf-8")).hexdigest()

# def load_master_log():
#     """Load master log Excel file."""
#     if not os.path.exists(LOG_FILE):
#         return pd.DataFrame(columns=[
#             "Sr No","Vendor", "PLATE_NO", "HEAT_NO", "TEST_CERT_NO",
#             "Filename", "Page", "Source PDF", "Created", "Hash","Remarks"
#         ])
#     return pd.read_excel(LOG_FILE)

# def save_to_log(entry):
#     """Save entry into Excel log with Sr No and duplicate remarks."""
#     df = load_master_log()

#     # Assign Sr No
#     entry["Sr No"] = (df["Sr No"].max() + 1) if not df.empty else 1

#     # Check for duplicate
#     if entry["Hash"] in df["Hash"].values:
#         # Find the original Sr No of the duplicate
#         original_sr_no = df.loc[df["Hash"] == entry["Hash"], "Sr No"].iloc[0]
#         entry["Remarks"] = f"DUPLICATE of Sr No {original_sr_no}"
#     else:
#         entry["Remarks"] = ""

#     df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
#     try:
#         df.to_excel(LOG_FILE, index=False)
#     except PermissionError:
#         print("❌ Please close 'logs/master_log.xlsx' and run again.")



# def extract_entries_from_text(text, vendor_config):
#     """
#     Extract multiple entries dynamically using vendor-specific fields,
#     then normalize them into (PLATE_NO, HEAT_NO, TEST_CERT_NO).
#     """
#     fields = vendor_config["fields"]

#     # Run regex matches for all defined fields
#     matches = {}
#     for key, pattern in fields.items():
#         matches[key] = re.findall(pattern, text, re.IGNORECASE) if text else []

#     # Normalization map
#     normalization_map = {
#         "PLATE_NO": "PLATE_NO",
#         "PART_NO": "PLATE_NO",
#         "PRODUCT_NO": "PLATE_NO",

#         "HEAT_NO": "HEAT_NO",

#         "TEST_CERT_NO": "TEST_CERT_NO",
#         "CERTIFICATE_NO": "TEST_CERT_NO",
#         "REPORT_NO": "TEST_CERT_NO"
#     }

#     # Align multiple entries
#     plate_vals = matches.get("PLATE_NO", []) + matches.get("PART_NO", []) + matches.get("PRODUCT_NO", [])
#     heat_vals = matches.get("HEAT_NO", [])
#     cert_vals = (
#         matches.get("TEST_CERT_NO", [])
#         + matches.get("CERTIFICATE_NO", [])
#         + matches.get("REPORT_NO", [])
#     )

#     # Usually one cert per page → take first
#     cert_val = cert_vals[0] if cert_vals else None

#     entries = []
#     if cert_val:
#         max_len = max(len(plate_vals), len(heat_vals))
#         for i in range(max_len):
#             plate = plate_vals[i] if i < len(plate_vals) else None
#             heat = heat_vals[i] if i < len(heat_vals) else None

#             if (plate or heat) and cert_val:
#                 entries.append({
#                     "PLATE_NO": plate.strip() if plate else "NA",
#                     "HEAT_NO": heat.strip() if heat else "NA",
#                     "TEST_CERT_NO": cert_val.strip()
#                 })

#     # Fallback debug entry
#     if not entries:
#         entries = [{
#             "PLATE_NO": "DEBUG_PLATE",
#             "HEAT_NO": "DEBUG_HEAT",
#             "TEST_CERT_NO": "DEBUG_CERT"
#         }]

#     return entries

# def extract_multi_entries(pdf_path, vendor_config, output_folder):
#     """Main extraction pipeline with safe filename handling."""
#     logger = logging.getLogger(__name__)
#     logger.info("=== Starting PDF Extraction ===")
#     logger.info(f"PDF Path: {pdf_path}")
#     logger.info(f"Vendor Config: {vendor_config}")
#     logger.info(f"Output Folder: {output_folder}")
    
#     results = []
#     vendor_id = vendor_config.get("vendor_id")
#     vendor_name = vendor_config.get("vendor_name")
    
#     if not vendor_id or not vendor_name:
#         logger.error("Missing vendor_id or vendor_name in config")
#         raise ValueError("Invalid vendor configuration: missing vendor_id or vendor_name")

#     vendor_output_dir = os.path.join(output_folder, vendor_name.replace(" ", "_"))
#     os.makedirs(vendor_output_dir, exist_ok=True)

#     reader = PdfReader(pdf_path)

#     with pdfplumber.open(pdf_path) as pdf:
#         for idx, page in enumerate(pdf.pages):
#             try:
#                 # Extract text (OCR fallback)
#                 text = page.extract_text()
#                 if not text or len(text.strip()) < 50:
#                     text = extract_text_with_ocr(pdf_path, idx)

#                 # Extract fields using vendor patterns (with debug fallback)
#                 entries = extract_entries_from_text(text, vendor_config)

#                 for entry in entries:
#                     entry["Hash"] = generate_hash(entry, vendor_id)
#                     if entry["Hash"] in load_master_log()["Hash"].values:
#                         print(f"[SKIPPED] Duplicate: {entry}")

#                     # Build filename dynamically & sanitize it
#                     filename_parts = [
#                         entry.get(k, "NA")
#                         .replace("/", "-")
#                         .replace("\\", "-")
#                         .replace("\n", " ")
#                         .replace("\r", " ")
#                         .strip()
#                         for k in vendor_config["fields"].keys()
#                     ]
#                     raw_filename = "_".join(filename_parts)
#                     safe_filename = re.sub(r'[<>:"/\\|?*\n\r\t]+', " ", raw_filename).strip() + ".pdf"

#                     # Save extracted PDF page
#                     writer = PdfWriter()
#                     writer.add_page(reader.pages[idx])
#                     file_path = os.path.join(vendor_output_dir, safe_filename)
#                     with open(file_path, "wb") as f:
#                         writer.write(f)

#                     # Save log entry
#                     log_entry = {
#                         "Vendor": vendor_name,
#                         "Filename": safe_filename,
#                         "Page": idx + 1,
#                         "Source PDF": os.path.basename(pdf_path),
#                         "Created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                         "Hash": entry["Hash"],
#                         **entry
#                     }
#                     save_to_log(log_entry)
#                     results.append(log_entry)
#                     print(f"[✔] Saved: {safe_filename}")

#             except Exception as e:
#                 logging.error(f"Error processing page {idx+1} in {pdf_path}: {e}")
#                 print(f"[!] Error processing page {idx+1}: {e}")

#     return results

# def extract_pdf_fields(pdf_path, vendor_config, output_folder="extracted_output"):
#     """
#     Wrapper for views.py: extracts entries from a PDF using vendor config
#     and returns the results.
#     """
#     return extract_multi_entries(pdf_path, vendor_config, output_folder)




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

# Setup logging
logging.basicConfig(
    filename=ERROR_LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def generate_hash(entry, vendor_id):
    """Generate MD5 hash for duplicate detection."""
    # Use all fields present in entry for hash
    key = f"{vendor_id}|" + "|".join(str(entry.get(k, "")) for k in ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"])
    return hashlib.md5(key.encode("utf-8")).hexdigest()

def load_master_log():
    """Load master log Excel file."""
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(columns=[
            "Sr No", "Vendor", "PLATE_NO", "HEAT_NO", "TEST_CERT_NO",
            "Filename", "Page", "Source PDF", "Created", "Hash", "Remarks"
        ])
    return pd.read_excel(LOG_FILE)

def save_to_log(entry):
    """Save entry into Excel log with Sr No and duplicate remarks."""
    df = load_master_log()
    # Assign Sr No
    entry["Sr No"] = (df["Sr No"].max() + 1) if not df.empty else 1
    # Check for duplicate
    if entry["Hash"] in df["Hash"].values:
        # Find the original Sr No of the duplicate
        original_sr_no = df.loc[df["Hash"] == entry["Hash"], "Sr No"].iloc[0]
        entry["Remarks"] = f"DUPLICATE of Sr No {original_sr_no}"
    else:
        entry["Remarks"] = ""
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    try:
        df.to_excel(LOG_FILE, index=False)
    except PermissionError:
        print("❌ Please close 'logs/master_log.xlsx' and run again.")

def extract_entries_from_text(text, vendor_config, page=None):
    """
    Enhanced extractor that:
    - Tries to extract structured table rows if `page` object is provided (pdfplumber page),
    - Falls back to regex on raw text if tables are missing,
    - Extracts Plate No, Heat No, and Test Certificate No entries.
    """
    vendor_id = vendor_config["vendor_id"]
    fields = vendor_config["fields"]
    entries = []

    # Vendor-specific extraction logic for POSCO
    if vendor_id == "posco" and page:
        tables = page.extract_tables()
        cert_no_match = re.search(fields["TEST_CERT_NO"], text, re.IGNORECASE)
        cert_no = cert_no_match.group(1) if cert_no_match and cert_no_match.lastindex else (cert_no_match.group(0) if cert_no_match else None)
        for table in tables:
            for row in table:
                plate_no, heat_no = None, None
                for cell in row:
                    if cell:
                        # Use search (not fullmatch) to handle partial matches or noisy data
                        if re.search(fields["PLATE_NO"], cell):
                            plate_no = cell.strip()
                        if re.search(fields["HEAT_NO"], cell):
                            heat_no = cell.strip()
                if plate_no and heat_no:
                    entries.append({
                        "PLATE_NO": plate_no,
                        "HEAT_NO": heat_no,
                        "TEST_CERT_NO": cert_no
                    })
        if entries:
            return entries

    # Default extraction fallback logic for JSW, CITIC and others
    test_cert_pattern = re.compile(fields["TEST_CERT_NO"], re.IGNORECASE)
    cert_matches = list(test_cert_pattern.finditer(text))

    if cert_matches:
        for idx, cert_match in enumerate(cert_matches):
            tc_no = cert_match.group(1) if cert_match.lastindex else cert_match.group(0)
            start = cert_match.end()
            end = cert_matches[idx+1].start() if idx+1 < len(cert_matches) else len(text)
            block_text = text[start:end]

            # Normalize whitespace for robust matching
            normalized_block = re.sub(r'\s+', ' ', block_text)
            combined_pattern = re.compile(
                rf"({fields['PLATE_NO']}).*?({fields['HEAT_NO']})",
                re.IGNORECASE
            )
            for match in combined_pattern.finditer(normalized_block):
                entries.append({
                    "PLATE_NO": match.group(1),
                    "HEAT_NO": match.group(2),
                    "TEST_CERT_NO": tc_no
                })
    else:
        plate_pattern = re.compile(fields["PLATE_NO"], re.IGNORECASE)
        heat_pattern = re.compile(fields["HEAT_NO"], re.IGNORECASE)
        plates = plate_pattern.findall(text)
        heats = heat_pattern.findall(text)
        for p, h in zip(plates, heats):
            entries.append({
                "PLATE_NO": p,
                "HEAT_NO": h,
                "TEST_CERT_NO": None
            })

    return entries

def extract_multi_entries(pdf_path, vendor_config, output_folder):
    """Main extraction pipeline with safe filename handling and OCR fallback tracking."""
    logger = logging.getLogger(__name__)
    logger.info("=== Starting PDF Extraction ===")
    logger.info(f"PDF Path: {pdf_path}")
    logger.info(f"Vendor Config: {vendor_config}")
    logger.info(f"Output Folder: {output_folder}")
    
    results = []
    ocr_fallback_pages = []  # Track pages that needed OCR fallback
    failed_pages = []       # Track pages that failed completely
    
    vendor_id = vendor_config.get("vendor_id")
    vendor_name = vendor_config.get("vendor_name")
    if not vendor_id or not vendor_name:
        logger.error("Missing vendor_id or vendor_name in config")
        raise ValueError("Invalid vendor configuration: missing vendor_id or vendor_name")
    
    vendor_output_dir = os.path.join(output_folder, vendor_name.replace(" ", "_"))
    os.makedirs(vendor_output_dir, exist_ok=True)
    
    reader = PdfReader(pdf_path)
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for idx, page in enumerate(pdf.pages):
            try:
                # Extract text with potential OCR fallback
                text = page.extract_text()
                used_ocr = False
                
                if not text or len(text.strip()) < 50:
                    logger.info(f"Using OCR fallback for page {idx + 1} due to insufficient text")
                    text = extract_text_with_ocr(pdf_path, idx)
                    used_ocr = True
                    ocr_fallback_pages.append(idx + 1)  # Store 1-based page number
                
                # Extract fields using vendor patterns
                entries = extract_entries_from_text(text, vendor_config, page=page)
                
                # If no entries found even with OCR, mark as needing better OCR
                if not entries and used_ocr:
                    logger.warning(f"OCR fallback didn't yield results on page {idx + 1}")
                    continue
                
                # If no entries found with regular extraction, try OCR as a fallback
                if not entries and not used_ocr:
                    logger.info(f"No entries found with standard extraction, trying OCR for page {idx + 1}")
                    text = extract_text_with_ocr(pdf_path, idx)
                    entries = extract_entries_from_text(text, vendor_config, page=page)
                    
                    if entries:
                        used_ocr = True
                        ocr_fallback_pages.append(idx + 1)  # Store 1-based page number
                    else:
                        logger.warning(f"Failed to extract entries from page {idx + 1} even with OCR")
                        failed_pages.append(idx + 1)  # Store 1-based page number
                        continue

                for entry in entries:
                    entry["Hash"] = generate_hash(entry, vendor_id)
                    if entry["Hash"] in load_master_log()["Hash"].values:
                        logger.info(f"[SKIPPED] Duplicate: {entry}")
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
                        "OCR_Used": used_ocr,
                        **entry
                    }
                    save_to_log(log_entry)
                    results.append(log_entry)
                    logger.info(f"[✔] Saved: {safe_filename}")

            except Exception as e:
                logger.error(f"Error processing page {idx + 1} in {pdf_path}: {e}")
                failed_pages.append(idx + 1)  # Store 1-based page number
                print(f"[!] Error processing page {idx + 1}: {e}")
    
    # Include OCR and failure info with results
    extraction_stats = {
        "total_pages": total_pages,
        "successful_pages": total_pages - len(failed_pages),
        "ocr_fallback_pages": ocr_fallback_pages,
        "failed_pages": failed_pages,
        "extraction_success": len(results) > 0,
        "partial_extraction": len(results) > 0 and (len(ocr_fallback_pages) > 0 or len(failed_pages) > 0),
    }
    
    return results, extraction_stats

def extract_pdf_fields(pdf_path, vendor_config, output_folder="extracted_output"):
    """
    Wrapper for views.py: extracts entries from a PDF using vendor config
    and returns the results along with extraction statistics.
    
    Returns:
        tuple: (list of extracted entries, extraction statistics dict)
    """
    return extract_multi_entries(pdf_path, vendor_config, output_folder)
