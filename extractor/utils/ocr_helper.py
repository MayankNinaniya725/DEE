from pdf2image import convert_from_path
import pytesseract

def extract_text_with_ocr(pdf_path, page_num):
    images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1, dpi=300)
    if images:
        return pytesseract.image_to_string(images[0])
    return ""
