from pathlib import Path

import pytest

from app.services.document_processing_service import convert_file_to_artifact_payloads


def test_upload_style_renaming_logic(tmp_path: Path):
    # simulate what document_routes does: convert temp file then rename outputs
    # build a tiny xlsx file via openpyxl (dependency already in requirements)
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["A", "B"])
    ws.append([1, 2])
    tmp_file = tmp_path / "random_tmp_name.xlsx"
    wb.save(tmp_file)

    payloads = convert_file_to_artifact_payloads(str(tmp_file), imported_via="upload")
    assert len(payloads) >= 1

    source_file = "mydata.xlsx"
    original_stem = Path(source_file).stem

    for p in payloads:
        ext = Path(p["filename"]).suffix
        p["filename"] = f"{original_stem}{ext}"
        meta = p.get("artifact_meta") or {}
        meta.update({"source_file": source_file, "source_path": f"upload:{source_file}"})
        p["artifact_meta"] = meta

        assert p["filename"].startswith(original_stem)
        assert p["artifact_meta"]["source_file"] == source_file
        assert p["artifact_meta"]["source_path"] == f"upload:{source_file}"
