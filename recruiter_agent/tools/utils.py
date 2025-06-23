import os
import logging
from io import BytesIO
from fastapi import UploadFile, HTTPException

# Optional dependency for PDF parsing
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

logger = logging.getLogger(__name__)

# for local file upload (using local host)
def extract_text_from_pdf(file_path: str) -> str:
    if not os.path.exists(file_path) or not PdfReader:
        return "Dummy text..."
    try:
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            return "".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return f"Error reading PDF: {e}"

# for cloud deployment (using cloud run)
def extract_text_from_uploaded_pdf(file: UploadFile) -> str:
    if not PdfReader:
        raise ImportError("PyPDF2 is not installed. Cannot process PDFs.")
    try:
        pdf_stream = BytesIO(file.file.read())
        text = ""
        reader = PdfReader(pdf_stream)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error reading or parsing PDF: {e}"
        )
