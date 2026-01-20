import os
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def save_and_extract_pdf(file_storage):
    """
    Saves the uploaded PDF and extracts its text content.
    """
    filename = secure_filename(file_storage.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file_storage.save(file_path)
    
    # Extract text
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Error reading PDF {filename}: {e}")
        return None
        
    return text
