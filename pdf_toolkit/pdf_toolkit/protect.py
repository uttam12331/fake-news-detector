from __future__ import annotations

import io

from pypdf import PasswordType, PdfReader, PdfWriter
from pypdf.errors import FileNotDecryptedError

from pdf_toolkit.errors import IncorrectPasswordError


def add_password(input_bytes: bytes, user_password: str, owner_password: str | None = None) -> bytes:
    reader = PdfReader(io.BytesIO(input_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=user_password, owner_password=owner_password, algorithm="AES-256")

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def remove_password(input_bytes: bytes, password: str) -> bytes:
    reader = PdfReader(io.BytesIO(input_bytes))
    if reader.is_encrypted:
        try:
            result = reader.decrypt(password)
        except FileNotDecryptedError as exc:
            raise IncorrectPasswordError("Incorrect password.") from exc
        if result == PasswordType.NOT_DECRYPTED:
            raise IncorrectPasswordError("Incorrect password.")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
