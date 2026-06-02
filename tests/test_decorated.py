from typing import Any

import pytest

from aigf.interface import AIGameServer, GameState


@pytest.mark.asyncio
async def test_decorated_game_lifecycle():
    app = AIGameServer(is_real_time=True, fps=30)

    players = []
    actions = []
    ticks = 0
    state_call = False

    @app.on_connect
    async def connect(player_id: int):
        players.append(player_id)
        if len(players) >= 2:
            app.state = GameState.RUNNING

    @app.on_disconnect
    async def disconnect(player_id: int):
        players.remove(player_id)
        app.state = GameState.LOBBY

    @app.on_action
    async def action(player_id: int, act: dict[str, Any]):
        actions.append((player_id, act))

    @app.on_tick
    async def tick(dt: float):
        nonlocal ticks
        ticks += 1

    @app.on_get_state
    def get_state() -> dict[str, Any]:
        nonlocal state_call
        state_call = True
        return {"players": players, "ticks": ticks}

    # Verify initial state
    assert app.state == GameState.LOBBY
    assert app.is_real_time is True
    assert app.fps == 30

    # Test decorated connect
    await app.on_player_connect(1)
    assert players == [1]
    assert app.state == GameState.LOBBY

    await app.on_player_connect(2)
    assert players == [1, 2]
    assert app.state == GameState.RUNNING

    # Test decorated action
    await app.process_action(2, {"action": "move"})
    assert actions == [(2, {"action": "move"})]

    # Test decorated tick
    await app.tick(0.1)
    assert ticks == 1

    # Test decorated state
    res = app.get_state()
    assert state_call is True
    assert res == {"players": [1, 2], "ticks": 1}

    # Test decorated disconnect
    await app.on_player_disconnect(1)
    assert players == [2]
    assert app.state == GameState.LOBBY
