import asyncio
import contextlib
import http.client
import json
import os
import unittest

import websockets

from aigf.main import serve_game, stop_game

_port_counter = 28780

def get_next_port():
    global _port_counter
    _port_counter += 1
    return _port_counter


class TestLoader(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        os.environ["GAME_CLASS"] = "tests.test_interface.MockGame"
        self.port = get_next_port()
        # Run serve_game in a background task
        self.server_task = asyncio.create_task(serve_game("127.0.0.1", self.port))
        # Give the server a small moment to start up
        await asyncio.sleep(0.2)
        if self.server_task.done():
            self.server_task.result()
        self.uri = f"ws://127.0.0.1:{self.port}/ws"

    async def asyncTearDown(self):
        await stop_game()
        with contextlib.suppress(Exception):
            await self.server_task

    async def test_root_endpoint(self):
        loop = asyncio.get_running_loop()
        def get_url():
            conn = http.client.HTTPConnection("127.0.0.1", self.port)
            conn.request("GET", "/")
            response = conn.getresponse()
            body = response.read()
            status = response.status
            conn.close()
            return body, status

        body, status = await loop.run_in_executor(None, get_url)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "running")
        self.assertTrue(data["game_loaded"])

    async def test_static_file_serving(self):
        loop = asyncio.get_running_loop()
        def get_file():
            conn = http.client.HTTPConnection("127.0.0.1", self.port)
            conn.request("GET", "/framework/nord.css")
            response = conn.getresponse()
            body = response.read()
            status = response.status
            content_type = response.getheader("Content-Type")
            conn.close()
            return body, status, content_type

        body, status, mime = await loop.run_in_executor(None, get_file)
        self.assertEqual(status, 200)
        self.assertIn(b"Nord Color Palette", body)
        self.assertIsNotNone(mime)
        assert mime is not None
        self.assertIn("text/css", mime)

    async def test_api_maps(self):
        loop = asyncio.get_running_loop()
        def get_maps():
            conn = http.client.HTTPConnection("127.0.0.1", self.port)
            conn.request("GET", "/api/maps")
            response = conn.getresponse()
            body = response.read()
            status = response.status
            conn.close()
            return body, status

        body, status = await loop.run_in_executor(None, get_maps)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("maps", data)
        self.assertIsInstance(data["maps"], list)

    async def test_websocket_invalid_client(self):
        async with websockets.connect(self.uri) as websocket:
            await websocket.send(json.dumps({"client": "invalid"}))
            try:
                await websocket.recv()
                self.fail("Should have disconnected for invalid client type")
            except websockets.exceptions.ConnectionClosed as e:
                code = getattr(e, "code", None) or getattr(websocket, "close_code", None)
                self.assertEqual(code, 1008)
