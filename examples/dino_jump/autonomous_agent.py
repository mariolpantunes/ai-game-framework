__author__ = "Mário Antunes"
__version__ = "1.1.0"
__email__ = "mario.antunes@ua.pt"
__status__ = "Development"

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Error: The 'websockets' library is required to run the agent.")
    print("Please install it: pip install websockets")
    sys.exit(1)

async def play_dino(host: str, port: int):
    url = f"ws://{host}:{port}/ws"
    print(f"Connecting to Dino Jump Server on {url}...")
    
    player_id = None
    
    try:
        async with websockets.connect(url) as websocket:
            # Shake hands
            await websocket.send(json.dumps({"client": "agent", "name": "Autonomous Dino"}))
            
            async for msg in websocket:
                data = json.loads(msg)
                
                if data.get("type") == "setup":
                    player_id = data.get("player_id")
                    print(f"\n[Handshake Complete] Connected as Agent {player_id}.")
                    print("=" * 60)
                
                elif data.get("type") == "update":
                    players = data.get("players", [])
                    obstacles = data.get("obstacles", [])
                    high_score = data.get("high_score", 0)
                    
                    # Find our dino
                    my_dino = None
                    for p in players:
                        if p.get("id") == player_id:
                            my_dino = p
                            break
                    
                    if not my_dino:
                        continue
                    
                    dino_x = my_dino.get("x", 100.0)
                    dino_y = my_dino.get("y", 252.0)
                    is_jumping = my_dino.get("is_jumping", False)
                    alive = my_dino.get("alive", True)
                    score = my_dino.get("score", 0)
                    
                    print(f"Score: {score} | High Score: {high_score} | Alive: {alive} | Jumping: {is_jumping}")
                    
                    if not alive:
                        continue
                    
                    # Look for nearest obstacle in front of us
                    for obs in obstacles:
                        obs_x = obs.get("x", 0.0)
                        dist = obs_x - dino_x
                        
                        # If the obstacle is ahead and close, trigger jump!
                        if 0 < dist < 160.0 and not is_jumping:
                            print(f"Nearest obstacle at distance {dist:.1f}! JUMP!")
                            await websocket.send(json.dumps({"action": "jump"}))
                            break
                            
    except websockets.exceptions.ConnectionClosed:
        print("\nDisconnected from Dino Jump Server.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dino Jump Autonomous Agent using AIGF.")
    parser.add_argument("--host", type=str, default="localhost", help="Host address")
    parser.add_argument("--port", type=int, default=8765, help="Port of the server")
    args = parser.parse_args()
    
    try:
        asyncio.run(play_dino(args.host, args.port))
    except KeyboardInterrupt:
        print("\nAutonomous dino driver exited.")
