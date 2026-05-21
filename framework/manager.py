import logging
from typing import Dict, Optional, Any

from fastapi import WebSocket

from .interface import GameInterface

logging.basicConfig(level=logging.INFO, format="%(asctime)s - FRAMEWORK - %(levelname)s - %(message)s")


class ConnectionManager:
    """
    Manages WebSocket connections for a game.
    Supports a dynamic number of agents and exactly one frontend.
    """

    def __init__(self, game: GameInterface) -> None:
        """
        Initializes the ConnectionManager.

        Args:
            game (GameInterface): The game instance to bind to.
        """
        self.game = game
        self.frontend_ws: Optional[WebSocket] = None
        self.agent_wss: Dict[int, WebSocket] = {}
        self.next_player_id = 1

    async def connect_frontend(self, websocket: WebSocket) -> None:
        """
        Connects a frontend visualization client.

        Args:
            websocket (WebSocket): The frontend WebSocket.
        """
        await websocket.accept()
        self.frontend_ws = websocket
        logging.info("Frontend connected.")
        await self.broadcast_frontend()

    async def disconnect_frontend(self) -> None:
        """
        Disconnects the frontend visualization client.
        """
        self.frontend_ws = None
        logging.info("Frontend disconnected.")

    async def connect_agent(self, websocket: WebSocket) -> int:
        """
        Connects a new agent client and assigns a unique player ID.

        Args:
            websocket (WebSocket): The agent WebSocket.

        Returns:
            int: The assigned player ID.
        """
        player_id = self.next_player_id
        self.next_player_id += 1
        
        self.agent_wss[player_id] = websocket
        logging.info(f"Agent {player_id} connected.")
        await self.game.on_player_connect(player_id)
        return player_id

    async def disconnect_agent(self, player_id: int) -> None:
        """
        Disconnects an agent client.

        Args:
            player_id (int): The ID of the player to disconnect.
        """
        if player_id in self.agent_wss:
            del self.agent_wss[player_id]
            logging.info(f"Agent {player_id} disconnected.")
            await self.game.on_player_disconnect(player_id)

    async def broadcast_frontend(self) -> None:
        """
        Broadcasts the current game state and framework metadata to the frontend.
        """
        if self.frontend_ws:
            state = self.game.get_state()
            # Inject framework metadata
            state["_framework"] = {
                "agents": list(self.agent_wss.keys()),
                "state": self.game.state.name
            }
            try:
                await self.frontend_ws.send_json({"type": "update", **state})
            except Exception as e:
                logging.error(f"Error broadcasting to frontend: {e}")

    async def send_agent_state(self, player_id: int, state: Dict[str, Any]) -> None:
        """
        Sends a specific state update to a single agent.

        Args:
            player_id (int): The target player ID.
            state (Dict[str, Any]): The state data to send.
        """
        if player_id in self.agent_wss:
            try:
                await self.agent_wss[player_id].send_json({"type": "state", **state})
            except Exception as e:
                logging.error(f"Error sending state to Agent {player_id}: {e}")

    async def broadcast_all(self) -> None:
        """
        Convenience method to update the frontend. 
        Agent updates are typically managed individually by the game logic.
        """
        await self.broadcast_frontend()
