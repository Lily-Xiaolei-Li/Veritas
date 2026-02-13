from pathlib import Path

import pytest

from app.services.document_processing_service import (
    convert_file_to_artifact_payloads,
    generate_docx_bytes,
    generate_xlsx_bytes,
)


def test_generate_docx_bytes_roundtrip(tmp_path: Path):
    content = "Title\n\nParagraph one.\nLine two.\n\nParagraph two."
    b = generate_docx_bytes(content)
    assert isinstance(b, (bytes, bytearray))
    assert len(b) > 1000

    p = tmp_path / "out.docx"
    p.write_bytes(b)

    payloads = convert_file_to_artifact_payloads(str(p), imported_via="test")
    assert payloads
    md = next(x for x in payloads if x["filename"].endswith(".md"))
    text = md["content"].decode("utf-8")
    assert "Title" in text
    assert "Paragraph one" in text


def test_generate_xlsx_bytes_roundtrip(tmp_path: Path):
    b = generate_xlsx_bytes(
        sheets=[
            {"name": "Sheet1", "headers": ["A", "B"], "rows": [[1, 2], [3, 4]]}
        ]
    )
    assert isinstance(b, (bytes, bytearray))
    assert len(b) > 1000

    p = tmp_path / "out.xlsx"
    p.write_bytes(b)

    payloads = convert_file_to_artifact_payloads(str(p), imported_via="test")
    # xlsx produces md + json
    names = {x["filename"] for x in payloads}
    assert any(n.endswith(".md") for n in names)
    assert any(n.endswith(".json") for n in names)


def test_convert_unsupported_file_type(tmp_path: Path):
    p = tmp_path / "bad.bin"
    p.write_bytes(b"\x00\x01\x02")
    with pytest.raises(RuntimeError):
        convert_file_to_artifact_payloads(str(p), imported_via="test")
