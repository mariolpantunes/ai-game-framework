__author__ = "Mário Antunes"
__version__ = "1.1.0"
__email__ = "mario.antunes@ua.pt"
__status__ = "Development"

import asyncio
import json
import select
import sys

try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

try:
    import websockets
except ImportError:
    print("Error: The 'websockets' library is required to run the agent.")
    print("Please install it: pip install websockets")
    sys.exit(1)
async def receive_loop(websocket):
    try:
        async for msg in websocket:
            data = json.loads(msg)
            if data.get("type") == "setup":
                print(f"\n[Handshake Complete] Assigned Dino Player ID: {data.get('player_id')}")
                print("Controls: SPACEBAR or Arrow Up to JUMP, 'q' to quit.")
                print("="*60)
            elif data.get("type") == "update":
                players = data.get("players", [])
                high_score = data.get("high_score", 0)

                # Clear terminal screen cleanly without spawning a subprocess (which resets raw tty state)
                sys.stdout.write("\033[H\033[2J")
                sys.stdout.flush()

                print("="*18 + " DINO JUMP TERMINAL HUD " + "="*18)
                print(f"HIGH SCORE: {high_score:<10}")
                print("-" * 56)
                print(f"{'PLAYER ID':<10} | {'SCORE':<10} | {'STATUS':<15}")
                print("-" * 56)

                for p in players:
                    status = "RUNNING" if p.get("alive") else "💥 CRASHED!"
                    print(f"Dino {p.get('id'):<5} | {p.get('score'):<10} | {status:<15}")
                print("="*56)
                print("\n[ACTIVE INPUT] Focus this terminal. Press SPACEBAR / W to jump! Press Q to quit.")
    except websockets.exceptions.ConnectionClosed:
        print("\nDisconnected from Dino Jump Server.")

async def send_loop(websocket):
    fd = sys.stdin.fileno() if HAS_TERMIOS else None
    old_settings = None
    if HAS_TERMIOS and fd is not None:
        old_settings = termios.tcgetattr(fd)
        tty.setraw(fd)

    try:
        while True:
            key = ""
            if HAS_TERMIOS and fd is not None:
                rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
                if rlist:
                    key = sys.stdin.read(1)
                    if key == "\x1b":
                        rlist2, _, _ = select.select([sys.stdin], [], [], 0.02)
                        if rlist2:
                            key += sys.stdin.read(2)
            else:
                line = sys.stdin.readline().strip().lower()
                if line in ("w", "up", " ", ""):
                    key = " "
                elif line == "q":
                    key = "q"

            if key:
                if key.lower() == "q":
                    break
                # SPACEBAR, Arrow Up ('\x1b[A'), or 'w' / 'W' triggers JUMP
                if key in (" ", "\x1b[A", "w", "W"):
                    await websocket.send(json.dumps({"action": "jump"}))
            await asyncio.sleep(0.02)
    finally:
        if HAS_TERMIOS and fd is not None and old_settings is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print("\nExiting Manual Agent...")

async def main():
    url = "ws://localhost:8765/ws"
    print(f"Connecting to Dino Jump Server on {url}...")
    try:
        async with websockets.connect(url) as websocket:
            # Shake hands
            await websocket.send(json.dumps({"client": "agent", "name": "Terminal Dino"}))
            await asyncio.gather(
                receive_loop(websocket),
                send_loop(websocket)
            )
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDino driver exited.")
