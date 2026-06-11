import json
import unittest
from unittest.mock import AsyncMock

from aigf.interface import GameInterface
from aigf.manager import ConnectionManager


class MockGame(GameInterface):
    async def on_player_connect(self, player_id): pass
    async def on_player_disconnect(self, player_id): pass
    async def process_action(self, player_id, action): pass
    async def tick(self, dt): pass
    def get_state(self): return {"test": "data"}


class TestConnectionManager(unittest.IsolatedAsyncioTestCase):
    async def test_connection_manager(self):
        game = MockGame()
        manager = ConnectionManager(game)

        # Mock WebSocket
        ws = AsyncMock()
        ws.send = AsyncMock()

        # Test Frontend Connection
        await manager.connect_frontend(ws)
        self.assertEqual(manager.frontend_ws, ws)

        await manager.broadcast_frontend()
        ws.send.assert_called()

        # Test Agent Connection
        ws_agent = AsyncMock()
        player_id = await manager.connect_agent(ws_agent)
        self.assertEqual(player_id, 1)
        self.assertEqual(manager.agent_wss[1], ws_agent)

        # Test Broadcast
        await manager.broadcast_frontend()
        last_call = ws.send.call_args[0][0]
        if isinstance(last_call, bytes):
            last_call = last_call.decode("utf-8")
        data = json.loads(last_call)

        self.assertIn("_framework", data)
        self.assertEqual(data["_framework"]["agents"], [1])

        # Test Disconnect
        await manager.disconnect_agent(1)
        self.assertNotIn(1, manager.agent_wss)

    async def test_connection_manager_extended(self):
        game = MockGame()
        manager = ConnectionManager(game)

        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        id1 = await manager.connect_agent(ws1)
        id2 = await manager.connect_agent(ws2)
        id3 = await manager.connect_agent(ws3)

        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)
        self.assertEqual(id3, 3)
        self.assertEqual(len(manager.agent_wss), 3)

        ws_front = AsyncMock()
        await manager.connect_frontend(ws_front)
        self.assertEqual(manager.frontend_ws, ws_front)
        await manager.disconnect_frontend()
        self.assertIsNone(manager.frontend_ws)

        ws_broken = AsyncMock()
        ws_broken.send.side_effect = Exception("Connection lost")
        await manager.connect_frontend(ws_broken)
        await manager.broadcast_frontend()

    async def test_broadcast_agents(self):
        game = MockGame()
        manager = ConnectionManager(game)

        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await manager.connect_agent(ws1)
        await manager.connect_agent(ws2)
        await manager.connect_agent(ws3)

        await manager.broadcast_agents()

        for ws in [ws1, ws2, ws3]:
            ws.send.assert_called()
            last_call = ws.send.call_args[0][0]
            if isinstance(last_call, bytes):
                last_call = last_call.decode("utf-8")
            data = json.loads(last_call)
            self.assertEqual(data["type"], "update")
            self.assertEqual(data["test"], "data")

    async def test_broadcast_all(self):
        game = MockGame()
        manager = ConnectionManager(game)

        ws_front = AsyncMock()
        ws_agent = AsyncMock()

        await manager.connect_frontend(ws_front)
        ws_front.send.reset_mock()

        await manager.connect_agent(ws_agent)
        ws_agent.send.reset_mock()

        await manager.broadcast_all()
        ws_front.send.assert_called_once()
        ws_agent.send.assert_called_once()

        agent_msg = ws_agent.send.call_args[0][0]
        if isinstance(agent_msg, bytes):
            agent_msg = agent_msg.decode("utf-8")
        agent_data = json.loads(agent_msg)
        self.assertEqual(agent_data["type"], "update")
        self.assertEqual(agent_data["test"], "data")

        front_msg = ws_front.send.call_args[0][0]
        if isinstance(front_msg, bytes):
            front_msg = front_msg.decode("utf-8")
        front_data = json.loads(front_msg)
        self.assertEqual(front_data["type"], "update")
        self.assertIn("_framework", front_data)

    async def test_broadcast_agents_handles_broken_socket(self):
        game = MockGame()
        manager = ConnectionManager(game)

        ws_good = AsyncMock()
        ws_broken = AsyncMock()
        ws_broken.send.side_effect = Exception("Connection lost")

        await manager.connect_agent(ws_good)
        await manager.connect_agent(ws_broken)

        await manager.broadcast_agents()
        ws_good.send.assert_called()
