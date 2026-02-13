import pytest


@pytest.mark.anyio
async def test_shell_exec_tool_smoke():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r0 = await client.get("/api/v1/tools")
        if r0.status_code == 401:
            pytest.skip("auth enabled")

        r = await client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "shell_exec", "args": {"command": "echo hello"}},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["tool_name"] == "shell_exec"
        assert data["success"] is True


@pytest.mark.anyio
async def test_shell_exec_tool_allows_cwd_in_workspace():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r0 = await client.get("/api/v1/tools")
        if r0.status_code == 401:
            pytest.skip("auth enabled")

        # Create a subdir via file_write
        r1 = await client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "file_write", "args": {"path": "subdir/hello.txt", "content": "x"}},
        )
        assert r1.status_code == 200

        r2 = await client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "shell_exec", "args": {"command": "echo cwd-ok", "cwd": "subdir"}},
        )
        assert r2.status_code == 200
        data = r2.json()
        assert data["success"] is True


@pytest.mark.anyio
async def test_shell_exec_tool_blocks_rm():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r0 = await client.get("/api/v1/tools")
        if r0.status_code == 401:
            pytest.skip("auth enabled")

        r = await client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "shell_exec", "args": {"command": "rm -rf /"}},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False
        assert "blocked" in (data.get("error") or "").lower()
