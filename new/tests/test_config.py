import pytest
from config.settings import settings

def test_settings_initialization():
    assert settings is not None
    assert hasattr(settings, 'API')
    assert hasattr(settings, 'SERVER')
    assert hasattr(settings, 'SECURITY')
    assert hasattr(settings, 'CORS')
    assert hasattr(settings, 'MODEL')
    assert hasattr(settings, 'RISK_THRESHOLDS')
    assert hasattr(settings, 'BEHAVIORAL_ANALYSIS')
    assert hasattr(settings, 'FEATURE_EXTRACTION')
    assert hasattr(settings, 'MACHINE_LEARNING')
    assert hasattr(settings, 'ENTERPRISE_INTEGRATION')
    assert hasattr(settings, 'LOGGING')
    assert hasattr(settings, 'PERFORMANCE')

def test_api_settings():
    assert settings.API.VERSION == "1.0.0"
    assert settings.API.PREFIX == "/api/v1"
    assert settings.API.DOCS_URL == "/docs"
    assert settings.API.REDOC_URL == "/redoc"
    assert settings.API.OPENAPI_URL == "/openapi.json"

def test_server_settings():
    assert settings.SERVER.HOST == "0.0.0.0"
    assert settings.SERVER.PORT == 8000
    assert settings.SERVER.WORKERS == 4
    assert settings.SERVER.RELOAD == True
    assert settings.SERVER.LOG_LEVEL == "info"

def test_security_settings():
    assert settings.SECURITY.SECRET_KEY is not None
    assert len(settings.SECURITY.SECRET_KEY) >= 32
    assert settings.SECURITY.ALGORITHM == "HS256"
    assert settings.SECURITY.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.SECURITY.REFRESH_TOKEN_EXPIRE_DAYS == 7

def test_cors_settings():
    assert settings.CORS.ALLOWED_ORIGINS == ["*"]
    assert settings.CORS.ALLOWED_METHODS == ["*"]
    assert settings.CORS.ALLOWED_HEADERS == ["*"]
    assert settings.CORS.ALLOW_CREDENTIALS == True
    assert settings.CORS.MAX_AGE == 600

def test_model_settings():
    assert settings.MODEL.PATH == "models"
    assert settings.MODEL.FILENAME == "behavioral_model.pkl"
    assert settings.MODEL.VERSION == "1.0.0"
    assert settings.MODEL.UPDATE_INTERVAL == 3600
    assert settings.MODEL.BACKUP_COUNT == 5

def test_risk_thresholds():
    assert settings.RISK_THRESHOLDS.CRITICAL == 90.0
    assert settings.RISK_THRESHOLDS.HIGH == 75.0
    assert settings.RISK_THRESHOLDS.MEDIUM == 50.0
    assert settings.RISK_THRESHOLDS.LOW == 25.0

def test_behavioral_analysis_settings():
    assert settings.BEHAVIORAL_ANALYSIS.SESSION_TIMEOUT == 3600
    assert settings.BEHAVIORAL_ANALYSIS.MAX_EVENTS == 1000
    assert settings.BEHAVIORAL_ANALYSIS.DRIFT_THRESHOLD == 0.8
    assert settings.BEHAVIORAL_ANALYSIS.CONFIDENCE_THRESHOLD == 0.9
    assert settings.BEHAVIORAL_ANALYSIS.UPDATE_INTERVAL == 300

def test_feature_extraction_settings():
    assert settings.FEATURE_EXTRACTION.KEYSTROKE_FEATURES == [
        "hold_time",
        "flight_time",
        "pressure",
        "spatial_diff"
    ]
    assert settings.FEATURE_EXTRACTION.MOUSE_FEATURES == [
        "velocity",
        "acceleration",
        "pressure",
        "spatial_diff"
    ]
    assert settings.FEATURE_EXTRACTION.WINDOW_SIZE == 10
    assert settings.FEATURE_EXTRACTION.STRIDE == 1
    assert settings.FEATURE_EXTRACTION.NORMALIZE == True

def test_machine_learning_settings():
    assert settings.MACHINE_LEARNING.MODEL_TYPE == "isolation_forest"
    assert settings.MACHINE_LEARNING.RANDOM_STATE == 42
    assert settings.MACHINE_LEARNING.N_ESTIMATORS == 100
    assert settings.MACHINE_LEARNING.CONTAMINATION == 0.1
    assert settings.MACHINE_LEARNING.BATCH_SIZE == 32

def test_enterprise_integration_settings():
    assert settings.ENTERPRISE_INTEGRATION.AD_ENABLED == False
    assert settings.ENTERPRISE_INTEGRATION.AD_DOMAIN == ""
    assert settings.ENTERPRISE_INTEGRATION.AD_SERVER == ""
    assert settings.ENTERPRISE_INTEGRATION.AD_PORT == 389
    assert settings.ENTERPRISE_INTEGRATION.SIEM_ENDPOINT == ""

def test_logging_settings():
    assert settings.LOGGING.LEVEL == "INFO"
    assert settings.LOGGING.FORMAT == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    assert settings.LOGGING.FILE == "logs/behavioral_biometrics.log"
    assert settings.LOGGING.MAX_BYTES == 10485760
    assert settings.LOGGING.BACKUP_COUNT == 5

def test_performance_settings():
    assert settings.PERFORMANCE.MAX_CONNECTIONS == 1000
    assert settings.PERFORMANCE.KEEP_ALIVE_TIMEOUT == 60
    assert settings.PERFORMANCE.MAX_REQUEST_SIZE == 1048576
    assert settings.PERFORMANCE.RATE_LIMIT == 100
    assert settings.PERFORMANCE.RATE_LIMIT_PERIOD == 60

def test_settings_immutability():
    with pytest.raises(Exception):
        settings.API.VERSION = "2.0.0"
    
    with pytest.raises(Exception):
        settings.SERVER.PORT = 9000
    
    with pytest.raises(Exception):
        settings.RISK_THRESHOLDS.CRITICAL = 95.0

def test_settings_validation():
    # Test invalid port number
    with pytest.raises(ValueError):
        settings.SERVER.PORT = -1
    
    # Test invalid risk threshold
    with pytest.raises(ValueError):
        settings.RISK_THRESHOLDS.CRITICAL = 101.0
    
    # Test invalid max connections
    with pytest.raises(ValueError):
        settings.PERFORMANCE.MAX_CONNECTIONS = -1 