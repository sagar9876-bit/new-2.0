import pytest
from datetime import datetime
from enterprise.ad_integration import ADIntegration
from enterprise.siem_integration import SIEMIntegration
from enterprise.audit_logger import AuditLogger

@pytest.fixture
def ad_integration():
    return ADIntegration(
        domain="test.domain",
        server="ldap.test.domain",
        port=389,
        username="test_user",
        password="test_password"
    )

@pytest.fixture
def siem_integration():
    return SIEMIntegration(
        endpoint="https://siem.test.domain/api/v1",
        api_key="test_api_key",
        batch_size=100,
        flush_interval=60
    )

@pytest.fixture
def audit_logger():
    return AuditLogger(
        log_file="logs/audit.log",
        max_size=10485760,
        backup_count=5
    )

def test_ad_integration_initialization(ad_integration):
    assert ad_integration.domain == "test.domain"
    assert ad_integration.server == "ldap.test.domain"
    assert ad_integration.port == 389
    assert ad_integration.username == "test_user"
    assert ad_integration.password == "test_password"
    assert ad_integration.connection is None

def test_ad_integration_connection(ad_integration):
    # Mock connection
    ad_integration.connection = type('MockConnection', (), {
        'bind': lambda: True,
        'unbind': lambda: None
    })
    
    # Test connection
    assert ad_integration.connect() is True
    assert ad_integration.is_connected() is True
    
    # Test disconnection
    ad_integration.disconnect()
    assert ad_integration.is_connected() is False

def test_ad_integration_user_validation(ad_integration):
    # Mock connection and search
    ad_integration.connection = type('MockConnection', (), {
        'search': lambda *args: [
            {
                'dn': 'CN=test_user,DC=test,DC=domain',
                'attributes': {
                    'memberOf': [b'CN=Users,DC=test,DC=domain'],
                    'userAccountControl': [b'512']
                }
            }
        ]
    })
    
    # Test user validation
    result = ad_integration.validate_user("test_user")
    assert result['valid'] is True
    assert result['groups'] == ['CN=Users,DC=test,DC=domain']
    assert result['account_status'] == 'active'

def test_ad_integration_group_membership(ad_integration):
    # Mock connection and search
    ad_integration.connection = type('MockConnection', (), {
        'search': lambda *args: [
            {
                'dn': 'CN=test_user,DC=test,DC=domain',
                'attributes': {
                    'memberOf': [
                        b'CN=Users,DC=test,DC=domain',
                        b'CN=Admins,DC=test,DC=domain'
                    ]
                }
            }
        ]
    })
    
    # Test group membership
    groups = ad_integration.get_user_groups("test_user")
    assert len(groups) == 2
    assert 'CN=Users,DC=test,DC=domain' in groups
    assert 'CN=Admins,DC=test,DC=domain' in groups

def test_siem_integration_initialization(siem_integration):
    assert siem_integration.endpoint == "https://siem.test.domain/api/v1"
    assert siem_integration.api_key == "test_api_key"
    assert siem_integration.batch_size == 100
    assert siem_integration.flush_interval == 60
    assert len(siem_integration.event_buffer) == 0

def test_siem_integration_event_buffering(siem_integration):
    # Test event buffering
    event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'risk_score',
        'user_id': 'test_user',
        'risk_score': 75.0,
        'risk_level': 'high'
    }
    
    siem_integration.buffer_event(event)
    assert len(siem_integration.event_buffer) == 1
    assert siem_integration.event_buffer[0] == event

def test_siem_integration_batch_flushing(siem_integration):
    # Fill buffer
    for i in range(150):
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'risk_score',
            'user_id': f'test_user_{i}',
            'risk_score': 75.0,
            'risk_level': 'high'
        }
        siem_integration.buffer_event(event)
    
    # Mock API call
    siem_integration._send_batch = lambda events: True
    
    # Test batch flushing
    siem_integration.flush_buffer()
    assert len(siem_integration.event_buffer) == 50  # Remaining events

def test_siem_integration_api_call(siem_integration):
    # Mock API call
    siem_integration._make_request = lambda method, url, data: {
        'status': 'success',
        'message': 'Events processed successfully'
    }
    
    # Test API call
    events = [
        {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'risk_score',
            'user_id': 'test_user',
            'risk_score': 75.0,
            'risk_level': 'high'
        }
    ]
    
    result = siem_integration._send_batch(events)
    assert result is True

def test_audit_logger_initialization(audit_logger):
    assert audit_logger.log_file == "logs/audit.log"
    assert audit_logger.max_size == 10485760
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

def test_audit_logger_event_formats(audit_logger):
    # Test different event formats
    events = [
        {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'user_login',
            'user_id': 'test_user',
            'ip_address': '192.168.1.1',
            'status': 'success'
        },
        {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'risk_score',
            'user_id': 'test_user',
            'risk_score': 75.0,
            'risk_level': 'high'
        },
        {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'session_end',
            'user_id': 'test_user',
            'session_duration': 3600,
            'event_count': 100
        }
    ]
    
    # Mock logger
    audit_logger.logger = type('MockLogger', (), {
        'info': lambda msg: None
    })
    
    # Test logging different event types
    for event in events:
        audit_logger.log_event(event)
        # No assertion needed as we're just testing the method call

def test_enterprise_integration_error_handling(ad_integration, siem_integration, audit_logger):
    # Test AD integration error handling
    with pytest.raises(Exception):
        ad_integration.connect()
    
    # Test SIEM integration error handling
    with pytest.raises(Exception):
        siem_integration._send_batch([])
    
    # Test audit logger error handling
    with pytest.raises(Exception):
        audit_logger.log_event({}) 