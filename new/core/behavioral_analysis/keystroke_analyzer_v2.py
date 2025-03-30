from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
from dataclasses import dataclass
from datetime import datetime

@dataclass
class KeystrokeEvent:
    key: str
    press_time: float
    release_time: float
    pressure: float
    x_coord: float
    y_coord: float
    timestamp: datetime

class KeystrokeAnalyzer:
    def __init__(self, model_path: Optional[str] = None):
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.feature_dim = 10
        self.model_path = model_path
        self.neural_net = self._build_neural_net()
        if model_path:
            self.load_model(model_path)
    
    def _build_neural_net(self) -> nn.Module:
        """Build the neural network for feature extraction"""
        return nn.Sequential(
            nn.Linear(self.feature_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16)
        )
    
    def extract_features(self, events: List[KeystrokeEvent]) -> np.ndarray:
        """Extract features from keystroke events"""
        features = []
        for i in range(len(events) - 1):
            current = events[i]
            next_event = events[i + 1]
            
            # Basic timing features
            hold_time = current.release_time - current.press_time
            flight_time = next_event.press_time - current.release_time
            
            # Pressure features
            pressure_diff = next_event.pressure - current.pressure
            
            # Spatial features
            x_diff = next_event.x_coord - current.x_coord
            y_diff = next_event.y_coord - current.y_coord
            
            # Combined features
            feature_vector = [
                hold_time,
                flight_time,
                pressure_diff,
                x_diff,
                y_diff,
                current.pressure,
                next_event.pressure,
                np.sqrt(x_diff**2 + y_diff**2),  # Distance
                np.arctan2(y_diff, x_diff),  # Angle
                (next_event.timestamp - current.timestamp).total_seconds()
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    def calculate_risk_score(self, events: List[KeystrokeEvent]) -> float:
        """Calculate risk score for the current session"""
        if len(events) < 2:
            return 0.0
            
        features = self.extract_features(events)
        
        # Scale features
        scaled_features = self.scaler.fit_transform(features)
        
        # Get anomaly scores from Isolation Forest
        anomaly_scores = self.isolation_forest.score_samples(scaled_features)
        
        # Convert to risk score (0-100)
        risk_scores = (anomaly_scores - anomaly_scores.min()) / (anomaly_scores.max() - anomaly_scores.min()) * 100
        
        # Calculate composite risk score
        composite_risk = np.mean(risk_scores)
        
        return float(composite_risk)
    
    def train(self, training_events: List[List[KeystrokeEvent]]) -> None:
        """Train the model on historical data"""
        all_features = []
        for session in training_events:
            features = self.extract_features(session)
            all_features.append(features)
        
        # Combine all features
        combined_features = np.vstack(all_features)
        
        # Fit scaler and transform features
        scaled_features = self.scaler.fit_transform(combined_features)
        
        # Train Isolation Forest
        self.isolation_forest.fit(scaled_features)
    
    def save_model(self, path: str) -> None:
        """Save the trained model"""
        import joblib
        model_data = {
            'isolation_forest': self.isolation_forest,
            'scaler': self.scaler,
            'neural_net_state': self.neural_net.state_dict()
        }
        joblib.dump(model_data, path)
    
    def load_model(self, path: str) -> None:
        """Load a trained model"""
        import joblib
        model_data = joblib.load(path)
        self.isolation_forest = model_data['isolation_forest']
        self.scaler = model_data['scaler']
        self.neural_net.load_state_dict(model_data['neural_net_state']) 