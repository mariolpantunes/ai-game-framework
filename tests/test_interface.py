import pytest
from typing import Dict, Any
from framework.interface import GameInterface, GameState

class MockGame(GameInterface):
    def __init__(self):
        super().__init__()
        self.players = []
        self.actions = []
        self.ticks = 0

    async def on_player_connect(self, player_id: int):
        self.players.append(player_id)
        if len(self.players) >= 2:
            self.state = GameState.RUNNING

    async def on_player_disconnect(self, player_id: int):
        self.players.remove(player_id)
        self.state = GameState.LOBBY

    async def process_action(self, player_id: int, action: Dict[str, Any]):
        self.actions.append((player_id, action))

    async def tick(self, dt: float):
        self.ticks += 1

    def get_state(self) -> Dict[str, Any]:
        return {"players": self.players, "ticks": self.ticks}

@pytest.mark.asyncio
async def test_game_lifecycle():
    game = MockGame()
    assert game.state == GameState.LOBBY
    
    await game.on_player_connect(1)
    assert game.state == GameState.LOBBY
    
    await game.on_player_connect(2)
    assert game.state == GameState.RUNNING
    
    await game.tick(0.1)
    assert game.ticks == 1
    
    await game.on_player_disconnect(1)
    assert game.state == GameState.LOBBY
