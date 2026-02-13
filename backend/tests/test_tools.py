import pytest


@pytest.mark.anyio
async def test_list_tools_endpoint():
    from app.main import app
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get("/api/v1/tools")

    # If auth enabled, the endpoint may 401.
    assert r.status_code in (200, 401)


@pytest.mark.anyio
async def test_execute_file_write_and_read():
    from app.main import app
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r0 = await client.get("/api/v1/tools")
        if r0.status_code == 401:
            pytest.skip("auth enabled")

        r = await client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "file_write", "args": {"path": "tmp/test.txt", "text": "hello"}},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

        r2 = await client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "file_read", "args": {"path": "tmp/test.txt"}},
        )
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["success"] is True
        assert "hello" in (data2["output"]["text"] or "")
