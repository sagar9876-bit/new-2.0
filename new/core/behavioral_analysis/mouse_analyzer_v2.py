from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MouseEvent:
    event_type: str  # 'move', 'click', 'drag'
    x_coord: float
    y_coord: float
    pressure: float
    timestamp: datetime
    velocity: Optional[float] = None
    acceleration: Optional[float] = None

class MouseAnalyzer:
    def __init__(self, model_path: Optional[str] = None):
        self.svm = OneClassSVM(kernel='rbf', nu=0.1)
        self.scaler = StandardScaler()
        self.feature_dim = 8
        self.model_path = model_path
        self.cnn = self._build_cnn()
        if model_path:
            self.load_model(model_path)
    
    def _build_cnn(self) -> nn.Module:
        """Build CNN for trajectory analysis"""
        return nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Flatten(),
            nn.Linear(64 * 2, 32),
            nn.ReLU(),
            nn.Linear(32, 16)
        )
    
    def _calculate_bezier_curve(self, points: List[Tuple[float, float]]) -> np.ndarray:
        """Calculate Bézier curve for mouse trajectory"""
        if len(points) < 3:
            return np.array(points)
            
        t = np.linspace(0, 1, 100)
        curve = np.zeros((len(t), 2))
        
        for i in range(len(t)):
            curve[i] = np.array([0.0, 0.0])
            for j in range(len(points)):
                curve[i] += points[j] * np.math.comb(len(points) - 1, j) * \
                           (t[i] ** j) * ((1 - t[i]) ** (len(points) - 1 - j))
        
        return curve
    
    def extract_features(self, events: List[MouseEvent]) -> np.ndarray:
        """Extract features from mouse events"""
        features = []
        for i in range(len(events) - 1):
            current = events[i]
            next_event = events[i + 1]
            
            # Calculate velocity and acceleration if not present
            if current.velocity is None:
                time_diff = (next_event.timestamp - current.timestamp).total_seconds()
                distance = np.sqrt(
                    (next_event.x_coord - current.x_coord) ** 2 +
                    (next_event.y_coord - current.y_coord) ** 2
                )
                current.velocity = distance / time_diff if time_diff > 0 else 0
                
                if i > 0:
                    prev_event = events[i - 1]
                    prev_time_diff = (current.timestamp - prev_event.timestamp).total_seconds()
                    prev_distance = np.sqrt(
                        (current.x_coord - prev_event.x_coord) ** 2 +
                        (current.y_coord - prev_event.y_coord) ** 2
                    )
                    prev_velocity = prev_distance / prev_time_diff if prev_time_diff > 0 else 0
                    current.acceleration = (current.velocity - prev_velocity) / time_diff if time_diff > 0 else 0
            
            # Extract features
            feature_vector = [
                current.x_coord,
                current.y_coord,
                current.velocity if current.velocity is not None else 0,
                current.acceleration if current.acceleration is not None else 0,
                current.pressure,
                next_event.x_coord - current.x_coord,  # Delta X
                next_event.y_coord - current.y_coord,  # Delta Y
                (next_event.timestamp - current.timestamp).total_seconds()  # Time delta
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    def calculate_risk_score(self, events: List[MouseEvent]) -> float:
        """Calculate risk score for the current session"""
        if len(events) < 2:
            return 0.0
            
        features = self.extract_features(events)
        
        # Scale features
        scaled_features = self.scaler.fit_transform(features)
        
        # Get anomaly scores from OneClassSVM
        anomaly_scores = self.svm.score_samples(scaled_features)
        
        # Convert to risk score (0-100)
        risk_scores = (anomaly_scores - anomaly_scores.min()) / (anomaly_scores.max() - anomaly_scores.min()) * 100
        
        # Calculate composite risk score
        composite_risk = np.mean(risk_scores)
        
        return float(composite_risk)
    
    def train(self, training_events: List[List[MouseEvent]]) -> None:
        """Train the model on historical data"""
        all_features = []
        for session in training_events:
            features = self.extract_features(session)
            all_features.append(features)
        
        # Combine all features
        combined_features = np.vstack(all_features)
        
        # Fit scaler and transform features
        scaled_features = self.scaler.fit_transform(combined_features)
        
        # Train OneClassSVM
        self.svm.fit(scaled_features)
    
    def save_model(self, path: str) -> None:
        """Save the trained model"""
        import joblib
        model_data = {
            'svm': self.svm,
            'scaler': self.scaler,
            'cnn_state': self.cnn.state_dict()
        }
        joblib.dump(model_data, path)
    
    def load_model(self, path: str) -> None:
        """Load a trained model"""
        import joblib
        model_data = joblib.load(path)
        self.svm = model_data['svm']
        self.scaler = model_data['scaler']
        self.cnn.load_state_dict(model_data['cnn_state']) 