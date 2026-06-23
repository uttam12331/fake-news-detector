import io

import pytest
from pypdf import PdfReader

from pdf_toolkit import protect
from pdf_toolkit.errors import IncorrectPasswordError


def test_add_password_encrypts(pdf_factory):
    doc = pdf_factory(2)
    protected = protect.add_password(doc, "secret")
    reader = PdfReader(io.BytesIO(protected))
    assert reader.is_encrypted


def test_remove_password_with_correct_password(pdf_factory):
    doc = pdf_factory(2)
    protected = protect.add_password(doc, "secret")
    unlocked = protect.remove_password(protected, "secret")
    reader = PdfReader(io.BytesIO(unlocked))
    assert not reader.is_encrypted
    assert len(reader.pages) == 2


def test_remove_password_with_wrong_password_raises(pdf_factory):
    doc = pdf_factory(2)
    protected = protect.add_password(doc, "secret")
    with pytest.raises(IncorrectPasswordError):
        protect.remove_password(protected, "wrong")


def test_remove_password_on_unencrypted_doc_is_noop(pdf_factory):
    doc = pdf_factory(2)
    result = protect.remove_password(doc, "whatever")
    reader = PdfReader(io.BytesIO(result))
    assert len(reader.pages) == 2
