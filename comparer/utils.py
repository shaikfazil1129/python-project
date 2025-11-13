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

def find_files(root_dir, extension):
    """
    Recursively finds all files with a given extension and returns a map of
    {relative_path: full_path}.
    """
    file_map = {}
    for dirpath, _, filenames in os.walk(root_dir):
        # Skip empty directories
        if not filenames:
            continue

        for filename in filenames:
            if filename.lower().endswith(extension):
                full_path = os.path.join(dirpath, filename)
                # This relative_path is the new "key"
                # e.g., "7021\report-1.xlsx"
                relative_path = os.path.relpath(full_path, root_dir)
                file_map[relative_path] = full_path
    return file_map

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
