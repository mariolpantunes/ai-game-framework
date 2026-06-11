import shutil
import tempfile
import unittest
from typing import Any

from aigf.interface import GameInterface, GameState


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

    async def process_action(self, player_id: int, action: dict[str, Any]):
        self.actions.append((player_id, action))

    async def tick(self, dt: float):
        self.ticks += 1

    def get_state(self) -> dict[str, Any]:
        return {"players": self.players, "ticks": self.ticks}


class TestGameInterface(unittest.IsolatedAsyncioTestCase):
    async def test_game_lifecycle(self):
        game = MockGame()
        self.assertEqual(game.state, GameState.LOBBY)

        await game.on_player_connect(1)
        self.assertEqual(game.state, GameState.LOBBY)

        await game.on_player_connect(2)
        self.assertEqual(game.state, GameState.RUNNING)

        await game.tick(0.1)
        self.assertEqual(game.ticks, 1)

        await game.on_player_disconnect(1)
        self.assertEqual(game.state, GameState.LOBBY)

    def test_map_operations(self):
        game = MockGame()
        tmp_dir = tempfile.mkdtemp()
        game.maps_dir = tmp_dir

        try:
            map_data = {"width": 800, "height": 600, "obstacles": [1, 2, 3]}
            success, err = game.save_map("level1", map_data)
            self.assertTrue(success)
            self.assertIsNone(err)

            maps = game.get_map_list()
            self.assertEqual(maps, ["level1.json"])

            loaded = game.load_map("level1.json")
            self.assertEqual(loaded, map_data)

            non_existent = game.load_map("void")
            self.assertIsNone(non_existent)
        finally:
            shutil.rmtree(tmp_dir)
