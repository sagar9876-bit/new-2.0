from typing import Dict, List, Optional, Tuple, Set
import numpy as np
from datetime import datetime, timedelta
import logging
from pathlib import Path
import joblib
import json
from dataclasses import dataclass
from .keystroke_analyzer_v2 import KeystrokeAnalyzer, KeystrokeEvent
from .mouse_analyzer_v2 import MouseAnalyzer, MouseEvent
from config.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class SessionState:
    keystroke_events: List[KeystrokeEvent]
    mouse_events: List[MouseEvent]
    start_time: datetime
    risk_scores: List[Dict]
    last_activity: datetime
    user_info: Optional[Dict]
    anomaly_count: int = 0
    consecutive_anomalies: int = 0
    max_anomaly_threshold: int = 5

class ContextProcessor:
    def __init__(self, keystroke_model_path: Optional[str] = None, mouse_model_path: Optional[str] = None):
        self.keystroke_model_path = keystroke_model_path or settings.KEYSTROKE_MODEL_PATH
        self.mouse_model_path = mouse_model_path or settings.MOUSE_MODEL_PATH
        
        try:
            self.keystroke_analyzer = KeystrokeAnalyzer(self.keystroke_model_path)
            self.mouse_analyzer = MouseAnalyzer(self.mouse_model_path)
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            raise
        
        self.session_history: List[Dict] = []
        self.current_session: Optional[SessionState] = None
        self.last_cleanup = datetime.now()
        self.anomaly_patterns: Dict[str, int] = {}
        self.blocked_patterns: Set[str] = set()
        
        # Create necessary directories
        self.forensic_dir = Path("forensics")
        self.forensic_dir.mkdir(exist_ok=True)
    
    def _cleanup_old_sessions(self) -> None:
        """Clean up old sessions based on timeout"""
        current_time = datetime.now()
        if (current_time - self.last_cleanup).total_seconds() < settings.BEHAVIORAL_ANALYSIS.UPDATE_INTERVAL:
            return
            
        timeout = timedelta(seconds=settings.BEHAVIORAL_ANALYSIS.SESSION_TIMEOUT)
        self.session_history = [
            session for session in self.session_history
            if current_time - session['start_time'] < timeout
        ]
        self.last_cleanup = current_time
    
    def _check_session_timeout(self) -> bool:
        """Check if current session has timed out"""
        if not self.current_session:
            return False
            
        current_time = datetime.now()
        timeout = timedelta(seconds=settings.BEHAVIORAL_ANALYSIS.SESSION_TIMEOUT)
        return current_time - self.current_session.last_activity > timeout
    
    def _validate_event(self, event: Dict, event_type: str) -> bool:
        """Validate event data"""
        try:
            if event_type == 'keystroke':
                required_fields = {'key', 'press_time', 'release_time', 'timestamp'}
            else:  # mouse
                required_fields = {'event_type', 'x_coord', 'y_coord', 'timestamp'}
            
            if not all(field in event for field in required_fields):
                logger.warning(f"Missing required fields in {event_type} event")
                return False
            
            # Validate timestamp
            if not isinstance(event['timestamp'], (int, float)):
                logger.warning(f"Invalid timestamp in {event_type} event")
                return False
            
            # Validate coordinates for mouse events
            if event_type == 'mouse':
                if not isinstance(event['x_coord'], (int, float)) or not isinstance(event['y_coord'], (int, float)):
                    logger.warning("Invalid coordinates in mouse event")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating event: {str(e)}")
            return False
    
    def process_keystroke_event(self, event: Dict) -> None:
        """Process a new keystroke event"""
        try:
            if not self._validate_event(event, 'keystroke'):
                raise ValueError("Invalid keystroke event")
            
            if self._check_session_timeout():
                self.end_session()
            
            if not self.current_session:
                self.current_session = SessionState(
                    keystroke_events=[],
                    mouse_events=[],
                    start_time=datetime.now(),
                    risk_scores=[],
                    last_activity=datetime.now(),
                    user_info=None
                )
            
            keystroke_event = KeystrokeEvent(
                key=event['key'],
                press_time=event['press_time'],
                release_time=event['release_time'],
                pressure=event.get('pressure', 0.0),
                x_coord=event.get('x_coord', 0.0),
                y_coord=event.get('y_coord', 0.0),
                timestamp=datetime.fromtimestamp(event['timestamp'])
            )
            
            self.current_session.keystroke_events.append(keystroke_event)
            self.current_session.last_activity = datetime.now()
            
            self._update_risk_score()
            self._cleanup_old_sessions()
        except Exception as e:
            logger.error(f"Error processing keystroke event: {str(e)}")
            raise
    
    def process_mouse_event(self, event: Dict) -> None:
        """Process a new mouse event"""
        try:
            if not self._validate_event(event, 'mouse'):
                raise ValueError("Invalid mouse event")
            
            if self._check_session_timeout():
                self.end_session()
            
            if not self.current_session:
                self.current_session = SessionState(
                    keystroke_events=[],
                    mouse_events=[],
                    start_time=datetime.now(),
                    risk_scores=[],
                    last_activity=datetime.now(),
                    user_info=None
                )
            
            mouse_event = MouseEvent(
                event_type=event['event_type'],
                x_coord=event['x_coord'],
                y_coord=event['y_coord'],
                pressure=event.get('pressure', 0.0),
                timestamp=datetime.fromtimestamp(event['timestamp']),
                velocity=event.get('velocity'),
                acceleration=event.get('acceleration')
            )
            
            self.current_session.mouse_events.append(mouse_event)
            self.current_session.last_activity = datetime.now()
            
            self._update_risk_score()
            self._cleanup_old_sessions()
        except Exception as e:
            logger.error(f"Error processing mouse event: {str(e)}")
            raise
    
    def _update_risk_score(self) -> None:
        """Update the composite risk score based on both analyzers"""
        try:
            if not self.current_session:
                return
                
            keystroke_risk = self.keystroke_analyzer.calculate_risk_score(
                self.current_session.keystroke_events
            )
            mouse_risk = self.mouse_analyzer.calculate_risk_score(
                self.current_session.mouse_events
            )
            
            # Weighted combination of risk scores
            composite_risk = (
                settings.KEYSTROKE_WEIGHT * keystroke_risk +
                settings.MOUSE_WEIGHT * mouse_risk
            )
            
            # Check for anomalies
            is_anomaly = self._detect_anomaly(composite_risk)
            if is_anomaly:
                self.current_session.anomaly_count += 1
                self.current_session.consecutive_anomalies += 1
                
                if self.current_session.consecutive_anomalies >= self.current_session.max_anomaly_threshold:
                    self._handle_consecutive_anomalies()
            else:
                self.current_session.consecutive_anomalies = 0
            
            self.current_session.risk_scores.append({
                'timestamp': datetime.now(),
                'keystroke_risk': keystroke_risk,
                'mouse_risk': mouse_risk,
                'composite_risk': composite_risk,
                'is_anomaly': is_anomaly
            })
        except Exception as e:
            logger.error(f"Error updating risk score: {str(e)}")
            raise
    
    def _detect_anomaly(self, risk_score: float) -> bool:
        """Detect if the current risk score is anomalous"""
        if not self.current_session or not self.current_session.risk_scores:
            return False
            
        recent_scores = [
            score['composite_risk']
            for score in self.current_session.risk_scores[-settings.DRIFT_DETECTION_WINDOW:]
        ]
        
        if not recent_scores:
            return False
            
        mean_score = np.mean(recent_scores)
        std_score = np.std(recent_scores)
        
        return (
            risk_score > mean_score + 2 * std_score or
            risk_score < mean_score - 2 * std_score
        )
    
    def _handle_consecutive_anomalies(self) -> None:
        """Handle consecutive anomalies"""
        if not self.current_session:
            return
            
        # Generate pattern signature
        pattern = self._generate_pattern_signature()
        
        # Check if pattern is blocked
        if pattern in self.blocked_patterns:
            logger.warning(f"Blocked pattern detected: {pattern}")
            self._collect_forensic_evidence("blocked_pattern")
            return
        
        # Update pattern frequency
        self.anomaly_patterns[pattern] = self.anomaly_patterns.get(pattern, 0) + 1
        
        # Block pattern if it occurs too frequently
        if self.anomaly_patterns[pattern] >= settings.BEHAVIORAL_ANALYSIS.MAX_EVENTS:
            self.blocked_patterns.add(pattern)
            logger.warning(f"Pattern blocked due to frequency: {pattern}")
            self._collect_forensic_evidence("pattern_blocked")
    
    def _generate_pattern_signature(self) -> str:
        """Generate a signature for the current pattern"""
        if not self.current_session:
            return ""
            
        recent_events = (
            self.current_session.keystroke_events[-10:] +
            self.current_session.mouse_events[-10:]
        )
        
        # Sort events by timestamp
        recent_events.sort(key=lambda x: x.timestamp)
        
        # Generate signature based on event sequence
        signature = []
        for event in recent_events:
            if isinstance(event, KeystrokeEvent):
                signature.append(f"k:{event.key}")
            else:
                signature.append(f"m:{event.event_type}")
        
        return "|".join(signature)
    
    def get_current_risk_score(self) -> float:
        """Get the current composite risk score"""
        if not self.current_session or not self.current_session.risk_scores:
            return 0.0
        return self.current_session.risk_scores[-1]['composite_risk']
    
    def detect_behavioral_drift(self) -> bool:
        """Detect if there's significant behavioral drift"""
        try:
            if not self.current_session or len(self.current_session.risk_scores) < settings.MIN_EVENTS_FOR_ANALYSIS:
                return False
                
            recent_scores = [
                score['composite_risk']
                for score in self.current_session.risk_scores[-settings.DRIFT_DETECTION_WINDOW:]
            ]
            mean_score = np.mean(recent_scores)
            std_score = np.std(recent_scores)
            
            return (
                mean_score > settings.DRIFT_SCORE_THRESHOLD or
                std_score > settings.DRIFT_VARIANCE_THRESHOLD
            )
        except Exception as e:
            logger.error(f"Error detecting behavioral drift: {str(e)}")
            return False
    
    def end_session(self) -> Dict:
        """End the current session and archive it"""
        try:
            if not self.current_session:
                return {}
                
            session_data = {
                'keystroke_events': [
                    {
                        'key': e.key,
                        'press_time': e.press_time,
                        'release_time': e.release_time,
                        'pressure': e.pressure,
                        'x_coord': e.x_coord,
                        'y_coord': e.y_coord,
                        'timestamp': e.timestamp.isoformat()
                    }
                    for e in self.current_session.keystroke_events
                ],
                'mouse_events': [
                    {
                        'event_type': e.event_type,
                        'x_coord': e.x_coord,
                        'y_coord': e.y_coord,
                        'pressure': e.pressure,
                        'timestamp': e.timestamp.isoformat(),
                        'velocity': e.velocity,
                        'acceleration': e.acceleration
                    }
                    for e in self.current_session.mouse_events
                ],
                'start_time': self.current_session.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'risk_scores': self.current_session.risk_scores,
                'anomaly_count': self.current_session.anomaly_count,
                'user_info': self.current_session.user_info
            }
            
            self.session_history.append(session_data)
            
            # Create new session
            self.current_session = SessionState(
                keystroke_events=[],
                mouse_events=[],
                start_time=datetime.now(),
                risk_scores=[],
                last_activity=datetime.now(),
                user_info=None
            )
            
            return session_data
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            raise
    
    def generate_forensic_evidence(self, reason: str) -> Dict:
        """Generate forensic evidence for the current session"""
        try:
            if not self.current_session or not self.current_session.risk_scores:
                return {}
                
            latest_risk = self.current_session.risk_scores[-1]
            
            evidence = {
                'timestamp': datetime.now().isoformat(),
                'reason': reason,
                'session_duration': (datetime.now() - self.current_session.start_time).total_seconds(),
                'event_counts': {
                    'keystrokes': len(self.current_session.keystroke_events),
                    'mouse_events': len(self.current_session.mouse_events)
                },
                'risk_metrics': {
                    'current_composite_risk': latest_risk['composite_risk'],
                    'keystroke_risk': latest_risk['keystroke_risk'],
                    'mouse_risk': latest_risk['mouse_risk'],
                    'risk_trend': self._calculate_risk_trend(),
                    'anomaly_count': self.current_session.anomaly_count,
                    'consecutive_anomalies': self.current_session.consecutive_anomalies
                },
                'behavioral_indicators': {
                    'has_drift': self.detect_behavioral_drift(),
                    'event_frequency': self._calculate_event_frequency(),
                    'blocked_patterns': list(self.blocked_patterns),
                    'pattern_frequencies': self.anomaly_patterns
                }
            }
            
            # Save forensic evidence to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            forensic_file = self.forensic_dir / f"forensic_{reason}_{timestamp}.json"
            with open(forensic_file, 'w') as f:
                json.dump(evidence, f, indent=2)
            
            return evidence
        except Exception as e:
            logger.error(f"Error generating forensic evidence: {str(e)}")
            return {}
    
    def _calculate_risk_trend(self) -> str:
        """Calculate the trend of risk scores"""
        try:
            if not self.current_session or len(self.current_session.risk_scores) < 2:
                return "insufficient_data"
                
            recent_scores = [
                score['composite_risk']
                for score in self.current_session.risk_scores[-5:]
            ]
            if np.mean(recent_scores) > np.mean(recent_scores[:-1]):
                return "increasing"
            elif np.mean(recent_scores) < np.mean(recent_scores[:-1]):
                return "decreasing"
            else:
                return "stable"
        except Exception as e:
            logger.error(f"Error calculating risk trend: {str(e)}")
            return "error"
    
    def _calculate_event_frequency(self) -> Dict[str, float]:
        """Calculate event frequencies per second"""
        try:
            if not self.current_session:
                return {'keystrokes': 0, 'mouse_events': 0}
                
            duration = (datetime.now() - self.current_session.start_time).total_seconds()
            if duration == 0:
                return {'keystrokes': 0, 'mouse_events': 0}
                
            return {
                'keystrokes': len(self.current_session.keystroke_events) / duration,
                'mouse_events': len(self.current_session.mouse_events) / duration
            }
        except Exception as e:
            logger.error(f"Error calculating event frequency: {str(e)}")
            return {'keystrokes': 0, 'mouse_events': 0} 