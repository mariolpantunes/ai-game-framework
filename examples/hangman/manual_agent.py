import asyncio
import sys
import os
import json

try:
    import websockets
except ImportError:
    print("Error: The 'websockets' library is required to run the agent.")
    print("Please install it: pip install websockets")
    sys.exit(1)

# Gorgeous ASCII Gallows representation for the CLI
GALLOWS_ART = [
    # 0 lives remaining (LOST)
    """
      +---+
      |   |
      O   |
     /|\\  |
     / \\  |
          |
    =========
    """,
    # 1 lives remaining
    """
      +---+
      |   |
      O   |
     /|\\  |
     /    |
          |
    =========
    """,
    # 2 lives remaining
    """
      +---+
      |   |
      O   |
     /|\\  |
          |
          |
    =========
    """,
    # 3 lives remaining
    """
      +---+
      |   |
      O   |
     /|   |
          |
          |
    =========
    """,
    # 4 lives remaining
    """
      +---+
      |   |
      O   |
      |   |
          |
          |
    =========
    """,
    # 5 lives remaining
    """
      +---+
      |   |
      O   |
          |
          |
          |
    =========
    """,
    # 6 lives remaining
    """
      +---+
      |   |
          |
          |
          |
          |
    =========
    """
]

async def receive_loop(websocket):
    try:
        async for msg in websocket:
            data = json.loads(msg)
            if data.get("type") == "setup":
                print("\n[Handshake Complete] Assigned Guesser ID.")
                print("Start typing letters below to guess the word.")
                print("="*60)
            elif data.get("type") == "update":
                status = data.get("status", "LOBBY")
                masked = data.get("masked_word", "")
                guessed = data.get("guessed_letters", [])
                lives = data.get("remaining_lives", 6)
                secret = data.get("secret_word", "")
                
                # Render CLI HUD
                os.system("clear" if os.name == "posix" else "cls")
                print("="*16 + " HANGMAN TERMINAL GAME " + "="*16)
                print(GALLOWS_ART[max(0, min(6, lives))])
                
                spaced_masked = " ".join(list(masked)).upper()
                print(f"WORD:  {spaced_masked}")
                print(f"GUESSED LETTERS: {', '.join(guessed).upper()}")
                print(f"LIVES REMAINING: {lives}")
                print("-" * 55)
                
                if status == "WON":
                    print("\n🏆 VICTORY! You guessed the word successfully!")
                    print("Press ENTER to play again or type 'q' to quit.")
                elif status == "LOST":
                    print(f"\n💀 DEFEAT! The secret word was: {secret.upper()}")
                    print("Press ENTER to play again or type 'q' to quit.")
                else:
                    print("\n[ACTION REQUIRED] Guess a letter (A-Z) and press ENTER. Type 'q' to quit.")
                print("="*55)
                print("\nYour input: ", end="", flush=True)
    except websockets.exceptions.ConnectionClosed:
        print("\nDisconnected from Hangman Server.")

async def send_loop(websocket):
    # Set stdin to non-blocking or just standard async reading
    loop = asyncio.get_event_loop()
    
    # Read guesses asynchronously from stdin
    def read_stdin():
        return sys.stdin.readline().strip().lower()
        
    while True:
        guess = await loop.run_in_executor(None, read_stdin)
        if guess:
            if guess == "q" or guess == "quit":
                print("Exiting Manual Agent...")
                break
            
            # Send single character guess
            if len(guess) == 1 and guess.isalpha():
                await websocket.send(json.dumps({"action": guess}))
            # Empty input triggers game restart if status is WON/LOST
            elif len(guess) == 0:
                await websocket.send(json.dumps({"action": "reset"}))
            else:
                print("Invalid input! Please enter a single letter (a-z).")
                print("Your input: ", end="", flush=True)
        await asyncio.sleep(0.05)

async def main():
    url = "ws://localhost:8765/ws"
    print(f"Connecting to Hangman Server on {url}...")
    try:
        async with websockets.connect(url) as websocket:
            # Connect as guesser agent
            await websocket.send(json.dumps({"client": "agent", "name": "Terminal Guesser"}))
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
        print("\nGuesser exited.")
