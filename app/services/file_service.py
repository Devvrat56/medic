import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return None
    return text

def extract_text_from_image(file_path):
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error reading Image {file_path}: {e}")
        return None

def extract_text_from_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading Text file {file_path}: {e}")
        return None

def save_and_process_file(file_storage):
    """
    Saves the uploaded file and extracts its text based on file type.
    """
    filename = secure_filename(file_storage.filename)
    if not allowed_file(filename):
        raise ValueError(f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file_storage.save(file_path)
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    if ext == 'pdf':
        return extract_text_from_pdf(file_path)
    elif ext in ['png', 'jpg', 'jpeg', 'bmp', 'tiff']:
        return extract_text_from_image(file_path)
    elif ext == 'txt':
        return extract_text_from_txt(file_path)
        
    return None
