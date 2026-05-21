import pytest
from unittest.mock import AsyncMock
from framework.manager import ConnectionManager
from framework.interface import GameInterface

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
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    
    # Test Frontend Connection
    await manager.connect_frontend(ws)
    assert manager.frontend_ws == ws
    ws.accept.assert_called_once()
    ws.send_json.assert_called()
    
    # Test Agent Connection
    ws_agent = AsyncMock()
    player_id = await manager.connect_agent(ws_agent)
    assert player_id == 1
    assert manager.agent_wss[1] == ws_agent
    
    # Test Broadcast
    await manager.broadcast_frontend()
    # Check if send_json was called with _framework metadata
    last_call = ws.send_json.call_args[0][0]
    assert "_framework" in last_call
    assert last_call["_framework"]["agents"] == [1]
    
    # Test Disconnect
    await manager.disconnect_agent(1)
    assert 1 not in manager.agent_wss
