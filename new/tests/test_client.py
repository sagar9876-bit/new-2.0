import pytest
import asyncio
from datetime import datetime
from examples.client import BehavioralClient

@pytest.fixture
def client():
    return BehavioralClient(
        server_url="ws://localhost:8000/ws",
        api_url="http://localhost:8000/api/v1"
    )

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

@pytest.mark.asyncio
async def test_client_initialization(client):
    assert client.server_url == "ws://localhost:8000/ws"
    assert client.api_url == "http://localhost:8000/api/v1"
    assert client.websocket is None
    assert client.session_id is None
    assert client.is_connected is False
    assert client.event_queue is not None
    assert client.response_queue is not None

@pytest.mark.asyncio
async def test_client_connection(client):
    # Mock server connection
    client.websocket = type('MockWebSocket', (), {
        'send_json': lambda x: None,
        'receive_json': lambda: {'status': 'connected'}
    })
    
    await client.connect()
    assert client.is_connected is True
    assert client.session_id is not None

@pytest.mark.asyncio
async def test_client_disconnection(client):
    # Mock server connection
    client.websocket = type('MockWebSocket', (), {
        'close': lambda: None
    })
    client.is_connected = True
    client.session_id = "test_session"
    
    await client.disconnect()
    assert client.is_connected is False
    assert client.session_id is None
    assert client.websocket is None

@pytest.mark.asyncio
async def test_client_send_event(client, sample_keystroke_event):
    # Mock server connection
    client.websocket = type('MockWebSocket', (), {
        'send_json': lambda x: None,
        'receive_json': lambda: {
            'risk_score': 0.5,
            'risk_level': 'low',
            'has_drift': False,
            'action_taken': None,
            'timestamp': datetime.now().isoformat()
        }
    })
    client.is_connected = True
    client.session_id = "test_session"
    
    response = await client.send_event('keystroke', sample_keystroke_event)
    assert response['risk_score'] == 0.5
    assert response['risk_level'] == 'low'
    assert response['has_drift'] is False
    assert response['action_taken'] is None
    assert 'timestamp' in response

@pytest.mark.asyncio
async def test_client_get_status(client):
    # Mock API response
    client.session_id = "test_session"
    client._make_request = lambda x, y: {
        'user_id': 'test_user',
        'start_time': datetime.now().isoformat(),
        'current_risk': 0.5,
        'risk_level': 'low',
        'has_drift': False,
        'event_count': 10,
        'is_blocked': False
    }
    
    status = await client.get_status()
    assert status['user_id'] == 'test_user'
    assert 'start_time' in status
    assert status['current_risk'] == 0.5
    assert status['risk_level'] == 'low'
    assert status['has_drift'] is False
    assert status['event_count'] == 10
    assert status['is_blocked'] is False

@pytest.mark.asyncio
async def test_client_end_session(client):
    # Mock API response
    client.session_id = "test_session"
    client._make_request = lambda x, y: {
        'session_data': {
            'events': [],
            'risk_scores': []
        },
        'forensic_data': {
            'behavioral_indicators': [],
            'risk_metrics': {}
        },
        'end_time': datetime.now().isoformat()
    }
    
    session_data = await client.end_session()
    assert 'session_data' in session_data
    assert 'forensic_data' in session_data
    assert 'end_time' in session_data

@pytest.mark.asyncio
async def test_client_simulate_behavior(client):
    # Mock server connection
    client.websocket = type('MockWebSocket', (), {
        'send_json': lambda x: None,
        'receive_json': lambda: {
            'risk_score': 0.5,
            'risk_level': 'low',
            'has_drift': False,
            'action_taken': None,
            'timestamp': datetime.now().isoformat()
        }
    })
    client.is_connected = True
    client.session_id = "test_session"
    
    # Simulate some events
    await client.simulate_behavior(num_events=5)
    assert client.event_queue.qsize() == 5

@pytest.mark.asyncio
async def test_client_event_processing(client, sample_keystroke_event):
    # Mock server connection
    client.websocket = type('MockWebSocket', (), {
        'send_json': lambda x: None,
        'receive_json': lambda: {
            'risk_score': 0.5,
            'risk_level': 'low',
            'has_drift': False,
            'action_taken': None,
            'timestamp': datetime.now().isoformat()
        }
    })
    client.is_connected = True
    client.session_id = "test_session"
    
    # Process an event
    await client.event_queue.put(('keystroke', sample_keystroke_event))
    await client._process_events()
    assert client.response_queue.qsize() == 1

@pytest.mark.asyncio
async def test_client_error_handling(client):
    # Mock server connection with error
    client.websocket = type('MockWebSocket', (), {
        'send_json': lambda x: None,
        'receive_json': lambda: {'error': 'Test error'}
    })
    client.is_connected = True
    client.session_id = "test_session"
    
    # Send an event that will cause an error
    response = await client.send_event('keystroke', {})
    assert 'error' in response
    assert response['error'] == 'Test error'

@pytest.mark.asyncio
async def test_client_reconnection(client):
    # Mock server connection
    client.websocket = type('MockWebSocket', (), {
        'send_json': lambda x: None,
        'receive_json': lambda: {'status': 'connected'}
    })
    
    # Test reconnection
    await client.connect()
    assert client.is_connected is True
    
    # Simulate disconnection
    client.is_connected = False
    client.websocket = None
    
    # Reconnect
    await client.connect()
    assert client.is_connected is True
    assert client.websocket is not None 