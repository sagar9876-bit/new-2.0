import pytest
import numpy as np
from datetime import datetime, timedelta
from core.behavioral_analysis.keystroke_analyzer_v2 import KeystrokeAnalyzer, KeystrokeEvent
from core.behavioral_analysis.mouse_analyzer_v2 import MouseAnalyzer, MouseEvent
from core.behavioral_analysis.context_processor import ContextProcessor

@pytest.fixture
def keystroke_analyzer():
    return KeystrokeAnalyzer()

@pytest.fixture
def mouse_analyzer():
    return MouseAnalyzer()

@pytest.fixture
def context_processor():
    return ContextProcessor()

@pytest.fixture
def sample_keystroke_events():
    return [
        KeystrokeEvent(
            key='a',
            press_time=1.0,
            release_time=1.1,
            pressure=0.5,
            x_coord=100.0,
            y_coord=100.0,
            timestamp=datetime.now()
        ),
        KeystrokeEvent(
            key='b',
            press_time=1.2,
            release_time=1.3,
            pressure=0.6,
            x_coord=150.0,
            y_coord=150.0,
            timestamp=datetime.now() + timedelta(seconds=0.1)
        )
    ]

@pytest.fixture
def sample_mouse_events():
    return [
        MouseEvent(
            event_type='move',
            x_coord=100.0,
            y_coord=100.0,
            pressure=0.5,
            timestamp=datetime.now(),
            velocity=1.0,
            acceleration=0.1
        ),
        MouseEvent(
            event_type='click',
            x_coord=150.0,
            y_coord=150.0,
            pressure=0.6,
            timestamp=datetime.now() + timedelta(seconds=0.1),
            velocity=1.2,
            acceleration=0.2
        )
    ]

def test_keystroke_analyzer_initialization(keystroke_analyzer):
    assert keystroke_analyzer.model is not None
    assert keystroke_analyzer.scaler is not None
    assert keystroke_analyzer.neural_net is not None

def test_keystroke_feature_extraction(keystroke_analyzer, sample_keystroke_events):
    features = keystroke_analyzer.extract_features(sample_keystroke_events)
    assert isinstance(features, np.ndarray)
    assert features.shape[0] > 0
    assert features.shape[1] > 0

def test_keystroke_risk_score(keystroke_analyzer, sample_keystroke_events):
    risk_score = keystroke_analyzer.calculate_risk_score(sample_keystroke_events)
    assert isinstance(risk_score, float)
    assert 0 <= risk_score <= 100

def test_mouse_analyzer_initialization(mouse_analyzer):
    assert mouse_analyzer.model is not None
    assert mouse_analyzer.scaler is not None
    assert mouse_analyzer.neural_net is not None

def test_mouse_feature_extraction(mouse_analyzer, sample_mouse_events):
    features = mouse_analyzer.extract_features(sample_mouse_events)
    assert isinstance(features, np.ndarray)
    assert features.shape[0] > 0
    assert features.shape[1] > 0

def test_mouse_risk_score(mouse_analyzer, sample_mouse_events):
    risk_score = mouse_analyzer.calculate_risk_score(sample_mouse_events)
    assert isinstance(risk_score, float)
    assert 0 <= risk_score <= 100

def test_context_processor_initialization(context_processor):
    assert context_processor.keystroke_analyzer is not None
    assert context_processor.mouse_analyzer is not None
    assert isinstance(context_processor.session_history, dict)
    assert isinstance(context_processor.risk_scores, dict)

def test_context_processor_keystroke_event(context_processor, sample_keystroke_events):
    user_id = "test_user"
    for event in sample_keystroke_events:
        result = context_processor.process_keystroke_event(user_id, event)
        assert isinstance(result, dict)
        assert 'risk_score' in result
        assert 'has_drift' in result

def test_context_processor_mouse_event(context_processor, sample_mouse_events):
    user_id = "test_user"
    for event in sample_mouse_events:
        result = context_processor.process_mouse_event(user_id, event)
        assert isinstance(result, dict)
        assert 'risk_score' in result
        assert 'has_drift' in result

def test_context_processor_risk_score_update(context_processor, sample_keystroke_events, sample_mouse_events):
    user_id = "test_user"
    
    # Process some events
    for event in sample_keystroke_events:
        context_processor.process_keystroke_event(user_id, event)
    
    for event in sample_mouse_events:
        context_processor.process_mouse_event(user_id, event)
    
    # Check risk score
    assert user_id in context_processor.risk_scores
    assert isinstance(context_processor.risk_scores[user_id], float)
    assert 0 <= context_processor.risk_scores[user_id] <= 100

def test_context_processor_behavioral_drift(context_processor, sample_keystroke_events):
    user_id = "test_user"
    
    # Process normal events
    for event in sample_keystroke_events:
        context_processor.process_keystroke_event(user_id, event)
    
    # Create anomalous event
    anomalous_event = KeystrokeEvent(
        key='x',
        press_time=5.0,  # Much longer than normal
        release_time=5.5,
        pressure=0.9,  # Much higher than normal
        x_coord=200.0,
        y_coord=200.0,
        timestamp=datetime.now() + timedelta(seconds=1)
    )
    
    # Process anomalous event
    result = context_processor.process_keystroke_event(user_id, anomalous_event)
    assert result['has_drift'] is True

def test_context_processor_session_management(context_processor, sample_keystroke_events):
    user_id = "test_user"
    
    # Process some events
    for event in sample_keystroke_events:
        context_processor.process_keystroke_event(user_id, event)
    
    # End session
    session_data = context_processor.end_session(user_id)
    assert isinstance(session_data, dict)
    assert 'session_data' in session_data
    assert 'forensic_data' in session_data
    assert 'end_time' in session_data
    
    # Verify session is ended
    assert user_id not in context_processor.session_history
    assert user_id not in context_processor.risk_scores 