import asyncio
import importlib
import logging
import os
import time
from typing import Optional, Any, Dict

import orjson
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from .interface import GameInterface, GameState
from .manager import ConnectionManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - SERVER - %(levelname)s - %(message)s")


class ORJSONResponse(Response):
    """
    Fast JSON response using the orjson library.
    """
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        """
        Renders the content using orjson.
        
        Args:
            content (Any): The content to serialize.
            
        Returns:
            bytes: The serialized JSON bytes.
        """
        return orjson.dumps(content)


app = FastAPI(default_response_class=ORJSONResponse)

# Global game and manager instances
game_instance: Optional[GameInterface] = None
manager: Optional[ConnectionManager] = None


def load_game() -> None:
    """
    Dynamically loads the game class specified in the GAME_CLASS environment variable.
    The format should be 'package.module.ClassName'.
    """
    global game_instance, manager
    game_class_path = os.getenv("GAME_CLASS")
    if not game_class_path:
        logging.error("GAME_CLASS environment variable not set.")
        return

    try:
        module_path, class_name = game_class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        game_class = getattr(module, class_name)
        game_instance = game_class()
        if game_instance:
            manager = ConnectionManager(game_instance)
            logging.info(f"Successfully loaded game: {game_class_path}")
    except Exception as e:
        logging.error(f"Failed to load game class {game_class_path}: {e}")


@app.on_event("startup")
async def startup_event() -> None:
    """
    FastAPI startup event. Loads the game and starts the real-time loop if applicable.
    """
    load_game()
    if game_instance and game_instance.is_real_time:
        asyncio.create_task(game_loop())


async def game_loop() -> None:
    """
    Main loop for real-time games. Runs at the FPS specified in the game instance.
    """
    if not game_instance:
        return
        
    logging.info("Starting real-time game loop.")
    dt = 1.0 / game_instance.fps
    while True:
        start_time = time.perf_counter()
        if game_instance.state == GameState.RUNNING:
            await game_instance.tick(dt)
            if manager:
                await manager.broadcast_frontend()
        
        # Calculate sleep to maintain FPS
        elapsed = time.perf_counter() - start_time
        sleep_time = max(0, dt - elapsed)
        await asyncio.sleep(sleep_time)


@app.get("/")
async def root() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Dict[str, Any]: Status and game loading information.
    """
    return {"status": "running", "game_loaded": game_instance is not None}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for both frontend and agent clients.
    Handles the initial handshake and routes messages accordingly.
    
    Args:
        websocket (WebSocket): The connecting WebSocket.
    """
    if manager is None or game_instance is None:
        await websocket.close(code=1011, reason="Game not initialized")
        return

    await websocket.accept()
    try:
        # Initial handshake to identify client type
        data = await websocket.receive_json()
        client_type = data.get("client")

        if client_type == "frontend":
            await manager.connect_frontend(websocket)
            try:
                while True:
                    # Frontend might send commands (e.g., reset, start)
                    msg = await websocket.receive_json()
                    await game_instance.process_action(0, msg)  # 0 for system actions
                    await manager.broadcast_frontend()
            except WebSocketDisconnect:
                await manager.disconnect_frontend()

        elif client_type == "agent":
            player_id = await manager.connect_agent(websocket)
            
            # Send initial setup
            setup_data = {
                "type": "setup",
                "player_id": player_id,
                **game_instance.get_setup_payload()
            }
            await websocket.send_json(setup_data)
            await manager.broadcast_frontend()

            try:
                while True:
                    action = await websocket.receive_json()
                    if game_instance.state == GameState.RUNNING:
                        await game_instance.process_action(player_id, action)
                        # For discrete games, we might want to broadcast after every action
                        if not game_instance.is_real_time:
                            await manager.broadcast_frontend()
            except WebSocketDisconnect:
                await manager.disconnect_agent(player_id)
                await manager.broadcast_frontend()
        else:
            await websocket.close(code=1008, reason="Unknown client type")

    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
