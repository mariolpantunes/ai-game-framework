# <img src="assets/logo.svg" alt="AI Game Framework logo" width="128" height="128" align="middle"> AI Game Framework

![Python Version](https://img.shields.io/badge/python-3.14-blue)
![GitHub License](https://img.shields.io/github/license/mariolpantunes/ai-game-framework)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/mariolpantunes/ai-game-framework/main.yml)
![GitHub last commit](https://img.shields.io/github/last-commit/mariolpantunes/ai-game-framework)

**AI Game Framework** is a unified infrastructure designed to support the development and optimization of AI agents across various games. It abstracts the communication scaffolding (WebSockets, FastAPI) and provides a clean, 2-state API (`LOBBY` and `RUNNING`) to handle both real-time and discrete-time simulations.

## Core Principles

1.  **Strict Volume Isolation**: Neither game logic nor framework logic is baked into Docker images. All code is injected at runtime via volumes.
2.  **Universal Scaffolding**: One centralized FastAPI/WebSocket backend supports unlimited agents and exactly one visualization frontend.
3.  **Performance Optimized**: Uses `orjson` and asynchronous I/O to support large agent populations (e.g., neuroevolution) on a single core.
4.  **Neuroevolution Ready**: Supports dynamic agent joining and explicit lifecycle states to synchronize Blind Optimization generations.

## Structure

### Framework Repository
```text
ai-game-framework/
├── compose.yml          # Base service definition
├── Dockerfile           # Python runtime + framework dependencies
├── entrypoint.sh        # Runtime dependency installer
├── framework/           # Core Python package
└── frontend/            # Unified JS WebSocket client
```

### Game Project (Submodule Integration)
```text
game-repo/
├── agents/              # Student/Agent scripts
├── framework/           # Git Submodule -> ai-game-framework
├── game/                # Isolated game logic (Python/HTML/JS)
└── compose.yml          # Overrides and Volume mappings
```

## API Overview

### Backend (`GameInterface`)
Games must implement the `GameInterface` to handle actions and state:

```python
from framework import GameInterface, GameState

class MyGame(GameInterface):
    async def on_player_connect(self, player_id):
        # Decide when to start the game
        if len(self.players) == 100:
            self.state = GameState.RUNNING

    async def tick(self, dt):
        # Update physics/logic every frame
        pass

    def get_state(self):
        # Return full state for frontend
        return {"birds": [...]}
```

### Frontend (`GameClient`)
The frontend visualization uses a simple event-based client:

```javascript
import { GameClient } from "/framework/framework.js";

const client = new GameClient();
client.onUpdate((state) => {
    // Draw state to Canvas
});
```

## Installation

Add this framework as a git submodule to your project:

```bash
git submodule add https://github.com/mariolpantunes/ai-game-framework framework
```

Then, include the framework's configuration in your `compose.yml`:

```yaml
include:
  - framework/compose.yml
```

## Documentation

The library uses standard Python docstrings. To generate documentation locally:

```bash
pdoc --math -d google -o docs framework
```

## Authors

  * **Mário Antunes** - [mariolpantunes](https://github.com/mariolpantunes)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
