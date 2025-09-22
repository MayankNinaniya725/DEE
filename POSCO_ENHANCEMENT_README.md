# Enhanced POSCO Steel Certificate Extraction

## Overview
This enhancement addresses complex table layout issues in POSCO steel certificates where:
- Tables are broken across multiple lines/pages
- Documents may be in portrait orientation or rotated
- Plate Numbers and Heat Numbers need vertical alignment matching
- Cells are misaligned or contain line breaks

## Key Features Implemented

### 1. Document Orientation Detection & Correction
- **File**: `extractor/utils/document_preprocessor.py`
- **Features**:
  - Auto-detects portrait vs landscape orientation
  - Identifies documents that need rotation
  - Applies automatic rotation before extraction
  - Cleans up temporary files after processing

### 2. Advanced POSCO Table Parser
- **File**: `extractor/utils/posco_table_parser.py`  
- **Features**:
  - Handles multi-line table rows and broken layouts
  - Uses vertical position alignment for Plate-Heat matching
  - Multiple extraction strategies with confidence scoring
  - Robust pattern matching for POSCO-specific formats

### 3. Enhanced Vendor Configuration
- **File**: `extractor/vendor_configs/posco_steel.json`
- **Features**:
  - Multiple regex patterns per field type
  - Vertical alignment matching configuration
  - Document preprocessing settings
  - Advanced table detection patterns

### 4. Integrated Extraction Pipeline
- **File**: `extractor/utils/extractor.py` (modified)
- **Features**:
  - Automatic POSCO document detection
  - Seamless integration with existing extraction flow
  - Preprocessing and specialized parsing when needed
  - Backwards compatibility with other vendors

## Pattern Recognition

### Plate Number Patterns
- `PP065420H=432` - Standard format with heat notation
- `PP060301` - Simple format
- Complex alphanumeric combinations

### Heat Number Patterns  
- `SU30682` - Standard SU prefix format
- `KOR` - Location/origin codes
- Various 5-8 digit combinations

### Certificate Number Patterns
- `241205-FP01KS-0001A1-0002` - Full certificate format
- Header extraction from document top

## Extraction Strategies

### 1. Structured Table Extraction (Priority 1)
- Identifies well-formed tables with clear headers
- Uses column mapping for field extraction
- Highest confidence matching

### 2. Positioned Text Extraction (Priority 2)
- Uses character coordinate information
- Matches fields by vertical alignment
- Handles misaligned table cells

### 3. Sequential Matching (Priority 3)
- Fallback for complex layouts
- Pairs plates and heats in document order
- Lower confidence but ensures extraction

## Usage

### Automatic Processing
The system automatically detects POSCO documents and applies enhanced processing:

```python
# Standard extraction call - no changes needed
results, stats = extract_pdf_fields(pdf_path, vendor_config)

# System automatically:
# 1. Detects if document needs orientation correction
# 2. Applies POSCO specialized parser if vendor_id = "posco"
# 3. Uses vertical alignment for field matching
# 4. Returns standard extraction results
```

### Manual Testing
```python
from extractor.utils.posco_table_parser import extract_posco_table_data

results = extract_posco_table_data(pdf_path)
# Returns list of {PLATE_NO, HEAT_NO, TEST_CERT_NO, page_number}
```

## Configuration Options

### Document Preprocessing
```json
"document_preprocessing": {
  "auto_rotate": true,
  "orientation_detection": true,
  "table_layout_correction": true
}
```

### Table Settings
```json
"table_settings": {
  "handle_multiline_rows": true,
  "vertical_alignment_matching": true,
  "position_tolerance": 5.0,
  "max_row_variance": 3
}
```

### Validation Rules
```json
"validation_rules": {
  "require_plate_heat_pairing": true,
  "min_extractions_per_page": 1,
  "max_extractions_per_page": 20
}
```

## Benefits

### For POSCO Documents
- ✅ Handles complex table layouts with broken rows
- ✅ Auto-corrects document orientation issues
- ✅ Accurate Plate-Heat number alignment
- ✅ Robust extraction even with scanning artifacts

### For System Stability
- ✅ Backwards compatible with existing vendors
- ✅ Automatic fallback to standard extraction
- ✅ Comprehensive error handling and cleanup
- ✅ Detailed logging for debugging

### For Users
- ✅ No additional steps required
- ✅ Higher extraction success rates
- ✅ More accurate data alignment
- ✅ Reduced manual correction needs

## Files Modified/Created

### New Files
- `extractor/utils/document_preprocessor.py`
- `extractor/utils/posco_table_parser.py`
- `test_posco_extraction.py`

### Modified Files
- `extractor/utils/extractor.py`
- `extractor/vendor_configs/posco_steel.json`

### Dependencies
- No new dependencies required
- Uses existing: pdfplumber, PyPDF2, pandas, re

## Testing

Run the comprehensive test:
```bash
python test_posco_extraction.py
```

Expected output: All tests pass with confirmation of pattern matching and component initialization.

## Troubleshooting

### If orientation detection fails:
- Check PDF is readable by pdfplumber
- Verify table structure indicators are present
- Review preprocessing logs for confidence scores

### If extraction finds no matches:
- Verify vendor_id is set to "posco"
- Check pattern matching in test script
- Review document for expected table structure

### If alignment is incorrect:
- Adjust `position_tolerance` in config
- Check `max_row_variance` setting
- Review extraction strategy priorities

## Future Enhancements

Potential improvements for complex documents:
- OCR preprocessing for scanned documents
- ML-based table structure detection
- Cross-page table continuation handling
- Template-based extraction for known formats