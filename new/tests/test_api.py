import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import json
from api.main import app

client = TestClient(app)

@pytest.fixture
def sample_keystroke_event():
    return {
        'key': 'a',
        'press_time': 1.0,
        'release_time': 1.1,
        'pressure': 0.5,
        'x_coord': 100.0,
        'y_coord': 100.0,
        'timestamp': datetime.now().isoformat()
    }

@pytest.fixture
def sample_mouse_event():
    return {
        'event_type': 'move',
        'x_coord': 100.0,
        'y_coord': 100.0,
        'pressure': 0.5,
        'timestamp': datetime.now().isoformat(),
        'velocity': 1.0,
        'acceleration': 0.1
    }

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_keystroke_event_endpoint(sample_keystroke_event):
    response = client.post(
        "/api/v1/events/keystroke",
        json=sample_keystroke_event
    )
    assert response.status_code == 200
    data = response.json()
    assert 'risk_score' in data
    assert 'risk_level' in data
    assert 'has_drift' in data
    assert 'action_taken' in data
    assert 'timestamp' in data

def test_mouse_event_endpoint(sample_mouse_event):
    response = client.post(
        "/api/v1/events/mouse",
        json=sample_mouse_event
    )
    assert response.status_code == 200
    data = response.json()
    assert 'risk_score' in data
    assert 'risk_level' in data
    assert 'has_drift' in data
    assert 'action_taken' in data
    assert 'timestamp' in data

def test_session_status_endpoint():
    user_id = "test_user"
    response = client.get(f"/api/v1/sessions/{user_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert 'user_id' in data
    assert 'start_time' in data
    assert 'current_risk' in data
    assert 'risk_level' in data
    assert 'has_drift' in data
    assert 'event_count' in data
    assert 'is_blocked' in data

def test_end_session_endpoint():
    user_id = "test_user"
    response = client.post(f"/api/v1/sessions/{user_id}/end")
    assert response.status_code == 200
    data = response.json()
    assert 'session_data' in data
    assert 'forensic_data' in data
    assert 'end_time' in data

def test_risk_levels_endpoint():
    response = client.get("/api/v1/risk-levels")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert 'critical' in data
    assert 'high' in data
    assert 'medium' in data
    assert 'low' in data

def test_invalid_keystroke_event():
    invalid_event = {
        'key': 'a',
        'press_time': 'invalid',  # Should be float
        'release_time': 1.1,
        'pressure': 0.5,
        'x_coord': 100.0,
        'y_coord': 100.0,
        'timestamp': datetime.now().isoformat()
    }
    response = client.post(
        "/api/v1/events/keystroke",
        json=invalid_event
    )
    assert response.status_code == 422  # Validation error

def test_invalid_mouse_event():
    invalid_event = {
        'event_type': 'invalid_type',  # Invalid event type
        'x_coord': 100.0,
        'y_coord': 100.0,
        'pressure': 0.5,
        'timestamp': datetime.now().isoformat(),
        'velocity': 1.0,
        'acceleration': 0.1
    }
    response = client.post(
        "/api/v1/events/mouse",
        json=invalid_event
    )
    assert response.status_code == 422  # Validation error

def test_websocket_connection():
    with client.websocket_connect("/ws") as websocket:
        # Send a test event
        test_event = {
            'type': 'keystroke',
            'data': {
                'key': 'a',
                'press_time': 1.0,
                'release_time': 1.1,
                'pressure': 0.5,
                'x_coord': 100.0,
                'y_coord': 100.0,
                'timestamp': datetime.now().isoformat()
            }
        }
        websocket.send_json(test_event)
        
        # Receive response
        response = websocket.receive_json()
        assert 'risk_score' in response
        assert 'risk_level' in response
        assert 'has_drift' in response
        assert 'action_taken' in response
        assert 'timestamp' in response

def test_websocket_invalid_event():
    with client.websocket_connect("/ws") as websocket:
        # Send an invalid event
        invalid_event = {
            'type': 'invalid_type',
            'data': {}
        }
        websocket.send_json(invalid_event)
        
        # Receive error response
        response = websocket.receive_json()
        assert 'error' in response
        assert response['error'] == "Invalid event type"

def test_websocket_disconnect():
    with client.websocket_connect("/ws") as websocket:
        # Send disconnect event
        disconnect_event = {
            'type': 'disconnect',
            'data': {}
        }
        websocket.send_json(disconnect_event)
        
        # Connection should be closed
        with pytest.raises(Exception):
            websocket.receive_json() 