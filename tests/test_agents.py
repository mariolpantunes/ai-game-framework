import asyncio
import contextlib
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock

import websockets

from aigf.interface import AIGameServer, GameState
from aigf.main import serve_game_instance, stop_game
from aigf.manager import ConnectionManager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "examples"))


# ---- Helpers ----

async def drain(ws, timeout=0.3):
    messages = []
    with contextlib.suppress(asyncio.TimeoutError):
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
            messages.append(json.loads(msg))
    return messages


async def recv_typed(ws, msg_type, timeout=2.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise asyncio.TimeoutError(f"Timed out waiting for message type '{msg_type}'")
        msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
        data = json.loads(msg)
        if data.get("type") == msg_type:
            return data


_port_counter = 28760

def get_next_port():
    global _port_counter
    _port_counter += 1
    return _port_counter


class SimpleGame(AIGameServer):
    def __init__(self):
        super().__init__(is_real_time=False)
        self._state_data = {"board": [1, 2, 3], "turn": 0}

        @self.on_connect
        async def _connect(pid):
            pass

        @self.on_disconnect
        async def _disconnect(pid):
            pass

        @self.on_action
        async def _action(pid, act):
            self._state_data["turn"] += 1

        @self.on_get_state
        def _state():
            return dict(self._state_data)


class TestAgentCommunication(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import hangman.main as hangman_mod  # pyright: ignore[reportMissingImports]

        # Reset all hangman global state before each test
        hangman_mod.secret_word = ""
        hangman_mod.guessed_letters = []
        hangman_mod.remaining_lives = 6
        hangman_mod.game_status = "LOBBY"
        hangman_mod.players.clear()

        self.app = hangman_mod.app
        self.port = get_next_port()
        self.server_task = asyncio.create_task(serve_game_instance(self.app, "127.0.0.1", self.port))
        await asyncio.sleep(0.3)
        if self.server_task.done():
            self.server_task.result()
        self.url = f"ws://127.0.0.1:{self.port}/ws"

    async def asyncTearDown(self):
        await stop_game()
        with contextlib.suppress(Exception):
            await self.server_task

    async def test_agent_handshake_returns_setup(self):
        async with websockets.connect(self.url) as ws:
            await ws.send(json.dumps({"client": "agent", "name": "TestBot"}))
            setup = await recv_typed(ws, "setup")
            self.assertIn("player_id", setup)
            self.assertIsInstance(setup["player_id"], int)
            self.assertEqual(setup["max_lives"], 6)

    async def test_agent_receives_state_after_connect(self):
        async with websockets.connect(self.url) as ws:
            await ws.send(json.dumps({"client": "agent", "name": "TestBot"}))
            await recv_typed(ws, "setup")
            update = await recv_typed(ws, "update")
            self.assertIn("masked_word", update)
            self.assertIn("guessed_letters", update)

    async def test_agent_action_triggers_state_update(self):
        async with websockets.connect(self.url) as ws:
            await ws.send(json.dumps({"client": "agent", "name": "TestBot"}))
            await recv_typed(ws, "setup")
            await drain(ws)

            await ws.send(json.dumps({"action": "e"}))
            update = await recv_typed(ws, "update")
            self.assertIn("e", update["guessed_letters"])

    async def test_action_rejected_when_not_running(self):
        import hangman.main as hangman_mod  # pyright: ignore[reportMissingImports]
        async with websockets.connect(self.url) as ws:
            await ws.send(json.dumps({"client": "agent", "name": "TestBot"}))
            await recv_typed(ws, "setup")
            await drain(ws)

            hangman_mod.game_status = "WON"
            await ws.send(json.dumps({"action": "z"}))
            update = await recv_typed(ws, "update")
            self.assertNotIn("z", update["guessed_letters"])

    async def test_broadcast_to_all_agents_on_action(self):
        async with (
            websockets.connect(self.url) as ws1,
            websockets.connect(self.url) as ws2,
        ):
            await ws1.send(json.dumps({"client": "agent", "name": "Bot1"}))
            await recv_typed(ws1, "setup")

            await ws2.send(json.dumps({"client": "agent", "name": "Bot2"}))
            await recv_typed(ws2, "setup")

            await drain(ws1)
            await drain(ws2)

            await ws1.send(json.dumps({"action": "s"}))
            u1 = await recv_typed(ws1, "update")
            u2 = await recv_typed(ws2, "update")

            self.assertIn("s", u1["guessed_letters"])
            self.assertIn("s", u2["guessed_letters"])

    async def test_agent_notified_on_peer_disconnect(self):
        ws1 = await websockets.connect(self.url)
        ws2 = await websockets.connect(self.url)
        try:
            await ws1.send(json.dumps({"client": "agent", "name": "Bot1"}))
            await recv_typed(ws1, "setup")

            await ws2.send(json.dumps({"client": "agent", "name": "Bot2"}))
            await recv_typed(ws2, "setup")

            await drain(ws1)
            await drain(ws2)

            await ws2.close()
            await asyncio.sleep(0.2)

            update = await recv_typed(ws1, "update", timeout=2.0)
            self.assertEqual(update["type"], "update")
        finally:
            with contextlib.suppress(Exception):
                await ws1.close()
            with contextlib.suppress(Exception):
                await ws2.close()

    async def test_sequential_player_ids(self):
        ids = []
        for i in range(3):
            async with websockets.connect(self.url) as ws:
                await ws.send(json.dumps({"client": "agent", "name": f"Bot{i}"}))
                setup = await recv_typed(ws, "setup")
                ids.append(setup["player_id"])
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(ids, sorted(ids))

    async def test_frontend_action_broadcasts_to_agents(self):
        async with (
            websockets.connect(self.url) as ws_agent,
            websockets.connect(self.url) as ws_front,
        ):
            await ws_agent.send(json.dumps({"client": "agent", "name": "Bot"}))
            await recv_typed(ws_agent, "setup")
            await drain(ws_agent)

            await ws_front.send(json.dumps({"client": "frontend"}))
            await drain(ws_agent)
            await drain(ws_front)

            await ws_front.send(json.dumps({"action": "some_custom_action"}))
            update = await recv_typed(ws_agent, "update", timeout=2.0)
            self.assertEqual(update["type"], "update")

    async def test_frontend_reset_sends_reset_to_agents(self):
        async with (
            websockets.connect(self.url) as ws_agent,
            websockets.connect(self.url) as ws_front,
        ):
            await ws_agent.send(json.dumps({"client": "agent", "name": "Bot"}))
            await recv_typed(ws_agent, "setup")

            await ws_front.send(json.dumps({"client": "frontend"}))
            await drain(ws_agent)
            await drain(ws_front)

            await ws_front.send(json.dumps({"action": "reset_sim"}))
            reset_msg = await recv_typed(ws_agent, "reset", timeout=2.0)
            self.assertEqual(reset_msg["type"], "reset")

    async def test_invalid_client_type_rejected(self):
        async with websockets.connect(self.url) as ws:
            await ws.send(json.dumps({"client": "unknown_type"}))
            try:
                await asyncio.wait_for(ws.recv(), timeout=2.0)
                self.fail("Should have been disconnected")
            except websockets.exceptions.ConnectionClosed as e:
                code = getattr(e, "code", None) or getattr(ws, "close_code", None)
                self.assertEqual(code, 1008)

    async def test_handshake_failure_does_not_leak_connection(self):
        class BadHandshakeGame(SimpleGame):
            async def on_handshake(self, player_id, data):
                raise ValueError("Handshake failed maliciously")

        game = BadHandshakeGame()
        port = get_next_port()
        server_task = asyncio.create_task(serve_game_instance(game, "127.0.0.1", port))
        await asyncio.sleep(0.2)
        if server_task.done():
            server_task.result()

        try:
            url = f"ws://127.0.0.1:{port}/ws"
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps({"client": "agent", "name": "EvilBot"}))
                with contextlib.suppress(Exception):
                    await ws.recv()

            import aigf.main as main_mod
            self.assertIsNotNone(main_mod.manager)
            if main_mod.manager is not None:
                self.assertEqual(len(main_mod.manager.agent_wss), 0)
        finally:
            await stop_game()
            with contextlib.suppress(Exception):
                await server_task

    async def test_load_map_resets_simulation_state(self):
        class MapResetGame(SimpleGame):
            def __init__(self):
                super().__init__()
                self.state = GameState.RUNNING
                self.maps_dir = tempfile.mkdtemp()
                self.map_file = os.path.join(self.maps_dir, "test_map.json")
                with open(self.map_file, "w") as f:
                    json.dump({"layout": []}, f)

            def load_map_data(self, data):
                pass

        game = MapResetGame()
        port = get_next_port()
        server_task = asyncio.create_task(serve_game_instance(game, "127.0.0.1", port))
        await asyncio.sleep(0.2)
        if server_task.done():
            server_task.result()

        try:
            url = f"ws://127.0.0.1:{port}/ws"
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps({"client": "frontend"}))
                game.state = GameState.RUNNING

                await ws.send(json.dumps({"action": "load_map", "filename": "test_map.json"}))
                await asyncio.sleep(0.2)

                self.assertEqual(game.state, GameState.LOBBY)
        finally:
            await stop_game()
            with contextlib.suppress(Exception):
                await server_task
            with contextlib.suppress(Exception):
                os.remove(game.map_file)
                os.rmdir(game.maps_dir)

    async def test_real_time_loop_maintains_fps(self):
        class SlowGame(SimpleGame):
            def __init__(self):
                super().__init__()
                self.is_real_time = True
                self.fps = 10
                self.state = GameState.RUNNING

            async def tick(self, dt):
                await asyncio.sleep(0.04)

        game = SlowGame()

        sleep_calls = []
        original_sleep = asyncio.sleep

        async def mock_sleep(delay, result=None):
            sleep_calls.append(delay)
            await original_sleep(delay, result)

        port = get_next_port()
        server_task = asyncio.create_task(serve_game_instance(game, "127.0.0.1", port))
        await asyncio.sleep(0.2)
        if server_task.done():
            server_task.result()

        import unittest.mock as mock
        with mock.patch("asyncio.sleep", new=mock_sleep):
            await original_sleep(0.4)

        try:
            self.assertTrue(len(sleep_calls) >= 2)
            for s in sleep_calls:
                self.assertTrue(0.03 <= s <= 0.09, f"Expected sleep around 0.06s, got {s}")
        finally:
            await stop_game()
            with contextlib.suppress(Exception):
                await server_task


class TestAgentManagerUnit(unittest.IsolatedAsyncioTestCase):
    async def test_broadcast_agents_sends_game_state(self):
        game = SimpleGame()
        mgr = ConnectionManager(game)

        agents = [AsyncMock() for _ in range(4)]
        for a in agents:
            await mgr.connect_agent(a)

        await mgr.broadcast_agents()

        for a in agents:
            self.assertEqual(a.send.call_count, 1)
            payload = json.loads(a.send.call_args[0][0])
            self.assertEqual(payload["type"], "update")
            self.assertEqual(payload["board"], [1, 2, 3])
            self.assertEqual(payload["turn"], 0)

    async def test_broadcast_agents_no_framework_metadata(self):
        game = SimpleGame()
        mgr = ConnectionManager(game)

        ws = AsyncMock()
        await mgr.connect_agent(ws)

        await mgr.broadcast_agents()

        payload = json.loads(ws.send.call_args[0][0])
        self.assertNotIn("_framework", payload)

    async def test_broadcast_frontend_includes_framework_metadata(self):
        game = SimpleGame()
        mgr = ConnectionManager(game)

        ws_front = AsyncMock()
        ws_agent = AsyncMock()

        await mgr.connect_agent(ws_agent)
        await mgr.connect_frontend(ws_front)

        ws_front.send.reset_mock()
        await mgr.broadcast_frontend()

        payload = json.loads(ws_front.send.call_args[0][0])
        fw = payload["_framework"]
        self.assertIn(1, fw["agents"])
        self.assertEqual(fw["state"], "LOBBY")
        self.assertIsInstance(fw["maps"], list)

    async def test_broadcast_all_reaches_everyone(self):
        game = SimpleGame()
        mgr = ConnectionManager(game)

        ws_front = AsyncMock()
        ws_a1 = AsyncMock()
        ws_a2 = AsyncMock()

        await mgr.connect_frontend(ws_front)
        await mgr.connect_agent(ws_a1)
        await mgr.connect_agent(ws_a2)

        for ws in [ws_front, ws_a1, ws_a2]:
            ws.send.reset_mock()

        await mgr.broadcast_all()

        for ws in [ws_front, ws_a1, ws_a2]:
            self.assertEqual(ws.send.call_count, 1)

    async def test_send_agent_state_targets_single_agent(self):
        game = SimpleGame()
        mgr = ConnectionManager(game)

        ws1 = AsyncMock()
        ws2 = AsyncMock()

        id1 = await mgr.connect_agent(ws1)
        _ = await mgr.connect_agent(ws2)

        ws1.send.reset_mock()
        ws2.send.reset_mock()

        await mgr.send_agent_state(id1, {"custom": "data"})

        self.assertEqual(ws1.send.call_count, 1)
        self.assertEqual(ws2.send.call_count, 0)

        payload = json.loads(ws1.send.call_args[0][0])
        self.assertEqual(payload["type"], "update")
        self.assertEqual(payload["custom"], "data")

    async def test_broadcast_skips_disconnected_agents(self):
        game = SimpleGame()
        mgr = ConnectionManager(game)

        ws1 = AsyncMock()
        ws2 = AsyncMock()

        id1 = await mgr.connect_agent(ws1)
        _ = await mgr.connect_agent(ws2)

        await mgr.disconnect_agent(id1)

        ws1.send.reset_mock()
        ws2.send.reset_mock()

        await mgr.broadcast_agents()

        self.assertEqual(ws1.send.call_count, 0)
        self.assertEqual(ws2.send.call_count, 1)

    async def test_broadcast_resilient_to_broken_socket(self):
        game = SimpleGame()
        mgr = ConnectionManager(game)

        ws_good1 = AsyncMock()
        ws_broken = AsyncMock()
        ws_broken.send.side_effect = Exception("Connection reset")
        ws_good2 = AsyncMock()

        await mgr.connect_agent(ws_good1)
        await mgr.connect_agent(ws_broken)
        await mgr.connect_agent(ws_good2)

        await mgr.broadcast_agents()

        self.assertEqual(ws_good1.send.call_count, 1)
        self.assertEqual(ws_good2.send.call_count, 1)


class TestStaticFileUnit(unittest.TestCase):
    def test_find_static_file_prevents_partial_prefix_traversal(self):
        import shutil
        import tempfile
        from unittest.mock import patch

        from aigf.main import find_static_file

        tmp_dir = tempfile.mkdtemp()
        app_dir = os.path.join(tmp_dir, "app")
        sibling_dir = os.path.join(tmp_dir, "app-sibling")

        os.mkdir(app_dir)
        os.mkdir(sibling_dir)

        secret_file = os.path.join(sibling_dir, "secret.txt")
        with open(secret_file, "w") as f:
            f.write("classified info")

        try:
            with patch("os.getcwd", return_value=app_dir):
                result = find_static_file("../app-sibling/secret.txt")
                self.assertIsNone(result)
        finally:
            shutil.rmtree(tmp_dir)
