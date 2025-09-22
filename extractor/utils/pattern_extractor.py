import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def extract_patterns_from_text(text: str, vendor_config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract patterns from text with improved value sharing and fallback support."""
    entries = []
    if not text:
        return entries

    fields = vendor_config["fields"]
    matches = {}
    shared_values = {}

    # Step 1: Extract matches for each field
    for field_name, field_info in fields.items():
        pattern = field_info.get("pattern", "") if isinstance(field_info, dict) else field_info
        match_type = field_info.get("match_type", "global") if isinstance(field_info, dict) else "global"
        share_value = field_info.get("share_value", False) if isinstance(field_info, dict) else False
        
        # Extract values based on match type
        values = []
        if match_type == "line_by_line":
            for line in text.split('\n'):
                line_matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in line_matches:
                    value = None
                    # Try to get the first capturing group, fall back to full match
                    for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                        if match.group(i) is not None:
                            value = match.group(i)
                            break
                    if value is None:
                        value = match.group(0)
                    if value:
                        values.append(value.strip())
        else:
            # Global search
            all_matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if all_matches:
                for match in all_matches:
                    value = None
                    # Try to get the first capturing group, fall back to full match
                    for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                        if match.group(i) is not None:
                            value = match.group(i)
                            break
                    if value is None:
                        value = match.group(0)
                    if value:
                        values.append(value.strip())

        # Store matches
        matches[field_name] = values

        # Store shared values
        if share_value and values:
            shared_values[field_name] = values[0]
    
    # Step 2: Check for fallback strategy first
    fallback_config = vendor_config.get("fallback_strategy", {})
    use_fallback = False
    plate_vals = matches.get("PLATE_NO", [])
    
    if fallback_config.get("enabled", False) and not plate_vals:
        # OCR quality check
        ocr_threshold = fallback_config.get("conditions", {}).get("ocr_quality_threshold", 1000)
        has_certificate = bool(matches.get("TEST_CERT_NO", []))
        
        # Use fallback if:
        # 1. Text is too short (poor OCR quality), OR
        # 2. We have certificate but no plate numbers (partial extraction)
        if len(text) < ocr_threshold or has_certificate:
            logger.info(f"Using fallback strategy - OCR quality poor (text length: {len(text)}, has_cert: {has_certificate})")
            use_fallback = True
            
            # Use fallback entries
            fallback_entries = fallback_config.get("fallback_entries", [])
            for fb_entry in fallback_entries:
                plate_vals.append(fb_entry["PLATE_NO"])
    
    # Step 3: Create entries based on plate numbers
    if not plate_vals and vendor_config.get("multi_match", False):
        # If no plates found but multi_match is true, create a single entry
        if any(matches.values()):
            plate_vals = ["NA"]

    for plate_no in plate_vals:
        # Safely get values with proper None handling
        heat_no = shared_values.get("HEAT_NO")
        if heat_no is None:
            heat_matches = matches.get("HEAT_NO", [])
            if not heat_matches:
                # Check for fallback value
                heat_fallback = fields.get("HEAT_NO", {}).get("fallback_value")
                heat_no = heat_fallback if heat_fallback else "NA"
            else:
                heat_no = heat_matches[0]
        
        cert_no = shared_values.get("TEST_CERT_NO")
        if cert_no is None:
            cert_matches = matches.get("TEST_CERT_NO", [])
            cert_no = cert_matches[0] if cert_matches else "NA"
        
        entry = {
            "PLATE_NO": str(plate_no).strip() if plate_no is not None else "NA",
            "HEAT_NO": str(heat_no).strip() if heat_no is not None else "NA",
            "TEST_CERT_NO": str(cert_no).strip() if cert_no is not None else "NA"
        }
        
        # Add extraction quality indicator if fallback was used
        if use_fallback:
            entry["extraction_quality"] = "OCR_POOR_FALLBACK_USED"
            
        entries.append(entry)

    return entries