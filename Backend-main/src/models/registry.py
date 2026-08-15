import hashlib
import os
import uuid
import shutil
from typing import BinaryIO



MODEL_STORAGE = "storage"


def save_model(file: bytes | BinaryIO, filename: str) -> dict[str, str | int]:
    model_id = str(uuid.uuid4())

    folder = os.path.join(MODEL_STORAGE, model_id)
    os.makedirs(folder, exist_ok=True)

    path = os.path.join(folder, filename)

    with open(path, "wb") as buffer:
        if isinstance(file, bytes):
            buffer.write(file)
        elif hasattr(file, 'read'):
            shutil.copyfileobj(
                file,
                buffer
            )
        else:
            raise TypeError("file must be bytes or a binary stream")

    checksum = calculate_sha256(path)

    size = os.path.getsize(path)

    return {
        "id": model_id,
        "path": path,
        "checksum": checksum,
        "size": size
    }


def calculate_sha256(path : str) -> str:
    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)

    return sha256.hexdigest()