# AI Game Framework Examples

This directory contains interactive examples demonstrating the features of the AI Game Framework (aigf).

## Prerequisites

Before running the examples, ensure that the package and its dependencies are installed:

```bash
# Install the library from the repository root
pip install .
```

The interactive terminal agents require the websockets library:

```bash
pip install websockets
```

---

## 1. Dino Jump (Real-Time Game)

A real-time obstacle avoidance game modeled after the classic offline dinosaur browser game. It demonstrates a fast tick rate (30 FPS) loop, collision detection, and multi-agent real-time environments.

### Start the Server
Run the game server from the repository root:

```bash
python3 -m dino_jump.main
```
Or directly via:
```bash
python3 examples/dino_jump/main.py
```

### Play / Watch in the Browser
Open your browser and navigate to:
http://localhost:8765/

The browser page acts as a visual dashboard (Viewer) that renders the game state dynamically in real-time.

### Control the Game via Terminal Agent
To active-play the game, start the manual agent in your terminal:

```bash
python3 -m dino_jump.manual_agent
```
Or directly via:
```bash
python3 examples/dino_jump/manual_agent.py
```

Focus the terminal window and use:
* SPACEBAR or Arrow Up (or W) to jump.
* Q to exit the agent session.

### Control the Game via Autonomous Agent
To watch the AI play the game autonomously:

```bash
python3 examples/dino_jump/autonomous_agent.py
```

---

## 2. Hangman (Turn-Based/Discrete Game)

A discrete, event-driven word guessing game. It demonstrates how to utilize discrete state machines without ticking game loops.

### Start the Server
Run the game server from the repository root:

```bash
python3 -m hangman.main
```
Or directly via:
```bash
python3 examples/hangman/main.py
```

### Play / Watch in the Browser
Open your browser and navigate to:
http://localhost:8765/

You can play directly inside the browser by clicking the alphabet buttons or typing on your physical keyboard.

### Play via Terminal Agent
Alternatively, you can play directly from your terminal using the discrete CLI agent:

```bash
python3 -m hangman.manual_agent
```
Or directly via:
```bash
python3 examples/hangman/manual_agent.py
```

Follow the prompts on your terminal screen:
* Type a letter (A-Z) and press ENTER to guess.
* Type Q and press ENTER to quit.

### Play via Autonomous Agent
Alternatively, you can watch the autonomous agent play the game:

```bash
python3 examples/hangman/autonomous_agent.py
```
