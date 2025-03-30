import pytest
import numpy as np
from datetime import datetime, timedelta
from utils.data_processing import (
    calculate_statistics,
    normalize_data,
    create_windows,
    calculate_velocity,
    calculate_acceleration
)
from utils.time_utils import (
    get_timestamp,
    format_timestamp,
    parse_timestamp,
    calculate_duration,
    is_timestamp_valid
)
from utils.validation import (
    validate_event_data,
    validate_risk_score,
    validate_coordinates,
    validate_pressure,
    validate_timestamp
)
from utils.encryption import (
    encrypt_data,
    decrypt_data,
    generate_key,
    hash_password,
    verify_password
)

@pytest.fixture
def sample_data():
    return np.array([1.0, 2.0, 3.0, 4.0, 5.0])

@pytest.fixture
def sample_coordinates():
    return np.array([
        [0.0, 0.0],
        [1.0, 1.0],
        [2.0, 2.0],
        [3.0, 3.0],
        [4.0, 4.0]
    ])

@pytest.fixture
def sample_timestamps():
    return [
        datetime.now().isoformat(),
        (datetime.now() + timedelta(seconds=1)).isoformat(),
        (datetime.now() + timedelta(seconds=2)).isoformat()
    ]

def test_calculate_statistics(sample_data):
    stats = calculate_statistics(sample_data)
    assert stats['mean'] == 3.0
    assert stats['std'] == 1.4142135623730951
    assert stats['min'] == 1.0
    assert stats['max'] == 5.0
    assert stats['median'] == 3.0

def test_normalize_data(sample_data):
    normalized = normalize_data(sample_data)
    assert len(normalized) == len(sample_data)
    assert np.all(normalized >= -1) and np.all(normalized <= 1)
    assert np.mean(normalized) == pytest.approx(0.0, rel=1e-10)
    assert np.std(normalized) == pytest.approx(1.0, rel=1e-10)

def test_create_windows(sample_data):
    windows = create_windows(sample_data, window_size=3, stride=1)
    assert windows.shape == (3, 3)
    assert np.array_equal(windows[0], np.array([1.0, 2.0, 3.0]))
    assert np.array_equal(windows[1], np.array([2.0, 3.0, 4.0]))
    assert np.array_equal(windows[2], np.array([3.0, 4.0, 5.0]))

def test_calculate_velocity(sample_coordinates, sample_timestamps):
    velocities = calculate_velocity(sample_coordinates, sample_timestamps)
    assert len(velocities) == len(sample_coordinates) - 1
    assert np.all(velocities >= 0)  # All velocities should be positive
    assert np.all(np.isfinite(velocities))  # All velocities should be finite

def test_calculate_acceleration(sample_coordinates, sample_timestamps):
    velocities = calculate_velocity(sample_coordinates, sample_timestamps)
    accelerations = calculate_acceleration(velocities, sample_timestamps)
    assert len(accelerations) == len(velocities) - 1
    assert np.all(np.isfinite(accelerations))  # All accelerations should be finite

def test_get_timestamp():
    timestamp = get_timestamp()
    assert isinstance(timestamp, str)
    assert is_timestamp_valid(timestamp)

def test_format_timestamp():
    dt = datetime.now()
    formatted = format_timestamp(dt)
    assert isinstance(formatted, str)
    assert is_timestamp_valid(formatted)

def test_parse_timestamp():
    timestamp = datetime.now().isoformat()
    parsed = parse_timestamp(timestamp)
    assert isinstance(parsed, datetime)
    assert parsed.isoformat() == timestamp

def test_calculate_duration():
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=5)
    duration = calculate_duration(start_time, end_time)
    assert duration == 5.0

def test_is_timestamp_valid():
    valid_timestamp = datetime.now().isoformat()
    invalid_timestamp = "invalid_timestamp"
    
    assert is_timestamp_valid(valid_timestamp) is True
    assert is_timestamp_valid(invalid_timestamp) is False

def test_validate_event_data():
    valid_event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'keystroke',
        'user_id': 'test_user',
        'data': {'key': 'a', 'pressure': 0.5}
    }
    
    invalid_event = {
        'timestamp': 'invalid',
        'event_type': 'invalid_type',
        'user_id': '',
        'data': {}
    }
    
    assert validate_event_data(valid_event) is True
    assert validate_event_data(invalid_event) is False

def test_validate_risk_score():
    assert validate_risk_score(0.0) is True
    assert validate_risk_score(50.0) is True
    assert validate_risk_score(100.0) is True
    assert validate_risk_score(-1.0) is False
    assert validate_risk_score(101.0) is False

def test_validate_coordinates():
    valid_coords = (100.0, 100.0)
    invalid_coords = (-1.0, -1.0)
    
    assert validate_coordinates(valid_coords) is True
    assert validate_coordinates(invalid_coords) is False

def test_validate_pressure():
    assert validate_pressure(0.0) is True
    assert validate_pressure(0.5) is True
    assert validate_pressure(1.0) is True
    assert validate_pressure(-0.1) is False
    assert validate_pressure(1.1) is False

def test_validate_timestamp():
    valid_timestamp = datetime.now().isoformat()
    invalid_timestamp = "invalid_timestamp"
    
    assert validate_timestamp(valid_timestamp) is True
    assert validate_timestamp(invalid_timestamp) is False

def test_encryption_decryption():
    data = "sensitive_data"
    key = generate_key()
    
    encrypted = encrypt_data(data, key)
    decrypted = decrypt_data(encrypted, key)
    
    assert encrypted != data
    assert decrypted == data
    assert isinstance(encrypted, bytes)
    assert isinstance(decrypted, str)

def test_password_hashing():
    password = "test_password"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    assert hashed != password
    assert isinstance(hashed, str)

def test_utility_error_handling():
    # Test invalid data for statistics
    with pytest.raises(ValueError):
        calculate_statistics(np.array([]))
    
    # Test invalid window size
    with pytest.raises(ValueError):
        create_windows(np.array([1, 2, 3]), window_size=0, stride=1)
    
    # Test invalid coordinates
    with pytest.raises(ValueError):
        calculate_velocity(np.array([]), [])
    
    # Test invalid timestamps
    with pytest.raises(ValueError):
        calculate_duration(None, datetime.now())
    
    # Test invalid encryption key
    with pytest.raises(ValueError):
        encrypt_data("data", None)
    
    # Test invalid password
    with pytest.raises(ValueError):
        hash_password(None) 