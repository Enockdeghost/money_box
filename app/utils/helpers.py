import os
from werkzeug.utils import secure_filename
from flask import current_app
import uuid

def save_receipt(file):
    filename = secure_filename(file.filename)
    unique = str(uuid.uuid4())[:8]
    name, ext = os.path.splitext(filename)
    filename = f"{name}_{unique}{ext}"
    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    return filename

def delete_receipt(filename):
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)