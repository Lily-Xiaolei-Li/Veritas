
import pytest


@pytest.mark.asyncio
async def test_document_read_docx_extracts_markdown(tmp_path):
    # Create a docx in workspace via tool
    import app.tools  # noqa: F401
    from app.tools.registry import execute_tool

    # Ensure workspace dir exists and is isolated for this test
    # Use backend/workspace (repo default) but within tmp_path to avoid polluting repo
    # We patch SETTINGS by setting env var if supported; fallback: write into configured workspace.
    # In this repo, workspace is a folder under backend/ by default.

    # Write docx
    write_res = await execute_tool(
        "document_write",
        {
            "path": "__tests__/doc_tools_test",
            "format": "docx",
            "text": "Hello world\n\nSecond paragraph.",
            "overwrite": True,
        },
    )
    assert write_res.success, write_res.error

    # Read it back
    read_res = await execute_tool(
        "document_read",
        {"path": "__tests__/doc_tools_test.docx", "max_bytes": 200000},
    )
    assert read_res.success, read_res.error
    outputs = read_res.output["outputs"]
    assert isinstance(outputs, list)
    assert len(outputs) == 1
    assert outputs[0]["filename"].endswith(".md")
    assert "Hello world" in outputs[0]["text"]


@pytest.mark.asyncio
async def test_document_write_xlsx_creates_file():
    import app.tools  # noqa: F401
    from app.tools.registry import execute_tool

    res = await execute_tool(
        "document_write",
        {
            "path": "__tests__/doc_tools_sheet",
            "format": "xlsx",
            "sheets": [
                {
                    "name": "Sheet1",
                    "headers": ["A", "B"],
                    "rows": [[1, 2], [3, 4]],
                }
            ],
            "overwrite": True,
        },
    )
    assert res.success, res.error
    assert res.output["path"].endswith(".xlsx")


@pytest.mark.asyncio
async def test_document_read_missing_file_fails():
    import app.tools  # noqa: F401
    from app.tools.registry import execute_tool

    res = await execute_tool("document_read", {"path": "__tests__/does_not_exist.docx"})
    assert not res.success
    assert "File not found" in (res.error or "")
