import asyncio
import sys
import os
import json
import select

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

def read_key_raw() -> str:
    if not HAS_TERMIOS:
        line = sys.stdin.readline().strip().lower()
        if line in ("w", "up", " ", ""):
            return " "
        if line == "q":
            return "q"
        return ""

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        # Listen for key press (non-blocking)
        rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
        if rlist:
            char = sys.stdin.read(1)
            if char == "\x1b":  # Escape sequence (arrow keys)
                rlist2, _, _ = select.select([sys.stdin], [], [], 0.02)
                if rlist2:
                    char += sys.stdin.read(2)
            return char
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ""

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
                
                os.system("clear" if os.name == "posix" else "cls")
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
    while True:
        key = read_key_raw()
        if key:
            if key == "q" or key.lower() == "q":
                print("\nExiting Manual Agent...")
                break
            # SPACEBAR, Arrow Up ('\x1b[A'), or 'w' / 'W' triggers JUMP
            if key in (" ", "\x1b[A", "w", "W"):
                await websocket.send(json.dumps({"action": "jump"}))
        await asyncio.sleep(0.02)

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
