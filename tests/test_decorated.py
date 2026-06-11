import unittest
from typing import Any

from aigf.interface import AIGameServer, GameState


class TestDecoratedGame(unittest.IsolatedAsyncioTestCase):
    async def test_decorated_game_lifecycle(self):
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
        self.assertEqual(app.state, GameState.LOBBY)
        self.assertTrue(app.is_real_time)
        self.assertEqual(app.fps, 30)

        # Test decorated connect
        await app.on_player_connect(1)
        self.assertEqual(players, [1])
        self.assertEqual(app.state, GameState.LOBBY)

        await app.on_player_connect(2)
        self.assertEqual(players, [1, 2])
        self.assertEqual(app.state, GameState.RUNNING)

        # Test decorated action
        await app.process_action(2, {"action": "move"})
        self.assertEqual(actions, [(2, {"action": "move"})])

        # Test decorated tick
        await app.tick(0.1)
        self.assertEqual(ticks, 1)

        # Test decorated state
        res = app.get_state()
        self.assertTrue(state_call)
        self.assertEqual(res, {"players": [1, 2], "ticks": 1})

        # Test decorated disconnect
        await app.on_player_disconnect(1)
        self.assertEqual(players, [2])
        self.assertEqual(app.state, GameState.LOBBY)
