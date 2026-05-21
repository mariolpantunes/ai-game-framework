from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict


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

    @abstractmethod
    async def process_action(self, player_id: int, action: Dict[str, Any]) -> None:
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
    def get_state(self) -> Dict[str, Any]:
        """
        Returns the full game state for the frontend viewer.
        
        Returns:
            Dict[str, Any]: The game state dictionary.
        """
        pass

    def get_setup_payload(self) -> Dict[str, Any]:
        """
        Returns metadata for initial agent setup (e.g., board size, config).
        
        Returns:
            Dict[str, Any]: The setup metadata.
        """
        return {}
