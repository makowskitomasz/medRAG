import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.extractor import extract_text


def test_extract_txt():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("Hello world\n\nSecond paragraph")
        tmp = f.name
    assert "Hello world" in extract_text(tmp)


def test_unsupported_extension():
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
        tmp = f.name
    with pytest.raises(ValueError, match="Unsupported"):
        extract_text(tmp)


def test_extract_pdf():
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Page content"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("pypdf.PdfReader", return_value=mock_reader):
        result = extract_text("test.pdf")

    assert result == "Page content"
