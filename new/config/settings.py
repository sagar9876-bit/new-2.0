from typing import Dict, Any, List
from pydantic import BaseSettings, validator
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class APISettings(BaseSettings):
    VERSION: str = "1.0.0"
    PREFIX: str = "/api/v1"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"

    @validator("VERSION")
    def validate_version(cls, v):
        if not v or not all(part.isdigit() for part in v.split(".")):
            raise ValueError("Version must be in format X.Y.Z where X, Y, Z are numbers")
        return v

class ServerSettings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = False
    LOG_LEVEL: str = "INFO"

    @validator("PORT")
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v
    
    @validator("WORKERS")
    def validate_workers(cls, v):
        if v < 1:
            raise ValueError("Number of workers must be at least 1")
        return v

class SecuritySettings(BaseSettings):
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAX_REQUEST_SIZE: int = 1048576  # 1MB
    MAX_CONNECTIONS_PER_IP: int = 100
    MAX_CONNECTIONS_PER_USER: int = 5
    RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_MAX_REQUESTS: int = 100
    ENABLE_IP_BLOCKING: bool = True
    MAX_FAILED_ATTEMPTS: int = 5
    IP_BLOCK_DURATION: int = 3600  # 1 hour

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if not v:
            raise ValueError("SECRET_KEY must be set in environment variables")
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    @validator("MAX_REQUEST_SIZE")
    def validate_max_request_size(cls, v):
        if v < 1024:  # Minimum 1KB
            raise ValueError("Maximum request size must be at least 1KB")
        if v > 10485760:  # Maximum 10MB
            raise ValueError("Maximum request size must not exceed 10MB")
        return v

    @validator("MAX_CONNECTIONS_PER_IP")
    def validate_max_connections_per_ip(cls, v):
        if v < 1:
            raise ValueError("Maximum connections per IP must be at least 1")
        return v

    @validator("MAX_CONNECTIONS_PER_USER")
    def validate_max_connections_per_user(cls, v):
        if v < 1:
            raise ValueError("Maximum connections per user must be at least 1")
        return v

    @validator("RATE_LIMIT_WINDOW")
    def validate_rate_limit_window(cls, v):
        if v < 1:
            raise ValueError("Rate limit window must be at least 1 second")
        return v

    @validator("RATE_LIMIT_MAX_REQUESTS")
    def validate_rate_limit_max_requests(cls, v):
        if v < 1:
            raise ValueError("Rate limit max requests must be at least 1")
        return v

    @validator("MAX_FAILED_ATTEMPTS")
    def validate_max_failed_attempts(cls, v):
        if v < 1:
            raise ValueError("Maximum failed attempts must be at least 1")
        return v

    @validator("IP_BLOCK_DURATION")
    def validate_ip_block_duration(cls, v):
        if v < 300:  # Minimum 5 minutes
            raise ValueError("IP block duration must be at least 5 minutes")
        return v

class CORSSettings(BaseSettings):
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]
    ALLOW_CREDENTIALS: bool = True
    MAX_AGE: int = 600

class ModelSettings(BaseSettings):
    MODEL_PATH: str = "models"
    MODEL_FILENAME: str = "behavioral_model.joblib"
    MODEL_VERSION: str = "1.0.0"
    UPDATE_INTERVAL: int = 3600  # 1 hour
    BACKUP_COUNT: int = 5

    @validator("UPDATE_INTERVAL")
    def validate_update_interval(cls, v):
        if v < 300:  # Minimum 5 minutes
            raise ValueError("Update interval must be at least 5 minutes")
        return v

class RiskThresholds(BaseSettings):
    CRITICAL: float = 90.0
    HIGH: float = 75.0
    MEDIUM: float = 50.0
    LOW: float = 25.0

    @validator("CRITICAL", "HIGH", "MEDIUM", "LOW")
    def validate_thresholds(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Risk thresholds must be between 0 and 100")
        return v
    
    @validator("CRITICAL")
    def validate_critical(cls, v, values):
        if "HIGH" in values and v <= values["HIGH"]:
            raise ValueError("Critical threshold must be higher than high threshold")
        return v
    
    @validator("HIGH")
    def validate_high(cls, v, values):
        if "MEDIUM" in values and v <= values["MEDIUM"]:
            raise ValueError("High threshold must be higher than medium threshold")
        return v
    
    @validator("MEDIUM")
    def validate_medium(cls, v, values):
        if "LOW" in values and v <= values["LOW"]:
            raise ValueError("Medium threshold must be higher than low threshold")
        return v

class BehavioralAnalysisSettings(BaseSettings):
    SESSION_TIMEOUT: int = 3600  # 1 hour
    MAX_EVENTS: int = 1000
    DRIFT_THRESHOLD: float = 0.7
    CONFIDENCE_THRESHOLD: float = 0.8
    UPDATE_INTERVAL: int = 300  # 5 minutes

    @validator("SESSION_TIMEOUT")
    def validate_session_timeout(cls, v):
        if v < 300:  # Minimum 5 minutes
            raise ValueError("Session timeout must be at least 5 minutes")
        return v
    
    @validator("MAX_EVENTS")
    def validate_max_events(cls, v):
        if v < 100:
            raise ValueError("Maximum events must be at least 100")
        return v
    
    @validator("DRIFT_THRESHOLD", "CONFIDENCE_THRESHOLD")
    def validate_thresholds(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Thresholds must be between 0 and 1")
        return v

class FeatureExtractionSettings(BaseSettings):
    KEYSTROKE_FEATURES: List[str] = [
        "inter_arrival_time",
        "key_press_duration",
        "key_release_duration",
        "key_hold_time",
        "key_sequence"
    ]
    MOUSE_FEATURES: List[str] = [
        "movement_speed",
        "acceleration",
        "angle",
        "distance",
        "click_duration"
    ]
    WINDOW_SIZE: int = 10
    STRIDE: int = 5
    NORMALIZE: bool = True

    @validator("WINDOW_SIZE")
    def validate_window_size(cls, v):
        if v < 5:
            raise ValueError("Window size must be at least 5")
        return v
    
    @validator("STRIDE")
    def validate_stride(cls, v, values):
        if "WINDOW_SIZE" in values and v >= values["WINDOW_SIZE"]:
            raise ValueError("Stride must be less than window size")
        return v

class MachineLearningSettings(BaseSettings):
    MODEL_TYPE: str = "isolation_forest"
    RANDOM_STATE: int = 42
    N_ESTIMATORS: int = 100
    CONTAMINATION: float = 0.1
    BATCH_SIZE: int = 32

    @validator("MODEL_TYPE")
    def validate_model_type(cls, v):
        allowed_types = ["isolation_forest", "autoencoder", "gmm"]
        if v not in allowed_types:
            raise ValueError(f"Model type must be one of {allowed_types}")
        return v
    
    @validator("N_ESTIMATORS")
    def validate_n_estimators(cls, v):
        if v < 10:
            raise ValueError("Number of estimators must be at least 10")
        return v
    
    @validator("CONTAMINATION")
    def validate_contamination(cls, v):
        if not 0 < v < 0.5:
            raise ValueError("Contamination must be between 0 and 0.5")
        return v

class EnterpriseIntegrationSettings(BaseSettings):
    AD_SERVER: str = os.getenv("AD_SERVER", "localhost")
    AD_PORT: int = int(os.getenv("AD_PORT", "389"))
    AD_USE_SSL: bool = os.getenv("AD_USE_SSL", "False").lower() == "true"
    AD_USER: str = os.getenv("AD_USER", "")
    AD_PASSWORD: str = os.getenv("AD_PASSWORD", "")
    AD_BASE_DN: str = os.getenv("AD_BASE_DN", "dc=example,dc=com")
    SIEM_ENDPOINT: str = os.getenv("SIEM_ENDPOINT", "http://localhost:8080")
    SIEM_API_KEY: str = os.getenv("SIEM_API_KEY", "")

    @validator("AD_PORT")
    def validate_ad_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("AD port must be between 1 and 65535")
        return v

class LoggingSettings(BaseSettings):
    LEVEL: str = "INFO"
    FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    FILE_PATH: str = "logs/app.log"
    MAX_BYTES: int = 10485760  # 10MB
    BACKUP_COUNT: int = 5

    @validator("LEVEL")
    def validate_level(cls, v):
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return v.upper()

class PerformanceSettings(BaseSettings):
    MAX_CONNECTIONS: int = 1000
    KEEP_ALIVE_TIMEOUT: int = 60
    MAX_REQUEST_SIZE: int = 1048576  # 1MB
    RATE_LIMIT: int = 100
    RATE_LIMIT_PERIOD: int = 60

    @validator("MAX_CONNECTIONS")
    def validate_max_connections(cls, v):
        if v < 100:
            raise ValueError("Maximum connections must be at least 100")
        return v
    
    @validator("KEEP_ALIVE_TIMEOUT")
    def validate_keep_alive_timeout(cls, v):
        if v < 30:
            raise ValueError("Keep-alive timeout must be at least 30 seconds")
        return v

class ResponseActions(BaseSettings):
    CRITICAL: List[str] = ["block_user", "notify_admin", "log_event"]
    HIGH: List[str] = ["warn_user", "notify_admin", "log_event"]
    MEDIUM: List[str] = ["warn_user", "log_event"]
    LOW: List[str] = ["log_event"]

    @validator("CRITICAL", "HIGH", "MEDIUM", "LOW")
    def validate_actions(cls, v):
        allowed_actions = ["block_user", "warn_user", "notify_admin", "log_event"]
        if not all(action in allowed_actions for action in v):
            raise ValueError(f"Actions must be one of {allowed_actions}")
        return v

class Settings(BaseSettings):
    API: APISettings = APISettings()
    SERVER: ServerSettings = ServerSettings()
    SECURITY: SecuritySettings = SecuritySettings()
    CORS: CORSSettings = CORSSettings()
    MODEL: ModelSettings = ModelSettings()
    RISK_THRESHOLDS: RiskThresholds = RiskThresholds()
    BEHAVIORAL_ANALYSIS: BehavioralAnalysisSettings = BehavioralAnalysisSettings()
    FEATURE_EXTRACTION: FeatureExtractionSettings = FeatureExtractionSettings()
    MACHINE_LEARNING: MachineLearningSettings = MachineLearningSettings()
    ENTERPRISE: EnterpriseIntegrationSettings = EnterpriseIntegrationSettings()
    LOGGING: LoggingSettings = LoggingSettings()
    PERFORMANCE: PerformanceSettings = PerformanceSettings()
    RESPONSE_ACTIONS: ResponseActions = ResponseActions()

    # API Configuration
    API_VERSION: str = "2.3.0"
    API_TITLE: str = "Zero Authentication Behavioral Biometrics API"
    API_DESCRIPTION: str = "API for continuous behavioral authentication system"
    
    # Server Configuration
    DEBUG: bool = False
    
    # CORS Settings
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    
    # Model Settings
    KEYSTROKE_MODEL_PATH: str = "models/keystroke_model.joblib"
    MOUSE_MODEL_PATH: str = "models/mouse_model.joblib"
    
    # Behavioral Analysis Settings
    KEYSTROKE_WEIGHT: float = 0.6
    MOUSE_WEIGHT: float = 0.4
    MIN_EVENTS_FOR_ANALYSIS: int = 10
    DRIFT_DETECTION_WINDOW: int = 10
    DRIFT_SCORE_THRESHOLD: float = 70.0
    DRIFT_VARIANCE_THRESHOLD: float = 20.0
    
    # Feature Extraction Settings
    FEATURE_EXTRACTION_DICT: Dict[str, Any] = {
        "keystroke": {
            "feature_dim": 10,
            "neural_net_layers": [64, 32, 16],
            "dropout_rate": 0.2
        },
        "mouse": {
            "feature_dim": 8,
            "cnn_filters": [32, 64],
            "kernel_size": 3
        }
    }
    
    # Machine Learning Settings
    ML_SETTINGS: Dict[str, Any] = {
        "keystroke": {
            "isolation_forest": {
                "contamination": 0.1,
                "random_state": 42
            }
        },
        "mouse": {
            "one_class_svm": {
                "kernel": "rbf",
                "nu": 0.1
            }
        }
    }
    
    # Enterprise Integration Settings
    ENTERPRISE: Dict[str, Any] = {
        "active_directory": {
            "enabled": False,
            "domain": os.getenv("AD_DOMAIN", ""),
            "server": os.getenv("AD_SERVER", ""),
            "port": int(os.getenv("AD_PORT", "389"))
        },
        "siem": {
            "enabled": False,
            "endpoint": os.getenv("SIEM_ENDPOINT", ""),
            "format": "CEF",
            "facility": "AUTH"
        }
    }
    
    # Logging Configuration
    LOGGING_DICT: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            }
        },
        "handlers": {
            "default": {
                "level": "INFO",
                "formatter": "standard",
                "class": "logging.StreamHandler"
            },
            "file": {
                "level": "INFO",
                "formatter": "standard",
                "class": "logging.FileHandler",
                "filename": "logs/app.log",
                "mode": "a"
            }
        },
        "loggers": {
            "": {
                "handlers": ["default", "file"],
                "level": "INFO",
                "propagate": True
            }
        }
    }
    
    # Performance Settings
    PERFORMANCE: Dict[str, Any] = {
        "max_concurrent_users": 10000,
        "events_per_second": 1000,
        "max_session_duration": 86400,  # 24 hours in seconds
        "cleanup_interval": 3600,  # 1 hour in seconds
        "max_memory_usage": "2G"
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Ensure required directories exist
def setup_directories():
    directories = [
        "logs",
        "models",
        "data"
    ]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

setup_directories() 