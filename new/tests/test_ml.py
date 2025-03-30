import pytest
import numpy as np
from datetime import datetime
from ml.model_manager import ModelManager
from ml.feature_processor import FeatureProcessor
from ml.anomaly_detector import AnomalyDetector
from ml.model_trainer import ModelTrainer

@pytest.fixture
def model_manager():
    return ModelManager(
        model_path="models",
        model_filename="behavioral_model.pkl",
        model_version="1.0.0",
        update_interval=3600,
        backup_count=5
    )

@pytest.fixture
def feature_processor():
    return FeatureProcessor(
        window_size=10,
        stride=1,
        normalize=True
    )

@pytest.fixture
def anomaly_detector():
    return AnomalyDetector(
        model_type="isolation_forest",
        random_state=42,
        n_estimators=100,
        contamination=0.1
    )

@pytest.fixture
def model_trainer():
    return ModelTrainer(
        batch_size=32,
        epochs=10,
        learning_rate=0.001
    )

@pytest.fixture
def sample_features():
    return np.random.rand(100, 10)  # 100 samples, 10 features

def test_model_manager_initialization(model_manager):
    assert model_manager.model_path == "models"
    assert model_manager.model_filename == "behavioral_model.pkl"
    assert model_manager.model_version == "1.0.0"
    assert model_manager.update_interval == 3600
    assert model_manager.backup_count == 5
    assert model_manager.model is None
    assert model_manager.last_update is None

def test_model_manager_save_load(model_manager, sample_features):
    # Mock model
    model_manager.model = type('MockModel', (), {
        'predict': lambda x: np.zeros(len(x)),
        'predict_proba': lambda x: np.zeros((len(x), 2))
    })
    
    # Test save
    model_manager.save_model()
    assert model_manager.last_update is not None
    
    # Test load
    model_manager.load_model()
    assert model_manager.model is not None

def test_model_manager_versioning(model_manager):
    # Test version update
    model_manager.update_model_version("2.0.0")
    assert model_manager.model_version == "2.0.0"
    
    # Test backup creation
    model_manager.create_backup()
    assert model_manager.get_backup_count() > 0

def test_feature_processor_initialization(feature_processor):
    assert feature_processor.window_size == 10
    assert feature_processor.stride == 1
    assert feature_processor.normalize == True
    assert feature_processor.scaler is not None

def test_feature_processor_window_creation(feature_processor, sample_features):
    # Test window creation
    windows = feature_processor.create_windows(sample_features)
    assert windows.shape[0] == (sample_features.shape[0] - feature_processor.window_size + 1)
    assert windows.shape[1] == feature_processor.window_size
    assert windows.shape[2] == sample_features.shape[1]

def test_feature_processor_normalization(feature_processor, sample_features):
    # Test normalization
    normalized = feature_processor.normalize_features(sample_features)
    assert normalized.shape == sample_features.shape
    assert np.all(normalized >= -1) and np.all(normalized <= 1)

def test_feature_processor_feature_extraction(feature_processor, sample_features):
    # Test feature extraction
    extracted = feature_processor.extract_features(sample_features)
    assert extracted.shape[0] == sample_features.shape[0]
    assert extracted.shape[1] > sample_features.shape[1]  # More features after extraction

def test_anomaly_detector_initialization(anomaly_detector):
    assert anomaly_detector.model_type == "isolation_forest"
    assert anomaly_detector.random_state == 42
    assert anomaly_detector.n_estimators == 100
    assert anomaly_detector.contamination == 0.1
    assert anomaly_detector.model is None

def test_anomaly_detector_training(anomaly_detector, sample_features):
    # Test model training
    anomaly_detector.train(sample_features)
    assert anomaly_detector.model is not None
    
    # Test prediction
    predictions = anomaly_detector.predict(sample_features)
    assert len(predictions) == len(sample_features)
    assert np.all(np.isin(predictions, [-1, 1]))  # -1 for normal, 1 for anomaly

def test_anomaly_detector_score_calculation(anomaly_detector, sample_features):
    # Train model
    anomaly_detector.train(sample_features)
    
    # Test score calculation
    scores = anomaly_detector.calculate_scores(sample_features)
    assert len(scores) == len(sample_features)
    assert np.all(scores >= 0) and np.all(scores <= 1)

def test_model_trainer_initialization(model_trainer):
    assert model_trainer.batch_size == 32
    assert model_trainer.epochs == 10
    assert model_trainer.learning_rate == 0.001
    assert model_trainer.model is None

def test_model_trainer_training(model_trainer, sample_features):
    # Create sample labels (0 for normal, 1 for anomaly)
    labels = np.random.randint(0, 2, len(sample_features))
    
    # Test model training
    model_trainer.train(sample_features, labels)
    assert model_trainer.model is not None
    
    # Test prediction
    predictions = model_trainer.predict(sample_features)
    assert len(predictions) == len(sample_features)
    assert np.all(np.isin(predictions, [0, 1]))

def test_model_trainer_evaluation(model_trainer, sample_features):
    # Create sample labels
    labels = np.random.randint(0, 2, len(sample_features))
    
    # Train model
    model_trainer.train(sample_features, labels)
    
    # Test evaluation
    metrics = model_trainer.evaluate(sample_features, labels)
    assert 'accuracy' in metrics
    assert 'precision' in metrics
    assert 'recall' in metrics
    assert 'f1_score' in metrics
    assert all(0 <= value <= 1 for value in metrics.values())

def test_ml_pipeline_integration(model_manager, feature_processor, anomaly_detector, model_trainer, sample_features):
    # Process features
    processed_features = feature_processor.process_features(sample_features)
    
    # Train anomaly detector
    anomaly_detector.train(processed_features)
    
    # Train model
    labels = np.random.randint(0, 2, len(processed_features))
    model_trainer.train(processed_features, labels)
    
    # Save model
    model_manager.model = model_trainer.model
    model_manager.save_model()
    
    # Load and verify
    model_manager.load_model()
    assert model_manager.model is not None
    
    # Test prediction pipeline
    predictions = model_manager.model.predict(processed_features)
    assert len(predictions) == len(processed_features)
    assert np.all(np.isin(predictions, [0, 1]))

def test_ml_error_handling(model_manager, feature_processor, anomaly_detector, model_trainer):
    # Test invalid feature data
    with pytest.raises(ValueError):
        feature_processor.process_features(None)
    
    # Test invalid model type
    with pytest.raises(ValueError):
        anomaly_detector.model_type = "invalid_type"
        anomaly_detector.train(np.random.rand(10, 5))
    
    # Test invalid training data
    with pytest.raises(ValueError):
        model_trainer.train(None, None)
    
    # Test invalid model path
    with pytest.raises(FileNotFoundError):
        model_manager.model_path = "invalid_path"
        model_manager.load_model() 