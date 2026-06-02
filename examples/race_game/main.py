import asyncio
import math
import random
import logging
from typing import Dict, Any
from aigf.interface import AIGameServer, GameState

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - RACE_GAME - %(levelname)s - %(message)s")

# Initialize the decorated server: real-time, 30 FPS
app = AIGameServer(is_real_time=True, fps=30)

# Track configuration
TRACK = {
    "cx": 400,
    "cy": 300,
    "inner_rx": 220,
    "inner_ry": 140,
    "outer_rx": 360,
    "outer_ry": 260,
}

# Nord Aurora and Frost colors for cars
CAR_COLORS = [
    "#88c0d0",  # Frost Blue (nord8)
    "#a3be8c",  # Green (nord14)
    "#ebcb8b",  # Yellow (nord13)
    "#bf616a",  # Red (nord11)
    "#d08770",  # Orange (nord12)
    "#b48ead",  # Purple (nord15)
]

# Game state variables
players: Dict[int, Dict[str, Any]] = {}

def get_random_color(player_id: int) -> str:
    return CAR_COLORS[player_id % len(CAR_COLORS)]

@app.on_connect
async def handle_connect(player_id: int):
    logging.info(f"Agent {player_id} connected to Race Game.")
    
    # Spawn player on the start line (bottom of the track, x=400, y=500)
    # Heading right (angle = 0)
    players[player_id] = {
        "id": player_id,
        "name": f"Agent {player_id}",
        "x": 400.0,
        "y": 500.0,
        "angle": 0.0,  # in radians
        "speed": 0.0,
        "color": get_random_color(player_id),
        "laps": 0,
        "off_road": False,
        "last_angle": 0.0,  # for lap counting
        "accel_input": 0.0,  # -1.0 to 1.0
        "steer_input": 0.0,  # -1.0 to 1.0
    }
    
    # If in lobby and we have players, auto-start!
    if app.state == GameState.LOBBY:
        logging.info("Auto-starting game session.")
        app.state = GameState.RUNNING

@app.on_disconnect
async def handle_disconnect(player_id: int):
    logging.info(f"Agent {player_id} disconnected.")
    if player_id in players:
        del players[player_id]
        
    if not players:
        app.state = GameState.LOBBY

@app.on_action
async def handle_action(player_id: int, action: Dict[str, Any]):
    # Process inputs from agents
    # Supports keyboard keys ("up", "down", "left", "right") or analog controls
    player = players.get(player_id)
    if not player:
        return

    # Check for direct key controls (e.g. from manual_agent)
    cmd = action.get("action") or action.get("cmd") or ""
    if isinstance(cmd, str):
        cmd = cmd.lower()
        if cmd == "accelerate" or cmd == "up":
            player["accel_input"] = 1.0
        elif cmd == "brake" or cmd == "down":
            player["accel_input"] = -0.5
        elif cmd == "steer_left" or cmd == "left":
            player["steer_input"] = -1.0
        elif cmd == "steer_right" or cmd == "right":
            player["steer_input"] = 1.0
        elif cmd == "release_accel":
            player["accel_input"] = 0.0
        elif cmd == "release_steer":
            player["steer_input"] = 0.0
        elif cmd == "stop" or cmd == "none":
            player["accel_input"] = 0.0
            player["steer_input"] = 0.0

    # Also support structure: { "accel": float, "steer": float }
    if "accel" in action:
        player["accel_input"] = max(-1.0, min(1.0, float(action["accel"])))
    if "steer" in action:
        player["steer_input"] = max(-1.0, min(1.0, float(action["steer"])))

@app.on_tick
async def handle_tick(dt: float):
    # Physics updates for each car
    for p_id, p in players.items():
        # Check off-road status (distance from center relative to track ellipses)
        dx = p["x"] - TRACK["cx"]
        dy = p["y"] - TRACK["cy"]
        
        # Calculate normalized radius squared relative to inner/outer track boundaries
        # Ellipse formula: (x/rx)^2 + (y/ry)^2
        inner_val = (dx / TRACK["inner_rx"])**2 + (dy / TRACK["inner_ry"])**2
        outer_val = (dx / TRACK["outer_rx"])**2 + (dy / TRACK["outer_ry"])**2
        
        # We are off-road if inside the inner ellipse or outside the outer ellipse
        off_road = (inner_val < 1.0) or (outer_val > 1.0)
        p["off_road"] = off_road
        
        # Set acceleration and drag factors
        max_speed = 100.0 if off_road else 280.0
        accel_factor = 150.0 if not off_road else 50.0
        drag_factor = 0.90 if off_road else 0.97
        
        # Update speed
        p["speed"] += p["accel_input"] * accel_factor * dt
        p["speed"] *= drag_factor
        
        # Cap speed
        if p["speed"] > max_speed:
            p["speed"] = max_speed
        elif p["speed"] < -max_speed / 2.0:
            p["speed"] = -max_speed / 2.0
            
        # Update steer angle (rad/s)
        # Higher speeds make it harder/slower to steer tightly, simulating momentum
        steer_speed = 3.2 - min(2.0, abs(p["speed"]) / 120.0)
        p["angle"] += p["steer_input"] * steer_speed * dt
        p["angle"] = p["angle"] % (2 * math.pi)
        
        # Update position
        p["x"] += p["speed"] * math.cos(p["angle"]) * dt
        p["y"] += p["speed"] * math.sin(p["angle"]) * dt
        
        # Boundary constraints (keep within screen area 800x600)
        p["x"] = max(10, min(790, p["x"]))
        p["y"] = max(10, min(590, p["y"]))
        
        # Lap counting check (when crossing x=400, y>300 heading right/clockwise)
        # Clockwise around (400, 300):
        # Angle from center (dx, dy):
        center_angle = math.atan2(dy, dx) # -pi to pi
        prev_center_angle = p.get("last_center_angle", center_angle)
        
        # Crossing the bottom vertical axis (start/finish line is at x=400, y > 300)
        # In atan2: bottom axis is math.pi/2 (90 deg)
        # Driving clockwise means the angle increases through math.pi/2
        if prev_center_angle < math.pi/2 <= center_angle or (prev_center_angle > 2.5 and center_angle < -2.5 and prev_center_angle - center_angle > math.pi):
            # Crossed the start line going clockwise!
            p["laps"] += 1
            logging.info(f"Player {p_id} completed lap {p['laps']}!")
            
        p["last_center_angle"] = center_angle

@app.on_get_state
def handle_get_state() -> Dict[str, Any]:
    # Return all game variables to the frontend
    return {
        "players": list(players.values()),
        "track": TRACK,
        "width": 800,
        "height": 600,
    }

@app.on_get_setup
def handle_get_setup() -> Dict[str, Any]:
    return {
        "width": 800,
        "height": 600,
        "track": TRACK,
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Race Game Server using AIGameServer Framework.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to run the server on")
    parser.add_argument("--port", type=int, default=8765, help="Port to run the server on")
    args = parser.parse_args()
    
    logging.info(f"Launching Race Game on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port)
