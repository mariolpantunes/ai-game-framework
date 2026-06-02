import asyncio
import contextlib
import http.client
import json
import os

import pytest
import pytest_asyncio
import websockets

from aigf.main import serve_game, stop_game


@pytest_asyncio.fixture(autouse=True)
async def test_server():
    os.environ["GAME_CLASS"] = "tests.test_interface.MockGame"
    # Run serve_game in a background task
    server_task = asyncio.create_task(serve_game("127.0.0.1", 8766))
    # Give the server a small moment to start up
    await asyncio.sleep(0.2)
    yield "ws://127.0.0.1:8766/ws"
    await stop_game()
    with contextlib.suppress(Exception):
        await server_task

@pytest.mark.asyncio
async def test_root_endpoint():
    loop = asyncio.get_running_loop()
    def get_url():
        conn = http.client.HTTPConnection("127.0.0.1", 8766)
        conn.request("GET", "/")
        response = conn.getresponse()
        body = response.read()
        status = response.status
        conn.close()
        return body, status

    body, status = await loop.run_in_executor(None, get_url)
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["status"] == "running"
    assert data["game_loaded"] is True

@pytest.mark.asyncio
async def test_static_file_serving():
    loop = asyncio.get_running_loop()
    def get_file():
        conn = http.client.HTTPConnection("127.0.0.1", 8766)
        conn.request("GET", "/framework/nord.css")
        response = conn.getresponse()
        body = response.read()
        status = response.status
        content_type = response.getheader("Content-Type")
        conn.close()
        return body, status, content_type

    body, status, mime = await loop.run_in_executor(None, get_file)
    assert status == 200
    assert b"Nord Color Palette" in body
    assert mime is not None and "text/css" in mime

@pytest.mark.asyncio
async def test_api_maps():
    loop = asyncio.get_running_loop()
    def get_maps():
        conn = http.client.HTTPConnection("127.0.0.1", 8766)
        conn.request("GET", "/api/maps")
        response = conn.getresponse()
        body = response.read()
        status = response.status
        conn.close()
        return body, status

    body, status = await loop.run_in_executor(None, get_maps)
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert "maps" in data
    assert isinstance(data["maps"], list)

@pytest.mark.asyncio
async def test_websocket_invalid_client(test_server):
    uri = test_server
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"client": "invalid"}))
        try:
            await websocket.recv()
            raise AssertionError("Should have disconnected for invalid client type")
        except websockets.exceptions.ConnectionClosed as e:
            assert e.code == 1008
