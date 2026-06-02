import json
from unittest.mock import AsyncMock

import pytest

from aigf.interface import GameInterface
from aigf.manager import ConnectionManager


class MockGame(GameInterface):
    async def on_player_connect(self, player_id): pass
    async def on_player_disconnect(self, player_id): pass
    async def process_action(self, player_id, action): pass
    async def tick(self, dt): pass
    def get_state(self): return {"test": "data"}

@pytest.mark.asyncio
async def test_connection_manager():
    game = MockGame()
    manager = ConnectionManager(game)

    # Mock WebSocket
    ws = AsyncMock()
    ws.send = AsyncMock()

    # Test Frontend Connection
    await manager.connect_frontend(ws)
    assert manager.frontend_ws == ws
    ws.send.assert_called()

    # Test Agent Connection
    ws_agent = AsyncMock()
    player_id = await manager.connect_agent(ws_agent)
    assert player_id == 1
    assert manager.agent_wss[1] == ws_agent

    # Test Broadcast
    await manager.broadcast_frontend()
    # Check if send was called with _framework metadata
    last_call = ws.send.call_args[0][0]
    if isinstance(last_call, bytes):
        last_call = last_call.decode("utf-8")
    data = json.loads(last_call)

    assert "_framework" in data
    assert data["_framework"]["agents"] == [1]

    # Test Disconnect
    await manager.disconnect_agent(1)
    assert 1 not in manager.agent_wss

@pytest.mark.asyncio
async def test_connection_manager_extended():
    game = MockGame()
    manager = ConnectionManager(game)

    # 1. Connect multiple agents sequentially
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    ws3 = AsyncMock()

    id1 = await manager.connect_agent(ws1)
    id2 = await manager.connect_agent(ws2)
    id3 = await manager.connect_agent(ws3)

    assert id1 == 1
    assert id2 == 2
    assert id3 == 3
    assert len(manager.agent_wss) == 3

    # 2. Test frontend disconnect
    ws_front = AsyncMock()
    await manager.connect_frontend(ws_front)
    assert manager.frontend_ws == ws_front
    await manager.disconnect_frontend()
    assert manager.frontend_ws is None

    # 3. Test exception resilience when a socket send fails
    ws_broken = AsyncMock()
    ws_broken.send.side_effect = Exception("Connection lost")
    await manager.connect_frontend(ws_broken)
    # This broadcast should handle the exception gracefully without throwing
    await manager.broadcast_frontend()

