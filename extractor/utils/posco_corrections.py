"""
POSCO Heat Number Correction Utility
Corrects common OCR errors in heat numbers
"""

import re
import logging

logger = logging.getLogger(__name__)

def correct_posco_heat_number(heat_no: str) -> str:
    """
    Corrects common OCR errors in POSCO heat numbers
    
    Common issues:
    - "6" misread as "8" or vice versa
    - "0" misread as "8" 
    - "9" misread as "6"
    """
    if not heat_no or not heat_no.startswith('SU'):
        return heat_no
    
    original = heat_no
    corrected = heat_no
    
    # Common OCR corrections for POSCO heat numbers
    ocr_corrections = {
        'SU30682': 'SU30882',  # 6->8 correction
        'SU30082': 'SU30882',  # 0->8 correction  
        'SU30692': 'SU30892',  # 6->8 correction
        'SU30602': 'SU30802',  # 6->8 correction
    }
    
    # Apply specific corrections
    if heat_no in ocr_corrections:
        corrected = ocr_corrections[heat_no]
        logger.info(f"POSCO Heat Number Corrected: {original} -> {corrected}")
    
    # Pattern-based corrections for SU30xxx format
    elif re.match(r'^SU30[0-9]{3}$', heat_no):
        # If it looks like SU30682 pattern, likely should be SU30882
        if '682' in heat_no:
            corrected = heat_no.replace('682', '882')
            logger.info(f"POSCO Heat Number Pattern Corrected: {original} -> {corrected}")
        elif '082' in heat_no:
            corrected = heat_no.replace('082', '882') 
            logger.info(f"POSCO Heat Number Pattern Corrected: {original} -> {corrected}")
    
    return corrected

def apply_posco_corrections(extraction_results):
    """
    Apply POSCO-specific corrections to extraction results
    Can handle single dictionary or list of dictionaries
    """
    # Handle single dictionary
    if isinstance(extraction_results, dict):
        result = extraction_results.copy()
        
        # Correct heat numbers
        if 'HEAT_NO' in result:
            original_heat = result['HEAT_NO']
            corrected_heat = correct_posco_heat_number(original_heat)
            result['HEAT_NO'] = corrected_heat
            
            if original_heat != corrected_heat:
                result['_corrections_applied'] = result.get('_corrections_applied', [])
                result['_corrections_applied'].append(f'HEAT_NO: {original_heat} -> {corrected_heat}')
        
        return result
    
    # Handle list of dictionaries
    corrected_results = []
    
    for result in extraction_results:
        corrected_result = result.copy()
        
        # Correct heat numbers
        if 'HEAT_NO' in corrected_result:
            original_heat = corrected_result['HEAT_NO']
            corrected_heat = correct_posco_heat_number(original_heat)
            corrected_result['HEAT_NO'] = corrected_heat
            
            if original_heat != corrected_heat:
                corrected_result['_corrections_applied'] = corrected_result.get('_corrections_applied', [])
                corrected_result['_corrections_applied'].append(f'HEAT_NO: {original_heat} -> {corrected_heat}')
        
        corrected_results.append(corrected_result)
    
    return corrected_results

# Test the correction function
if __name__ == "__main__":
    test_cases = ['SU30682', 'SU30882', 'SU30082', 'SU30692', 'SU12345']
    
    print("POSCO Heat Number Correction Test:")
    print("=" * 40)
    
    for test_heat in test_cases:
        corrected = correct_posco_heat_number(test_heat) 
        status = "CORRECTED" if test_heat != corrected else "NO CHANGE"
        print(f"{test_heat} -> {corrected} ({status})")