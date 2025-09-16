import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def extract_patterns_from_text(text: str, vendor_config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract patterns from text with improved value sharing."""
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
                    value = match.group(1) if match.lastindex else match.group(0)
                    values.append(value.strip())
        else:
            # Global search
            all_matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if all_matches:
                for match in all_matches:
                    value = match.group(1) if match.lastindex else match.group(0)
                    values.append(value.strip())

        # Store matches
        matches[field_name] = values

        # Store shared values
        if share_value and values:
            shared_values[field_name] = values[0]
    
    # Step 2: Create entries based on plate numbers
    plate_vals = matches.get("PLATE_NO", [])
    if not plate_vals and vendor_config.get("multi_match", False):
        # If no plates found but multi_match is true, create a single entry
        if any(matches.values()):
            plate_vals = ["NA"]

    for plate_no in plate_vals:
        entry = {
            "PLATE_NO": str(plate_no).strip(),
            "HEAT_NO": str(shared_values.get("HEAT_NO", matches.get("HEAT_NO", ["NA"])[0] if matches.get("HEAT_NO", []) else "NA")).strip(),
            "TEST_CERT_NO": str(shared_values.get("TEST_CERT_NO", matches.get("TEST_CERT_NO", ["NA"])[0] if matches.get("TEST_CERT_NO", []) else "NA")).strip()
        }
        entries.append(entry)

    return entries