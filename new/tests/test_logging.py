import pytest
import logging
import os
from datetime import datetime
from logging.log_manager import LogManager
from logging.audit_logger import AuditLogger
from logging.error_logger import ErrorLogger
from logging.performance_logger import PerformanceLogger

@pytest.fixture
def log_manager():
    return LogManager(
        log_dir="logs",
        log_level="INFO",
        log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        max_bytes=10485760,
        backup_count=5
    )

@pytest.fixture
def audit_logger():
    return AuditLogger(
        log_file="logs/audit.log",
        max_bytes=10485760,
        backup_count=5
    )

@pytest.fixture
def error_logger():
    return ErrorLogger(
        log_file="logs/error.log",
        max_bytes=10485760,
        backup_count=5
    )

@pytest.fixture
def performance_logger():
    return PerformanceLogger(
        log_file="logs/performance.log",
        max_bytes=10485760,
        backup_count=5
    )

def test_log_manager_initialization(log_manager):
    assert log_manager.log_dir == "logs"
    assert log_manager.log_level == "INFO"
    assert log_manager.log_format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    assert log_manager.max_bytes == 10485760
    assert log_manager.backup_count == 5
    assert log_manager.logger is not None

def test_log_manager_directory_creation(log_manager):
    # Test directory creation
    log_manager.create_log_directory()
    assert os.path.exists(log_manager.log_dir)
    
    # Clean up
    os.rmdir(log_manager.log_dir)

def test_log_manager_logger_creation(log_manager):
    # Test logger creation
    logger = log_manager.create_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.INFO
    assert len(logger.handlers) > 0

def test_audit_logger_initialization(audit_logger):
    assert audit_logger.log_file == "logs/audit.log"
    assert audit_logger.max_bytes == 10485760
    assert audit_logger.backup_count == 5
    assert audit_logger.logger is not None

def test_audit_logger_event_logging(audit_logger):
    # Test event logging
    event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'user_login',
        'user_id': 'test_user',
        'ip_address': '192.168.1.1',
        'status': 'success'
    }
    
    # Mock logger
    audit_logger.logger = type('MockLogger', (), {
        'info': lambda msg: None
    })
    
    # Test logging
    audit_logger.log_event(event)
    # No assertion needed as we're just testing the method call

def test_audit_logger_rotation(audit_logger):
    # Test log rotation
    audit_logger._rotate_logs = lambda: None
    audit_logger._check_rotation = lambda: None
    
    # Mock file size check
    audit_logger._get_file_size = lambda: 10485761  # Exceeds max_size
    
    # Test rotation
    audit_logger._check_rotation()
    # No assertion needed as we're just testing the method call

def test_error_logger_initialization(error_logger):
    assert error_logger.log_file == "logs/error.log"
    assert error_logger.max_bytes == 10485760
    assert error_logger.backup_count == 5
    assert error_logger.logger is not None

def test_error_logger_error_logging(error_logger):
    # Test error logging
    error = {
        'timestamp': datetime.now().isoformat(),
        'error_type': 'connection_error',
        'message': 'Failed to connect to database',
        'stack_trace': 'Traceback (most recent call last):\n...',
        'severity': 'ERROR'
    }
    
    # Mock logger
    error_logger.logger = type('MockLogger', (), {
        'error': lambda msg: None
    })
    
    # Test logging
    error_logger.log_error(error)
    # No assertion needed as we're just testing the method call

def test_error_logger_severity_levels(error_logger):
    # Test different severity levels
    severities = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    # Mock logger
    error_logger.logger = type('MockLogger', (), {
        'debug': lambda msg: None,
        'info': lambda msg: None,
        'warning': lambda msg: None,
        'error': lambda msg: None,
        'critical': lambda msg: None
    })
    
    # Test each severity level
    for severity in severities:
        error = {
            'timestamp': datetime.now().isoformat(),
            'error_type': 'test_error',
            'message': f'Test {severity.lower()} message',
            'stack_trace': 'Test stack trace',
            'severity': severity
        }
        error_logger.log_error(error)
        # No assertion needed as we're just testing the method call

def test_performance_logger_initialization(performance_logger):
    assert performance_logger.log_file == "logs/performance.log"
    assert performance_logger.max_bytes == 10485760
    assert performance_logger.backup_count == 5
    assert performance_logger.logger is not None

def test_performance_logger_metrics_logging(performance_logger):
    # Test metrics logging
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'metric_type': 'response_time',
        'value': 0.5,
        'unit': 'seconds',
        'context': {
            'endpoint': '/api/v1/events',
            'method': 'POST'
        }
    }
    
    # Mock logger
    performance_logger.logger = type('MockLogger', (), {
        'info': lambda msg: None
    })
    
    # Test logging
    performance_logger.log_metrics(metrics)
    # No assertion needed as we're just testing the method call

def test_performance_logger_threshold_alerts(performance_logger):
    # Test threshold alerts
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'metric_type': 'cpu_usage',
        'value': 95.0,
        'unit': 'percent',
        'threshold': 90.0
    }
    
    # Mock logger
    performance_logger.logger = type('MockLogger', (), {
        'warning': lambda msg: None
    })
    
    # Test alert logging
    performance_logger.log_metrics(metrics)
    # No assertion needed as we're just testing the method call

def test_logging_error_handling(log_manager, audit_logger, error_logger, performance_logger):
    # Test invalid log directory
    with pytest.raises(OSError):
        log_manager.log_dir = "/invalid/path"
        log_manager.create_log_directory()
    
    # Test invalid log file
    with pytest.raises(OSError):
        audit_logger.log_file = "/invalid/path/audit.log"
        audit_logger._setup_logger()
    
    # Test invalid event data
    with pytest.raises(ValueError):
        audit_logger.log_event({})
    
    # Test invalid error data
    with pytest.raises(ValueError):
        error_logger.log_error({})
    
    # Test invalid metrics data
    with pytest.raises(ValueError):
        performance_logger.log_metrics({})

def test_logging_cleanup(log_manager, audit_logger, error_logger, performance_logger):
    # Test cleanup
    log_manager.cleanup_old_logs()
    audit_logger.cleanup_old_logs()
    error_logger.cleanup_old_logs()
    performance_logger.cleanup_old_logs()
    
    # No assertions needed as we're just testing the method calls 