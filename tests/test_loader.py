import os
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from framework.main import app

@pytest.fixture
def client():
    # Set env var for testing
    os.environ["GAME_CLASS"] = "tests.test_interface.MockGame"
    with TestClient(app) as c:
        yield c

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"
    # Note: Game loading might happen on startup event which TestClient handles with 'with'
    assert response.json()["game_loaded"] is True

def test_websocket_invalid_client(client):
    try:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"client": "invalid"})
            websocket.receive_json() # This should trigger closure detection
    except WebSocketDisconnect:
        pass
