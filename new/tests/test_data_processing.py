import pytest
import numpy as np
from datetime import datetime, timedelta
from data_processing.event_processor import EventProcessor
from data_processing.feature_extractor import FeatureExtractor
from data_processing.data_cleaner import DataCleaner
from data_processing.data_validator import DataValidator

@pytest.fixture
def event_processor():
    return EventProcessor(
        window_size=10,
        stride=1,
        max_events=1000
    )

@pytest.fixture
def feature_extractor():
    return FeatureExtractor(
        keystroke_features=['hold_time', 'flight_time', 'pressure'],
        mouse_features=['velocity', 'acceleration', 'pressure']
    )

@pytest.fixture
def data_cleaner():
    return DataCleaner(
        min_pressure=0.0,
        max_pressure=1.0,
        min_velocity=0.0,
        max_velocity=1000.0,
        min_acceleration=-1000.0,
        max_acceleration=1000.0
    )

@pytest.fixture
def data_validator():
    return DataValidator(
        required_fields=['timestamp', 'event_type', 'user_id'],
        valid_event_types=['keystroke', 'mouse'],
        valid_mouse_types=['move', 'click', 'drag']
    )

@pytest.fixture
def sample_keystroke_events():
    return [
        {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'keystroke',
            'user_id': 'test_user',
            'key': 'a',
            'press_time': 1.0,
            'release_time': 1.1,
            'pressure': 0.5,
            'x_coord': 100.0,
            'y_coord': 100.0
        }
    ]

@pytest.fixture
def sample_mouse_events():
    return [
        {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'mouse',
            'user_id': 'test_user',
            'event_type': 'move',
            'x_coord': 100.0,
            'y_coord': 100.0,
            'pressure': 0.5,
            'velocity': 1.0,
            'acceleration': 0.1
        }
    ]

def test_event_processor_initialization(event_processor):
    assert event_processor.window_size == 10
    assert event_processor.stride == 1
    assert event_processor.max_events == 1000
    assert event_processor.events == []
    assert event_processor.windows == []

def test_event_processing(event_processor, sample_keystroke_events):
    # Process events
    event_processor.process_events(sample_keystroke_events)
    assert len(event_processor.events) == len(sample_keystroke_events)
    
    # Create windows
    event_processor.create_windows()
    assert len(event_processor.windows) > 0
    assert len(event_processor.windows[0]) == event_processor.window_size

def test_event_window_creation(event_processor, sample_keystroke_events):
    # Add more events to test window creation
    events = sample_keystroke_events * 15
    event_processor.process_events(events)
    event_processor.create_windows()
    
    # Verify window properties
    assert len(event_processor.windows) == 6  # 15 events with window_size=10 and stride=1
    assert all(len(window) == event_processor.window_size for window in event_processor.windows)

def test_feature_extractor_initialization(feature_extractor):
    assert feature_extractor.keystroke_features == ['hold_time', 'flight_time', 'pressure']
    assert feature_extractor.mouse_features == ['velocity', 'acceleration', 'pressure']
    assert feature_extractor.scaler is not None

def test_keystroke_feature_extraction(feature_extractor, sample_keystroke_events):
    # Extract features
    features = feature_extractor.extract_keystroke_features(sample_keystroke_events)
    
    # Verify feature structure
    assert isinstance(features, np.ndarray)
    assert features.shape[0] == len(sample_keystroke_events)
    assert features.shape[1] == len(feature_extractor.keystroke_features)

def test_mouse_feature_extraction(feature_extractor, sample_mouse_events):
    # Extract features
    features = feature_extractor.extract_mouse_features(sample_mouse_events)
    
    # Verify feature structure
    assert isinstance(features, np.ndarray)
    assert features.shape[0] == len(sample_mouse_events)
    assert features.shape[1] == len(feature_extractor.mouse_features)

def test_data_cleaner_initialization(data_cleaner):
    assert data_cleaner.min_pressure == 0.0
    assert data_cleaner.max_pressure == 1.0
    assert data_cleaner.min_velocity == 0.0
    assert data_cleaner.max_velocity == 1000.0
    assert data_cleaner.min_acceleration == -1000.0
    assert data_cleaner.max_acceleration == 1000.0

def test_keystroke_data_cleaning(data_cleaner, sample_keystroke_events):
    # Add invalid data
    invalid_event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'keystroke',
        'user_id': 'test_user',
        'key': 'a',
        'press_time': 1.0,
        'release_time': 1.1,
        'pressure': 1.5,  # Invalid pressure
        'x_coord': 100.0,
        'y_coord': 100.0
    }
    
    events = sample_keystroke_events + [invalid_event]
    
    # Clean data
    cleaned_events = data_cleaner.clean_keystroke_data(events)
    assert len(cleaned_events) == len(sample_keystroke_events)  # Invalid event should be removed
    assert all(0 <= event['pressure'] <= 1 for event in cleaned_events)

def test_mouse_data_cleaning(data_cleaner, sample_mouse_events):
    # Add invalid data
    invalid_event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'mouse',
        'user_id': 'test_user',
        'event_type': 'move',
        'x_coord': 100.0,
        'y_coord': 100.0,
        'pressure': 1.5,  # Invalid pressure
        'velocity': 2000.0,  # Invalid velocity
        'acceleration': 2000.0  # Invalid acceleration
    }
    
    events = sample_mouse_events + [invalid_event]
    
    # Clean data
    cleaned_events = data_cleaner.clean_mouse_data(events)
    assert len(cleaned_events) == len(sample_mouse_events)  # Invalid event should be removed
    assert all(0 <= event['pressure'] <= 1 for event in cleaned_events)
    assert all(0 <= event['velocity'] <= 1000 for event in cleaned_events)
    assert all(-1000 <= event['acceleration'] <= 1000 for event in cleaned_events)

def test_data_validator_initialization(data_validator):
    assert data_validator.required_fields == ['timestamp', 'event_type', 'user_id']
    assert data_validator.valid_event_types == ['keystroke', 'mouse']
    assert data_validator.valid_mouse_types == ['move', 'click', 'drag']

def test_event_validation(data_validator, sample_keystroke_events, sample_mouse_events):
    # Test valid events
    assert data_validator.validate_event(sample_keystroke_events[0]) is True
    assert data_validator.validate_event(sample_mouse_events[0]) is True
    
    # Test invalid event
    invalid_event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'invalid_type',
        'user_id': 'test_user'
    }
    assert data_validator.validate_event(invalid_event) is False

def test_mouse_event_validation(data_validator):
    # Test valid mouse event types
    valid_event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'mouse',
        'user_id': 'test_user',
        'event_type': 'move'
    }
    assert data_validator.validate_mouse_event(valid_event) is True
    
    # Test invalid mouse event type
    invalid_event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'mouse',
        'user_id': 'test_user',
        'event_type': 'invalid_type'
    }
    assert data_validator.validate_mouse_event(invalid_event) is False

def test_data_processing_error_handling(event_processor, feature_extractor, data_cleaner, data_validator):
    # Test event processor error handling
    with pytest.raises(ValueError):
        event_processor.window_size = 0
    
    # Test feature extractor error handling
    with pytest.raises(ValueError):
        feature_extractor.extract_keystroke_features([])
    
    # Test data cleaner error handling
    with pytest.raises(ValueError):
        data_cleaner.min_pressure = 1.5
    
    # Test data validator error handling
    with pytest.raises(ValueError):
        data_validator.validate_event({})

def test_data_processing_cleanup(event_processor, feature_extractor, data_cleaner, data_validator):
    # Test cleanup
    event_processor.cleanup()
    feature_extractor.cleanup()
    data_cleaner.cleanup()
    data_validator.cleanup()
    
    # No assertions needed as we're just testing the method calls 