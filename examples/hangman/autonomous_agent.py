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

# Predefined frequency order of letters in English words to guess reasonably smart
LETTER_FREQUENCY = list("etaoinshrdlcumwfgypbvkjxqz")

async def play_hangman(host: str, port: int):
    url = f"ws://{host}:{port}/ws"
    print(f"Connecting to Hangman Server on {url}...")
    try:
        async with websockets.connect(url) as websocket:
            # Shake hands
            await websocket.send(json.dumps({"client": "agent", "name": "Autonomous Guesser"}))
            
            async for msg in websocket:
                data = json.loads(msg)
                
                if data.get("type") == "setup":
                    player_id = data.get("player_id")
                    print(f"\n[Handshake Complete] Connected as Agent {player_id}.")
                    print("=" * 60)
                
                elif data.get("type") == "update":
                    status = data.get("status", "LOBBY")
                    masked = data.get("masked_word", "")
                    guessed = data.get("guessed_letters", [])
                    lives = data.get("remaining_lives", 6)
                    secret = data.get("secret_word", "")
                    
                    print(f"Word: {masked} | Guessed: {guessed} | Lives: {lives} | Status: {status}")
                    
                    if status in ("WON", "LOST"):
                        if status == "WON":
                            print(f"🏆 VICTORY! The word was guessed successfully.")
                        else:
                            print(f"💀 DEFEAT! The secret word was: {secret}")
                        print("Waiting to start a new game...")
                        await asyncio.sleep(2.0)
                        await websocket.send(json.dumps({"action": "reset"}))
                    elif status == "RUNNING":
                        # Guess next letter that hasn't been guessed yet
                        next_guess = None
                        for letter in LETTER_FREQUENCY:
                            if letter not in guessed:
                                next_guess = letter
                                break
                        
                        if next_guess:
                            print(f"Guesser decides to guess letter: '{next_guess.upper()}'")
                            await websocket.send(json.dumps({"action": next_guess}))
                        await asyncio.sleep(1.0)
                        
    except websockets.exceptions.ConnectionClosed:
        print("\nDisconnected from Hangman Server.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hangman Autonomous Agent using AIGF.")
    parser.add_argument("--host", type=str, default="localhost", help="Host address")
    parser.add_argument("--port", type=int, default=8765, help="Port of the server")
    args = parser.parse_args()
    
    try:
        asyncio.run(play_hangman(args.host, args.port))
    except KeyboardInterrupt:
        print("\nAutonomous guesser exited.")
