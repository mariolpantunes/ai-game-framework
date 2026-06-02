import logging
import random
from typing import Any

from aigf.interface import AIGameServer, GameState

logging.basicConfig(level=logging.INFO, format="%(asctime)s - DINO_JUMP - %(levelname)s - %(message)s")

# Initialize real-time server at 30 FPS
app = AIGameServer(is_real_time=True, fps=30)

# Constants
GROUND_Y = 300.0
DINO_WIDTH = 44
DINO_HEIGHT = 48
OBSTACLE_WIDTH = 24
OBSTACLE_HEIGHT = 46

# Game variables
players: dict[int, dict[str, Any]] = {}
obstacles: list[dict[str, Any]] = []
high_score = 0
spawn_timer = 0.0

@app.on_connect
async def handle_connect(player_id: int):
    logging.info(f"Agent {player_id} connected to Dino Jump.")
    # Spawn player dino on the ground
    players[player_id] = {
        "id": player_id,
        "name": f"Dino Agent {player_id}",
        "x": 100.0,
        "y": GROUND_Y - DINO_HEIGHT,
        "vy": 0.0,
        "is_jumping": False,
        "score": 0,
        "alive": True,
    }

    if app.state == GameState.LOBBY:
        logging.info("Starting Dino Jump session.")
        app.state = GameState.RUNNING

@app.on_disconnect
async def handle_disconnect(player_id: int):
    logging.info(f"Agent {player_id} disconnected.")
    if player_id in players:
        del players[player_id]
    if not players:
        app.state = GameState.LOBBY

@app.on_action
async def handle_action(player_id: int, action: dict[str, Any]):
    player = players.get(player_id)
    if not player or not player["alive"]:
        return

    cmd = action.get("action") or action.get("cmd") or ""
    if isinstance(cmd, str):
        cmd = cmd.lower()
        # Trigger jump when "jump", "space", or "up" is received
        if cmd in ("jump", "space", "up") and not player["is_jumping"]:
            player["vy"] = -520.0  # Upward velocity
            player["is_jumping"] = True
            logging.info(f"Player {player_id} jumped!")

@app.on_tick
async def handle_tick(dt: float):
    global spawn_timer, obstacles, high_score

    # 1. Physics update for players
    for p in players.values():
        if not p["alive"]:
            continue

        # Apply gravity
        p["vy"] += 1400.0 * dt
        p["y"] += p["vy"] * dt

        # Ground check
        if p["y"] >= GROUND_Y - DINO_HEIGHT:
            p["y"] = GROUND_Y - DINO_HEIGHT
            p["vy"] = 0.0
            p["is_jumping"] = False

        # Increment score slowly
        p["score"] += 1
        if p["score"] > high_score:
            high_score = p["score"]

    # 2. Obstacle spawning logic (distance-based + random interval)
    spawn_timer += dt
    # Ensure there is space between obstacles (minimum 1.8 seconds or ~450 pixels)
    can_spawn = True
    if obstacles:
        rightmost_x = max(obs["x"] for obs in obstacles)
        if rightmost_x > 500.0:
            can_spawn = False

    if can_spawn and spawn_timer > 1.4 and (random.random() < 0.3 or spawn_timer > 3.0):
        # Spawn new cactus obstacle
        obstacles.append({
            "x": 800.0,
            "y": GROUND_Y - OBSTACLE_HEIGHT,
            "width": OBSTACLE_WIDTH,
            "height": OBSTACLE_HEIGHT,
        })
        spawn_timer = 0.0

    # 3. Translate obstacles leftwards
    # Obstacle speed increases slightly over time to scale difficulty
    speed = 280.0
    if players:
        max_score = max(p["score"] for p in players.values())
        speed += min(200.0, max_score * 0.05)  # Scale up speed

    next_obstacles = []
    for obs in obstacles:
        obs["x"] -= speed * dt
        # Keep obstacle if it's still on screen
        if obs["x"] + obs["width"] > 0:
            next_obstacles.append(obs)
    obstacles = next_obstacles

    # 4. Bounding box collision check
    for p_id, p in players.items():
        if not p["alive"]:
            continue

        # Bounding box coordinates for Dino
        d_x1, d_y1 = p["x"] + 4, p["y"] + 2
        d_x2, d_y2 = p["x"] + DINO_WIDTH - 4, p["y"] + DINO_HEIGHT - 2

        for obs in obstacles:
            o_x1, o_y1 = obs["x"] + 2, obs["y"]
            o_x2, o_y2 = obs["x"] + obs["width"] - 2, obs["y"] + obs["height"]

            # Check overlap
            if d_x1 < o_x2 and d_x2 > o_x1 and d_y1 < o_y2 and d_y2 > o_y1:
                # Collision!
                logging.info(f"Collision detected! Player {p_id} has crashed.")
                p["alive"] = False

    # 5. Automatically reset/respawn dead players after 2 seconds if in RUNNING state
    # or if all players are dead, reset the obstacles and revive them to keep game going.
    all_dead = len(players) > 0 and all(not p["alive"] for p in players.values())
    if all_dead:
        logging.info("All players crashed. Resetting track grid.")
        obstacles.clear()
        spawn_timer = 0.0
        for p in players.values():
            p["alive"] = True
            p["score"] = 0
            p["x"] = 100.0
            p["y"] = GROUND_Y - DINO_HEIGHT
            p["vy"] = 0.0
            p["is_jumping"] = False

@app.on_get_state
def handle_get_state() -> dict[str, Any]:
    return {
        "players": list(players.values()),
        "obstacles": obstacles,
        "high_score": high_score,
        "width": 800,
        "height": 400,
    }

@app.on_get_setup
def handle_get_setup() -> dict[str, Any]:
    return {
        "width": 800,
        "height": 400,
        "ground_y": GROUND_Y,
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dino Jump Server using AIGF Framework.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8765, help="Port to run on")
    args = parser.parse_args()

    app.run(host=args.host, port=args.port)
