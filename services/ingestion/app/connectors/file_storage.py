import os
import uuid
from pathlib import Path


def save(content: bytes, ext: str, upload_dir: str) -> str:
    os.makedirs(upload_dir, exist_ok=True)
    path = f"{upload_dir}/{uuid.uuid4()}{ext}"
    with open(path, "wb") as f:
        f.write(content)
    return path


def file_ext(filename: str) -> str:
    return Path(filename).suffix.lower()
