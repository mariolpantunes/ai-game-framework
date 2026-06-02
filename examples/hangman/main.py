import logging
import random
from typing import Any

from aigf.interface import AIGameServer, GameState

logging.basicConfig(level=logging.INFO, format="%(asctime)s - HANGMAN - %(levelname)s - %(message)s")

# Initialize discrete game server (no real-time loop ticks needed)
app = AIGameServer(is_real_time=False)

# Dictionary of secret words
WORDS = [
    "python", "websockets", "asynchronous", "decorator", "framework",
    "optimization", "neuroevolution", "agent", "simulation", "arcade",
    "algorithm", "interface", "keyboard", "visualizer", "pipeline"
]

# Game state
secret_word = ""
guessed_letters: list[str] = []
remaining_lives = 6
game_status = "LOBBY"  # LOBBY, RUNNING, WON, LOST
players: dict[int, str] = {}

def get_masked_word() -> str:
    """
    Returns the secret word masked with underscores for unguessed letters.
    """
    return "".join([char if char in guessed_letters else "_" for char in secret_word])

def start_new_game():
    global secret_word, guessed_letters, remaining_lives, game_status
    secret_word = random.choice(WORDS).lower()
    guessed_letters = []
    remaining_lives = 6
    game_status = "RUNNING"
    logging.info(f"New Hangman game started. Secret word chosen: {secret_word}")

@app.on_connect
async def handle_connect(player_id: int):
    logging.info(f"Player {player_id} joined Hangman.")
    players[player_id] = f"Guesser {player_id}"

    # Auto-start a new game if in lobby
    if game_status == "LOBBY" or not secret_word:
        start_new_game()
        app.state = GameState.RUNNING

@app.on_disconnect
async def handle_disconnect(player_id: int):
    logging.info(f"Player {player_id} disconnected.")
    if player_id in players:
        del players[player_id]
    if not players:
        global game_status
        game_status = "LOBBY"
        app.state = GameState.LOBBY

@app.on_action
async def handle_action(player_id: int, action: dict[str, Any]):
    global guessed_letters, remaining_lives, game_status

    cmd = action.get("action") or action.get("cmd") or ""
    if isinstance(cmd, str):
        cmd = cmd.lower()

        # Reset command to start a new game session
        if cmd in ("reset", "restart", "start", "reset_sim", "start_sim"):
            start_new_game()
            return

        # Guess command (either {"action": "guess", "letter": "a"} or {"action": "a"})
        letter = ""
        if cmd == "guess" or cmd == "letter":
            letter = str(action.get("letter") or "").lower().strip()
        elif len(cmd) == 1 and cmd.isalpha():
            letter = cmd

        if letter and len(letter) == 1 and letter.isalpha():
            if game_status != "RUNNING":
                logging.info("Attempted guess while game is not active.")
                return

            if letter in guessed_letters:
                logging.info(f"Letter '{letter}' was already guessed.")
                return

            guessed_letters.append(letter)
            logging.info(f"Player {player_id} guessed letter: '{letter}'")

            # Check correctness
            if letter not in secret_word:
                remaining_lives -= 1
                logging.info(f"Incorrect guess! Remaining attempts: {remaining_lives}")

            # Win/Loss check
            masked = get_masked_word()
            if "_" not in masked:
                game_status = "WON"
                logging.info(f"Victory! The word was: {secret_word}")
            elif remaining_lives <= 0:
                game_status = "LOST"
                logging.info(f"Defeat! The secret word was: {secret_word}")

@app.on_get_state
def handle_get_state() -> dict[str, Any]:
    return {
        "masked_word": get_masked_word(),
        "guessed_letters": guessed_letters,
        "remaining_lives": remaining_lives,
        "status": game_status,
        "secret_word": secret_word if game_status in ("WON", "LOST") else "",
    }

@app.on_get_setup
def handle_get_setup() -> dict[str, Any]:
    return {
        "max_lives": 6,
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hangman Discrete Game Server using AIGF.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    args = parser.parse_args()

    app.run(host=args.host, port=args.port)
