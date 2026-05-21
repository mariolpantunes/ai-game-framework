export class GameClient {
  /**
   * Initializes the GameClient and connects to the framework.
   * @param {number} port - The port the framework backend is running on (default 8765).
   */
  constructor(port = 8765) {
    this.ws = null;
    this.port = port;
    this.onUpdate = null;
    this.onSetup = null;
    this.onAgentConnect = null;
    this.onAgentDisconnect = null;
    
    this.agents = [];
    this.gameState = "LOBBY";

    this.connect();
  }

  /**
   * Establishes the WebSocket connection.
   */
  connect() {
    const serverHost = window.location.hostname || "localhost";
    this.ws = new WebSocket(`ws://${serverHost}:${this.port}/ws`);

    this.ws.onopen = () => {
      console.log("Connected to AI Game Framework.");
      this.ws.send(JSON.stringify({ client: "frontend" }));
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === "update") {
        this._handleFrameworkData(data._framework);
        if (this.onUpdate) this.onUpdate(data);
      } else if (data.type === "setup") {
        if (this.onSetup) this.onSetup(data);
      }
    };

    this.ws.onclose = () => {
      console.log("Disconnected from framework. Retrying in 2s...");
      setTimeout(() => this.connect(), 2000);
    };

    this.ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };
  }

  /**
   * Handles internal framework metadata (agents, game state).
   * @private
   */
  _handleFrameworkData(frameworkData) {
    if (!frameworkData) return;

    const newAgents = frameworkData.agents || [];
    const newState = frameworkData.state || "LOBBY";

    // Detect agent connections/disconnections
    newAgents.forEach(id => {
        if (!this.agents.includes(id)) {
            if (this.onAgentConnect) this.onAgentConnect(id);
        }
    });

    this.agents.forEach(id => {
        if (!newAgents.includes(id)) {
            if (this.onAgentDisconnect) this.onAgentDisconnect(id);
        }
    });

    this.agents = newAgents;
    this.gameState = newState;
  }

  /**
   * Sends an action or command to the backend.
   * @param {Object} action - The JSON payload to send.
   */
  sendAction(action) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(action));
    }
  }

  /**
   * Utility to send a system command (e.g. START, RESET).
   * @param {string} cmd 
   */
  sendCommand(cmd) {
      this.sendAction({ command: cmd });
  }
}
