import asyncio
import importlib
import logging
import os
import time
from typing import Any

try:
    import orjson  # pyright: ignore[reportMissingImports]
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False
    import json

import contextlib

import websockets
from websockets.datastructures import Headers
from websockets.http11 import Response

from .interface import GameInterface, GameState
from .manager import ConnectionManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - SERVER - %(levelname)s - %(message)s")


def serialize(obj: Any) -> Any:
    """
    Serializes an object to JSON. Returns bytes if orjson is available,
    otherwise returns a string.
    """
    if HAS_ORJSON:
        return orjson.dumps(obj)
    return json.dumps(obj)


def deserialize(s: Any) -> Any:
    """
    Deserializes JSON data.
    """
    if HAS_ORJSON:
        return orjson.loads(s)
    return json.loads(s)


# Global game, manager, and server/stop control instances
game_instance: GameInterface | None = None
manager: ConnectionManager | None = None
server: Any | None = None
stop_event: asyncio.Event | None = None

# --- Lightweight Web Server Scaffolding ---

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
    ".ico": "image/x-icon",
}


def get_mime_type(filepath: str) -> str:
    _, ext = os.path.splitext(filepath.lower())
    return MIME_TYPES.get(ext, "application/octet-stream")


def find_static_file(path: str) -> str | None:
    """
    Finds a static file matching path inside standard directories.
    Prevents directory traversal attacks.
    """
    clean_path = path.lstrip("/")
    if not clean_path:
        clean_path = "index.html"

    cwd = os.getcwd()

    # We search in these directories in order:
    search_dirs = [
        os.path.join(cwd, "frontend"),
        os.path.join(cwd, "viewer"),
        os.path.join(cwd, "game", "frontend"),
        os.path.join(cwd, "game", "viewer"),
        cwd,
        # Check submodule's own frontend assets
        os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend")),
    ]

    paths_to_try = [clean_path]
    if clean_path.startswith("framework/"):
        paths_to_try.append(clean_path[len("framework/"):])
    elif clean_path.startswith("aigf/"):
        paths_to_try.append(clean_path[len("aigf/"):])
    elif clean_path.startswith("frontend/"):
        paths_to_try.append(clean_path[len("frontend/"):])

    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        for p in paths_to_try:
            candidate = os.path.abspath(os.path.join(sdir, p))
            # Directory traversal protection:
            if candidate.startswith(os.path.abspath(sdir)) and os.path.exists(candidate) and os.path.isfile(candidate):
                return candidate
    return None


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
        try:
            await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            logging.info("Real-time game loop cancelled.")
            break


async def process_request(connection: Any, request: Any) -> Response | None:
    """
    Intercepts HTTP requests.
    Supports a REST API to query maps, health checks, and a full-fledged static file server
    to serve viewer templates (no Nginx required!).
    """
    path = request.path

    # Standard REST API for map listing
    if (path == "/api/maps" or path == "/api/maps/") and game_instance:
        maps = game_instance.get_map_list()
        body_bytes = serialize({"maps": maps})
        if not isinstance(body_bytes, bytes):
            body_bytes = body_bytes.encode("utf-8")
        return Response(
            status_code=200,
            reason_phrase="OK",
            headers=Headers([
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body_bytes))),
                ("Connection", "close"),
            ]),
            body=body_bytes
        )

    # Health Checks
    if path == "/health" or path == "/healthcheck":
        body = serialize({"status": "running", "game_loaded": game_instance is not None})
        body_bytes = body if isinstance(body, bytes) else body.encode("utf-8")
        return Response(
            status_code=200,
            reason_phrase="OK",
            headers=Headers([
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body_bytes))),
                ("Connection", "close"),
            ]),
            body=body_bytes
        )

    # Static File Server for anything not matching /ws
    if path != "/ws":
        filepath = find_static_file(path)
        if filepath:
            try:
                with open(filepath, "rb") as f:
                    body_bytes = f.read()
                mime = get_mime_type(filepath)
                return Response(
                    status_code=200,
                    reason_phrase="OK",
                    headers=Headers([
                        ("Content-Type", mime),
                        ("Content-Length", str(len(body_bytes))),
                        ("Connection", "close"),
                        ("Access-Control-Allow-Origin", "*"),
                    ]),
                    body=body_bytes
                )
            except Exception as e:
                logging.error(f"Error reading file {filepath}: {e}")
                body = f"Internal Server Error: {e}".encode()
                return Response(
                    status_code=500,
                    reason_phrase="Internal Server Error",
                    headers=Headers([
                        ("Content-Type", "text/plain"),
                        ("Content-Length", str(len(body))),
                        ("Connection", "close"),
                    ]),
                    body=body
                )
        else:
            # Fall back to health check status description for GET to '/' if no index.html found
            if path == "/":
                body = serialize({"status": "running", "game_loaded": game_instance is not None})
                body_bytes = body if isinstance(body, bytes) else body.encode("utf-8")
                return Response(
                    status_code=200,
                    reason_phrase="OK",
                    headers=Headers([
                        ("Content-Type", "application/json"),
                        ("Content-Length", str(len(body_bytes))),
                        ("Connection", "close"),
                    ]),
                    body=body_bytes
                )

            body = f"File Not Found: {path}".encode()
            return Response(
                status_code=404,
                reason_phrase="Not Found",
                headers=Headers([
                    ("Content-Type", "text/plain"),
                    ("Content-Length", str(len(body))),
                    ("Connection", "close"),
                ]),
                body=body
            )

    return None


async def handler(websocket: Any) -> None:
    """
    WebSocket handler for both frontend and agent clients.
    Handles standard simulation start/stop/reset actions natively.
    """
    if manager is None or game_instance is None:
        await websocket.close(code=1011, reason="Game not initialized")
        return

    path = getattr(websocket.request, "path", "/ws")
    if path != "/ws":
        await websocket.close(code=1008, reason="Invalid path")
        return

    try:
        # Initial handshake to identify client type
        msg = await websocket.recv()
        data = deserialize(msg)
        client_type = data.get("client")

        if client_type == "frontend":
            await manager.connect_frontend(websocket)
            try:
                # Send the maps and metadata immediately
                await manager.broadcast_frontend()

                async for msg in websocket:
                    action = deserialize(msg)
                    cmd_raw = action.get("action") or action.get("command") or action.get("cmd")
                    cmd = cmd_raw.lower() if isinstance(cmd_raw, str) else ""

                    # Natively dispatch framework simulation state controls
                    if cmd in ("start_sim", "start"):
                        await game_instance.on_start_sim()
                    elif cmd in ("stop_sim", "stop", "pause"):
                        await game_instance.on_stop_sim()
                    elif cmd in ("reset_sim", "reset"):
                        await game_instance.on_reset_sim()
                        # Broadcast reset command to all connected agents
                        for agent_ws in list(manager.agent_wss.values()):
                            with contextlib.suppress(Exception):
                                await agent_ws.send(serialize({"type": "reset"}))
                    elif cmd == "load_map":
                        filename = action.get("filename")
                        map_data = game_instance.load_map(filename)
                        if map_data:
                            game_instance.current_map_name = filename
                            game_instance.load_map_data(map_data)
                            # Broadcast reset command to all connected agents
                            for agent_ws in list(manager.agent_wss.values()):
                                with contextlib.suppress(Exception):
                                    await agent_ws.send(serialize({"type": "reset"}))
                    elif cmd == "save_map":
                        filename = action.get("filename")
                        map_data = action.get("map_data")
                        success, error = game_instance.save_map(filename, map_data)
                        with contextlib.suppress(Exception):
                            await websocket.send(serialize({
                                "type": "save_response",
                                "success": success,
                                "error": error
                            }))

                    # Pass message to game implementation for any custom commands
                    await game_instance.process_action(0, action)
                    await manager.broadcast_frontend()
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                await manager.disconnect_frontend()

        elif client_type == "agent":
            player_id = await manager.connect_agent(websocket)
            await game_instance.on_handshake(player_id, data)

            # Send initial setup
            setup_data = {
                "type": "setup",
                "player_id": player_id,
                **game_instance.get_setup_payload()
            }
            await websocket.send(serialize(setup_data))
            await manager.broadcast_frontend()

            try:
                async for msg in websocket:
                    action = deserialize(msg)
                    if game_instance.state == GameState.RUNNING:
                        await game_instance.process_action(player_id, action)
                        # For discrete games, we might want to broadcast after every action
                        if not game_instance.is_real_time:
                            await manager.broadcast_frontend()
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                await manager.disconnect_agent(player_id)
                await manager.broadcast_frontend()
        else:
            await websocket.close(code=1008, reason="Unknown client type")

    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        with contextlib.suppress(Exception):
            await websocket.close()


async def serve_game_instance(instance: GameInterface, host: str, port: int) -> None:
    """
    Main function to run an instantiated game server.
    """
    global game_instance, manager, server, stop_event
    game_instance = instance
    manager = ConnectionManager(game_instance)
    stop_event = asyncio.Event()

    loop_task = None
    if game_instance.is_real_time:
        loop_task = asyncio.create_task(game_loop())

    logging.info(f"Starting WebSocket server on ws://{host}:{port}/ws")
    async with websockets.serve(handler, host, port, process_request=process_request) as s:
        server = s
        await stop_event.wait()

    if loop_task:
        loop_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await loop_task
    logging.info("WebSocket server stopped.")


async def serve_game(host: str, port: int) -> None:
    """
    Backward-compatible server launcher (loads from GAME_CLASS environment).
    """
    load_game()
    if game_instance:
        await serve_game_instance(game_instance, host, port)


def run_app(instance: GameInterface, host: str = "0.0.0.0", port: int = 8765) -> None:
    """
    Synchronously runs a game server instance (FastAPI/Flask app style).
    """
    try:
        asyncio.run(serve_game_instance(instance, host, port))
    except KeyboardInterrupt:
        logging.info("Server terminated by user.")


async def stop_game() -> None:
    """
    Stops the currently running game server.
    """
    global stop_event
    if stop_event:
        stop_event.set()


import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Game Framework Server - Scaffolding for Agent-Based Games."
    )
    parser.add_argument(
        "--host", "-H",
        type=str,
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host address to bind the server to (default: 0.0.0.0 or $HOST)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=int(os.getenv("PORT", "8765")),
        help="Port number to listen on (default: 8765 or $PORT)"
    )
    parser.add_argument(
        "--game-class", "-g",
        type=str,
        default=os.getenv("GAME_CLASS", ""),
        help="Game class path in format 'package.module.ClassName' (default: $GAME_CLASS)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.game_class:
        os.environ["GAME_CLASS"] = args.game_class
    try:
        asyncio.run(serve_game(args.host, args.port))
    except KeyboardInterrupt:
        logging.info("Server terminated by user.")
