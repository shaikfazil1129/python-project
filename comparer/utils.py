import os
import re
import hashlib
import logging
import PyPDF2

# Configure logging
LOG_PATH = os.path.join("logs", "comparison.log")
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def delete_if_exists(filepath):
    """Delete the file at 'filepath' if it already exists."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logging.info(f"Existing file deleted: {filepath}")
    except Exception as e:
        logging.error(f"Failed to delete existing file {filepath}: {e}")

def extract_batch(filename):
    match = re.search(r'(\d{3}-\d{3}-\d{2}-\d{3})', filename)
    if match:
        return match.group(1)
    match = re.search(r'(\d+)', filename)
    if match:
        return match.group(1)
    return os.path.splitext(filename)[0].lower()

def sha256_of_file(filepath):
    """Compute SHA-256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def extract_text_from_pdf(pdf_path):
    """Extracts all text from a PDF file."""
    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    except Exception as e:
        logging.error(f"Error extracting text from {pdf_path}: {e}")
    return text
