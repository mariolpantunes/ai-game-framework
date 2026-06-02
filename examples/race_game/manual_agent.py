import asyncio
import sys
import os
import json
import logging
import select

# Try loading termios and tty for non-blocking single-key inputs (standard on Unix/Linux)
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
    print("Please install it via: pip install websockets")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - AGENT - %(levelname)s - %(message)s")

# Key mappings for Linux escape sequences and standard WASD
KEY_MAPPINGS = {
    # Arrows
    "\x1b[A": "up",
    "\x1b[B": "down",
    "\x1b[D": "left",
    "\x1b[C": "right",
    # WASD
    "w": "up",
    "s": "down",
    "a": "left",
    "d": "right",
    # Mute/Stop
    " ": "stop",
    "q": "quit"
}

def read_key_raw() -> str:
    """
    Reads a single key press from standard input in raw terminal mode.
    """
    if not HAS_TERMIOS:
        # Fallback to standard input lines if termios is unavailable
        line = sys.stdin.readline().strip().lower()
        if line in ("w", "up"): return "w"
        if line in ("s", "down"): return "s"
        if line in ("a", "left"): return "a"
        if line in ("d", "right"): return "d"
        if line == "q": return "q"
        return " "

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        # Select waits until input is ready (non-blocking)
        rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
        if rlist:
            char = sys.stdin.read(1)
            if char == "\x1b":  # Escape sequence (e.g. arrow keys)
                # Escape sequences are 3 characters: \x1b, [, and a letter (A, B, C, D)
                # We read the remaining characters with a short select timeout
                rlist2, _, _ = select.select([sys.stdin], [], [], 0.02)
                if rlist2:
                    char += sys.stdin.read(2)
            return char
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ""

async def receive_loop(websocket):
    """
    Listens to server state broadcasts and renders a status HUD.
    """
    try:
        async for msg in websocket:
            data = json.loads(msg)
            if data.get("type") == "setup":
                print(f"\n[Handshake Complete] Assigned Player ID: {data.get('player_id')}")
                print(f"Board size: {data.get('width')}x{data.get('height')}")
                print("Controls: Arrow keys / WASD to steer, Space to coast/stop, Q to quit.")
                print("="*65)
            elif data.get("type") == "update":
                # Render a simple HUD showing player stats
                players = data.get("players", [])
                os.system("clear" if os.name == "posix" else "cls")
                print("="*25 + " NEON GP TERMINAL HUD " + "="*25)
                print(f"{'PLAYER ID':<12} | {'COLOR':<8} | {'SPEED (km/h)':<14} | {'LAPS':<6} | {'STATUS':<10}")
                print("-" * 68)
                for p in players:
                    speed_kmh = round(abs(p.get("speed", 0)) * 0.6)
                    off_road_status = "OFF-ROAD" if p.get("off_road") else "TRACK"
                    print(f"Agent {p.get('id'):<6} | {p.get('color'):<8} | {speed_kmh:<14} | {p.get('laps'):<6} | {off_road_status:<10}")
                print("="*68)
                print("\n[ACTIVE INPUTS] Steering and Throttle Active. Press Q to exit.")
            elif data.get("type") == "reset":
                print("\n[ALERT] Track was reset by the server. Back to start grid!")
    except websockets.exceptions.ConnectionClosed:
        print("\nDisconnected from Race Server.")

async def send_loop(websocket):
    """
    Continuously polls the terminal for keys and sends action updates to the server.
    """
    # Simple steering states
    last_action = "none"
    
    while True:
        key = read_key_raw()
        if key:
            action_name = KEY_MAPPINGS.get(key)
            if action_name == "quit":
                print("\nExiting Manual Agent...")
                break
            
            if action_name:
                # Map action name to commands
                payload = {"action": action_name}
                await websocket.send(json.dumps(payload))
                last_action = action_name
        else:
            # If no keys are held/pressed, release steer or slow down to natural physics coasting
            # For terminal, we send release steering if we don't hold keys
            # To avoid flooding, we only send if something was active
            if last_action != "none":
                await websocket.send(json.dumps({"action": "stop"}))
                last_action = "none"
                
        await asyncio.sleep(0.05)

async def main():
    host = "localhost"
    port = 8765
    url = f"ws://{host}:{port}/ws"
    
    print(f"Connecting to Race Server on {url}...")
    try:
        async with websockets.connect(url) as websocket:
            # Complete the agent connection handshake
            handshake = {
                "client": "agent",
                "name": "Terminal Driver"
            }
            await websocket.send(json.dumps(handshake))
            
            # Start concurrent send and receive tasks
            await asyncio.gather(
                receive_loop(websocket),
                send_loop(websocket)
            )
    except Exception as e:
        print(f"Error connecting to server: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDriver exited by interrupt.")
