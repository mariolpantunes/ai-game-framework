import os
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from enum import Enum
from typing import Any


class GameState(Enum):
    """
    Represents the high-level states of the game lifecycle.
    """
    LOBBY = 1     # Waiting for players or computing optimization
    RUNNING = 2   # Active simulation loop


class GameInterface(ABC):
    """
    Abstract Base Class for all games to be played by agents.
    Supports both real-time and discrete-time games.
    """

    def __init__(self) -> None:
        """
        Initializes the GameInterface with default LOBBY state and 30 FPS.
        """
        self.state = GameState.LOBBY
        self.is_real_time = False
        self.fps = 30
        self.maps_dir = "maps"
        self.current_map_name: str = ""

    @abstractmethod
    async def on_player_connect(self, player_id: int) -> None:
        """
        Called when a new agent connects.

        Args:
            player_id (int): The unique ID assigned to the connecting player.
        """
        pass

    @abstractmethod
    async def on_player_disconnect(self, player_id: int) -> None:
        """
        Called when an agent disconnects.

        Args:
            player_id (int): The ID of the disconnecting player.
        """
        pass

    async def on_handshake(self, player_id: int, data: dict[str, Any]) -> None:
        """
        Called after the initial handshake to process metadata (mode, id, etc).

        Args:
            player_id (int): The ID of the player (0 for system/frontend).
            data (Dict[str, Any]): The handshake payload.
        """
        pass

    @abstractmethod
    async def process_action(self, player_id: int, action: dict[str, Any]) -> None:
        """
        Processes an action or command from a specific player or the system.

        Args:
            player_id (int): The ID of the player sending the action (0 for system/frontend).
            action (Dict[str, Any]): The JSON action payload.
        """
        pass

    @abstractmethod
    async def tick(self, dt: float) -> None:
        """
        Called every frame if is_real_time is True and state is RUNNING.
        Handles physics and game logic updates.

        Args:
            dt (float): The time delta since the last frame (seconds).
        """
        pass

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        """
        Returns the full game state for the frontend viewer.

        Returns:
            Dict[str, Any]: The game state dictionary.
        """
        pass

    def get_setup_payload(self) -> dict[str, Any]:
        """
        Returns metadata for initial agent setup (e.g., board size, config).

        Returns:
            Dict[str, Any]: The setup metadata.
        """
        return {}

    # --- Standardized Simulation Controls ---

    async def on_start_sim(self) -> None:
        """
        Called when a 'start_sim' action is triggered from the frontend.
        """
        self.state = GameState.RUNNING

    async def on_stop_sim(self) -> None:
        """
        Called when a 'stop_sim' action is triggered from the frontend.
        """
        self.state = GameState.LOBBY

    async def on_reset_sim(self) -> None:
        """
        Called when a 'reset_sim' action is triggered from the frontend.
        """
        self.state = GameState.LOBBY

    def load_map_data(self, map_data: dict[str, Any]) -> None:
        """
        Overridden by games with custom map level editors to load map structures.
        """
        pass

    # --- Standardized Map Operations ---

    def get_map_list(self) -> list[str]:
        """
        Natively lists all JSON map files inside the maps_dir folder.
        """
        if not os.path.exists(self.maps_dir):
            return []
        try:
            files = os.listdir(self.maps_dir)
            return sorted([f for f in files if f.endswith(".json")])
        except Exception:
            return []

    def load_map(self, filename: str) -> dict[str, Any] | None:
        """
        Loads a map's JSON dictionary from maps_dir.
        """
        if not filename.endswith(".json"):
            filename += ".json"
        path = os.path.join(self.maps_dir, filename)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                import json
                return json.load(f)
        except Exception:
            return None

    def save_map(self, filename: str, map_data: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Saves a map JSON structure inside maps_dir.
        """
        if not os.path.exists(self.maps_dir):
            try:
                os.makedirs(self.maps_dir)
            except Exception as e:
                return False, f"Could not create maps directory: {e}"

        if not filename.endswith(".json"):
            filename += ".json"
        path = os.path.join(self.maps_dir, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                import json
                json.dump(map_data, f, indent=2)
            return True, None
        except Exception as e:
            return False, str(e)


class AIGameServer(GameInterface):
    """
    A FastAPI/Flask-style decorated game server application.
    Allows developers to register game and viewer hooks using function decorators.
    """

    def __init__(self, is_real_time: bool = False, fps: int = 30, maps_dir: str = "maps") -> None:
        """
        Initializes the decorated game server.
        """
        super().__init__()
        self.is_real_time = is_real_time
        self.fps = fps
        self.maps_dir = maps_dir

        # Callback slots for decorators (named to avoid namespace conflicts with methods)
        self._connect_cb: Callable[[int], Coroutine[Any, Any, None]] | None = None
        self._disconnect_cb: Callable[[int], Coroutine[Any, Any, None]] | None = None
        self._handshake_cb: Callable[[int, dict[str, Any]], Coroutine[Any, Any, None]] | None = None
        self._action_cb: Callable[[int, dict[str, Any]], Coroutine[Any, Any, None]] | None = None
        self._tick_cb: Callable[[float], Coroutine[Any, Any, None]] | None = None
        self._get_state_cb: Callable[[], dict[str, Any]] | None = None
        self._get_setup_cb: Callable[[], dict[str, Any]] | None = None
        self._start_cb: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._stop_cb: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._reset_cb: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._load_map_cb: Callable[[dict[str, Any]], None] | None = None

    # --- Decorator Hook Registrations ---

    def on_connect(self, func):
        self._connect_cb = func
        return func

    def on_disconnect(self, func):
        self._disconnect_cb = func
        return func

    def on_player_handshake(self, func):
        self._handshake_cb = func
        return func

    def on_action(self, func):
        self._action_cb = func
        return func

    def on_tick(self, func):
        self._tick_cb = func
        return func

    def on_get_state(self, func):
        self._get_state_cb = func
        return func

    def on_get_setup(self, func):
        self._get_setup_cb = func
        return func

    def on_start(self, func):
        self._start_cb = func
        return func

    def on_stop(self, func):
        self._stop_cb = func
        return func

    def on_reset(self, func):
        self._reset_cb = func
        return func

    def on_load_map(self, func):
        self._load_map_cb = func
        return func

    # --- Callback Delegations (matching GameInterface) ---

    async def on_player_connect(self, player_id: int) -> None:
        if self._connect_cb:
            await self._connect_cb(player_id)

    async def on_player_disconnect(self, player_id: int) -> None:
        if self._disconnect_cb:
            await self._disconnect_cb(player_id)

    async def on_handshake(self, player_id: int, data: dict[str, Any]) -> None:
        if self._handshake_cb:
            await self._handshake_cb(player_id, data)
        else:
            await super().on_handshake(player_id, data)

    async def process_action(self, player_id: int, action: dict[str, Any]) -> None:
        if self._action_cb:
            await self._action_cb(player_id, action)

    async def tick(self, dt: float) -> None:
        if self._tick_cb:
            await self._tick_cb(dt)

    def get_state(self) -> dict[str, Any]:
        if self._get_state_cb:
            return self._get_state_cb()
        return {}

    def get_setup_payload(self) -> dict[str, Any]:
        if self._get_setup_cb:
            return self._get_setup_cb()
        return super().get_setup_payload()

    async def on_start_sim(self) -> None:
        if self._start_cb:
            await self._start_cb()
        else:
            await super().on_start_sim()

    async def on_stop_sim(self) -> None:
        if self._stop_cb:
            await self._stop_cb()
        else:
            await super().on_stop_sim()

    async def on_reset_sim(self) -> None:
        if self._reset_cb:
            await self._reset_cb()
        else:
            await super().on_reset_sim()

    def load_map_data(self, map_data: dict[str, Any]) -> None:
        if self._load_map_cb:
            self._load_map_cb(map_data)
        else:
            super().load_map_data(map_data)

    # --- Run Launcher ---

    def run(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        """
        Directly starts the game server instance.
        """
        from .main import run_app
        run_app(self, host, port)
