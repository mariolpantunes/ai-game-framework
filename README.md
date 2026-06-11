# <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CiAgPCEtLSBOb3JkIFBhbGV0dGUgLS0+CiAgPCEtLSBTbm93IFN0b3JtOiAjRUNFRkY0LCAjRTVFOUYwIC0tPgogIDwhLS0gRnJvc3Q6ICM4RkJDQkIsICM4OEMwRDAsICM4MUExQzEgLS0+CiAgCiAgPHJlY3Qgd2lkdGg9IjEwMCIgaGVpZ2h0PSIxMDAiIHJ4PSIxNSIgZmlsbD0iI0VDRUZGNCIvPgogIAogIDwhLS0gQ29nd2hlZWwgKEdhbWUgRW5naW5lKSAtLT4KICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSg1MCwgNTApIiBmaWxsPSIjODFBMUMxIj4KICAgIDxwYXRoIGQ9Ik0tMzAsLTggTC00MCwtOCBMLTQwLDggTC0zMCw4IEEzMCwzMCAwIDAsMCAtMjEuMiwyMS4yIEwtMjYuOCwyNi44IEwtMTUuNSwzOC4yIEwtMTAsMzIuNSBBMzAsMzAgMCAwLDAgMTAsMzIuNSBMMTUuNSwzOC4yIEwyNi44LDI2LjggTDIxLjIsMjEuMiBBMzAsMzAgMCAwLDAgMzAsOCBMNDAsOCBMNDAsLTggTDMwLC04IEEzMCwzMCAwIDAsMCAyMS4yLC0yMS4yIEwyNi44LC0yNi44IEwxNS41LC0zOC4yIEwxMCwtMzIuNSBBMzAsMzAgMCAwLDAgLTEwLC0zMi41IEwtMTUuNSwtMzguMiBMLTI2LjgsLTI2LjggTC0yMS4yLC0yMS4yIEEzMCwzMCAwIDAsMCAtMzAsLTggWiIgLz4KICAgIDxjaXJjbGUgcj0iMjIiIGZpbGw9IiNFQ0VGRjQiLz4KICA8L2c+CgogIDwhLS0gVGlueSBSb2JvdCAoQUkpIC0tPgogIDxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDUwLCA1MikiPgogICAgPCEtLSBCb2R5IC0tPgogICAgPHJlY3QgeD0iLTEyIiB5PSItMTAiIHdpZHRoPSIyNCIgaGVpZ2h0PSIxOCIgcng9IjQiIGZpbGw9IiM4OEMwRDAiLz4KICAgIDwhLS0gQW50ZW5uYSAtLT4KICAgIDxsaW5lIHgxPSIwIiB5MT0iLTEwIiB4Mj0iMCIgeTI9Ii0xNiIgc3Ryb2tlPSIjNEM1NjZBIiBzdHJva2Utd2lkdGg9IjIiLz4KICAgIDxjaXJjbGUgY3g9IjAiIGN5PSItMTciIHI9IjIiIGZpbGw9IiNCRjYxNkEiLz4KICAgIDwhLS0gRXllcyAtLT4KICAgIDxjaXJjbGUgY3g9Ii01IiBjeT0iLTQiIHI9IjIiIGZpbGw9IiNFQ0VGRjQiLz4KICAgIDxjaXJjbGUgY3g9IjUiIGN5PSItNCIgcj0iMiIgZmlsbD0iI0VDRUZGNCIvPgogICAgPCEtLSBNb3V0aCAtLT4KICAgIDxyZWN0IHg9Ii00IiB5PSIyIiB3aWR0aD0iOCIgaGVpZ2h0PSIxLjUiIHJ4PSIxIiBmaWxsPSIjNEM1NjZBIi8+CiAgPC9nPgo8L3N2Zz4K" alt="AI Game Framework logo" width="128" height="128" align="middle"> AI Game Framework (aigf)

[![PyPI - Version](https://img.shields.io/badge/pypi-v1.0.0-blue)](https://pypi.org/project/ai-game-framework)
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://pypi.org/project/ai-game-framework)
[![GitHub License](https://img.shields.io/github/license/mariolpantunes/ai-game-framework)](LICENSE)
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/mariolpantunes/ai-game-framework/main.yml)](https://github.com/mariolpantunes/ai-game-framework/actions)

An elegant, high-performance, asynchronous Python library designed to streamline the development, testing, and optimization of AI agents in both real-time and discrete-time games.

Inspired by modern web micro-frameworks like **FastAPI** and **Flask**, `aigf` allows developers to build games using clean functional decorators or object-oriented classes. It bundles a fully integrated lightweight HTTP/WebSocket server that automatically serves custom visualizers along with packaged styling (`nord.css`) and client-side logic (`framework.js`).

---

## Features

1. **Lightweight & High Performance**: Utilizes `websockets` and async/await event loops to easily handle large volumes of concurrent agents (perfect for neuroevolution or RL optimization).
2. **Flexible API Models**:
   * **Decorated Hooks (`AIGameServer`)**: FastAPI/Flask style callbacks for connection, action, tick, and state-retrieval events.
   * **Class Inheritance (`GameInterface`)**: Rigid Object-Oriented structure for strict architectural isolation.
3. **Zero-Dependency Web Server**: Houses an integrated static asset server, letting developers serve a rich HTML/JS/CSS frontend directly from Python.
4. **Pre-packaged UI Ecosystem**: Standardized layout sheets (`nord.css`) and event handlers (`framework.js`) are packaged inside the wheel distribution and served natively.
5. **No Docker Required**: Run natively on host machines inside virtual environments.

---

## Installation

Add it directly to your game project's `requirements.txt`:

```text
ai-game-framework >= 1.0.0
```

Or install it directly from source/PyPI:

```bash
pip install .
```

---

## How it Works: Webpage Integration

The framework handles HTTP requests through a specialized static file server routing mechanism. 
When a web browser connects to the server (e.g. `http://localhost:8765/`):
1. **HTML Serving**: The server checks the game's `viewer/` or `frontend/` directory for an `index.html` file and serves it as the root webpage.
2. **Asset Bundling**: The custom HTML imports `/aigf/framework.js` or `/aigf/nord.css`.
3. **Automatic Routing**: The framework's internal path resolver interceptor (`find_static_file`) catches requests starting with `/aigf/` or `/framework/` and automatically serves the embedded assets bundled inside the pip package wheel. No Nginx, complex volume binds, or system-wide assets are required!

```javascript
// Inside your viewer/index.html
import { GameClient } from "/aigf/framework.js";

// Instantiates a client connecting automatically to ws://localhost:8765/ws
const client = new GameClient(8765);

client.onUpdate((state) => {
  // Renders the real-time game state coordinates on canvas
  console.log("Visualizer Update:", state);
});
```

---

## Quick Start: Decorated Game Server

Creating a game server is exceptionally quick. Register game loops and player interactions with function annotations:

```python
from aigf.interface import AIGameServer, GameState

# 1. Initialize a real-time server operating at 30 FPS
app = AIGameServer(is_real_time=True, fps=30)
players = {}

# 2. Player handshake connector
@app.on_connect
async def connect(player_id: int):
    players[player_id] = {"x": 400.0, "y": 300.0, "score": 0}
    if len(players) >= 2:
        app.state = GameState.RUNNING

# 3. Real-time game tick
@app.on_tick
async def tick(dt: float):
    for p in players.values():
        p["x"] += 10.0 * dt  # Move players slightly right

# 4. Action receiver hook
@app.on_action
async def action(player_id: int, act: dict):
    if act.get("cmd") == "jump":
        players[player_id]["y"] -= 50.0

# 5. Visualizer state builder
@app.on_get_state
def get_state() -> dict:
    return {"players": list(players.values())}

# 6. Launch the server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765)
```

---

## Interactive Examples

The package includes two fully functioning, high-quality sample games demonstrating the API:

### 1. Dino Jump (Real-Time Game)
Located in `examples/dino_jump/`. Mimics Chrome's offline dinosaur game.
* **Start Server**: `python3 examples/dino_jump/main.py`
* **Play in Browser**: Open `http://localhost:8765/` (press Space to jump).
* **Play in Terminal**: Run `python3 examples/dino_jump/manual_agent.py`.

### 2. Hangman (Discrete/Turn-Based Game)
Located in `examples/hangman/`. A turn-based word-discovery game with zero ticks.
* **Start Server**: `python3 examples/hangman/main.py`
* **Play in Browser**: Open `http://localhost:8765/` (click or type letters).
* **Play in Terminal**: Run `python3 examples/hangman/manual_agent.py`.

---

## Running Unit Tests
Validate code changes using unittest:
```bash
python3 -m unittest discover -s tests
```

---

## Generating Documentation
The codebase utilizes Google-style docstrings. Build documentation into standard HTML using `pdoc`:
```bash
pip install pdoc
PYTHONPATH=src pdoc --math -d google -o docs_out aigf
```

---

## Authors

* **Mário Antunes** - [mariolpantunes](https://github.com/mariolpantunes)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
