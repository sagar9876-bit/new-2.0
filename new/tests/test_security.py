import pytest
import asyncio
from datetime import datetime, timedelta
from security.risk_engine import RiskEngine
from security.response_system import ResponseSystem
from core.behavioral_analysis.keystroke_analyzer_v2 import KeystrokeEvent
from core.behavioral_analysis.mouse_analyzer_v2 import MouseEvent

@pytest.fixture
def risk_engine():
    return RiskEngine(ad_integration=False, siem_endpoint=None)

@pytest.fixture
def response_system():
    return ResponseSystem()

@pytest.fixture
def sample_keystroke_event():
    return {
        'key': 'a',
        'press_time': 1.0,
        'release_time': 1.1,
        'pressure': 0.5,
        'x_coord': 100.0,
        'y_coord': 100.0,
        'timestamp': datetime.now()
    }

@pytest.fixture
def sample_mouse_event():
    return {
        'event_type': 'move',
        'x_coord': 100.0,
        'y_coord': 100.0,
        'pressure': 0.5,
        'timestamp': datetime.now(),
        'velocity': 1.0,
        'acceleration': 0.1
    }

def test_risk_engine_initialization(risk_engine):
    assert risk_engine.context_processor is not None
    assert risk_engine.ad_integration is False
    assert risk_engine.siem_endpoint is None
    assert isinstance(risk_engine.risk_thresholds, dict)
    assert isinstance(risk_engine.active_sessions, dict)
    assert isinstance(risk_engine.blocked_users, list)

def test_risk_engine_process_event(risk_engine, sample_keystroke_event):
    user_id = "test_user"
    result = risk_engine.process_event(user_id, 'keystroke', sample_keystroke_event)
    
    assert isinstance(result, dict)
    assert 'risk_score' in result
    assert 'risk_level' in result
    assert 'has_drift' in result
    assert 'action_taken' in result
    assert 'timestamp' in result

def test_risk_engine_session_management(risk_engine, sample_keystroke_event):
    user_id = "test_user"
    
    # Process some events
    for _ in range(5):
        risk_engine.process_event(user_id, 'keystroke', sample_keystroke_event)
    
    # Get session status
    status = risk_engine.get_session_status(user_id)
    assert status['user_id'] == user_id
    assert 'start_time' in status
    assert 'current_risk' in status
    assert 'risk_level' in status
    assert 'has_drift' in status
    assert 'event_count' in status
    assert 'is_blocked' in status
    
    # End session
    session_data = risk_engine.end_session(user_id)
    assert isinstance(session_data, dict)
    assert 'session_data' in session_data
    assert 'forensic_data' in session_data
    assert 'end_time' in session_data

def test_response_system_initialization(response_system):
    assert response_system.risk_thresholds is not None
    assert response_system.actions is not None
    assert isinstance(response_system.active_responses, dict)
    assert isinstance(response_system.notification_queue, asyncio.Queue)

@pytest.mark.asyncio
async def test_response_system_risk_handling(response_system):
    user_id = "test_user"
    
    # Test critical risk
    critical_result = await response_system.handle_risk_level(user_id, 'critical', 95.0)
    assert critical_result['risk_level'] == 'critical'
    assert 'actions_taken' in critical_result
    
    # Test high risk
    high_result = await response_system.handle_risk_level(user_id, 'high', 75.0)
    assert high_result['risk_level'] == 'high'
    assert 'actions_taken' in high_result
    
    # Test medium risk
    medium_result = await response_system.handle_risk_level(user_id, 'medium', 50.0)
    assert medium_result['risk_level'] == 'medium'
    assert 'actions_taken' in medium_result
    
    # Test low risk
    low_result = await response_system.handle_risk_level(user_id, 'low', 25.0)
    assert low_result['risk_level'] == 'low'
    assert 'actions_taken' in low_result

@pytest.mark.asyncio
async def test_response_system_notifications(response_system):
    user_id = "test_user"
    
    # Queue a notification
    await response_system._notify_admin(user_id, 'high', 75.0)
    
    # Start notification processor
    await response_system.start()
    
    # Wait for notification to be processed
    await asyncio.sleep(0.1)
    
    # Stop the system
    await response_system.stop()

def test_response_system_active_responses(response_system):
    user_id = "test_user"
    
    # Add some active responses
    response_system.active_responses[user_id] = [
        {'action': 'increase_monitoring', 'timestamp': datetime.now().isoformat()}
    ]
    
    # Get active responses
    responses = response_system.get_active_responses(user_id)
    assert len(responses) == 1
    assert responses[0]['action'] == 'increase_monitoring'

@pytest.mark.asyncio
async def test_response_system_cleanup(response_system):
    user_id = "test_user"
    
    # Add some active responses
    response_system.active_responses[user_id] = [
        {'action': 'increase_monitoring', 'timestamp': datetime.now().isoformat()}
    ]
    
    # Clean up responses
    await response_system.cleanup_responses(user_id)
    assert user_id not in response_system.active_responses 