from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta
import logging
from pathlib import Path
import joblib
from .keystroke_analyzer_v2 import KeystrokeAnalyzer, KeystrokeEvent
from .mouse_analyzer_v2 import MouseAnalyzer, MouseEvent
from config.settings import settings

logger = logging.getLogger(__name__)

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
        self.current_session: Dict = {
            'keystroke_events': [],
            'mouse_events': [],
            'start_time': datetime.now(),
            'risk_scores': []
        }
        self.last_cleanup = datetime.now()
    
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
        current_time = datetime.now()
        timeout = timedelta(seconds=settings.BEHAVIORAL_ANALYSIS.SESSION_TIMEOUT)
        return current_time - self.current_session['start_time'] > timeout
    
    def process_keystroke_event(self, event: KeystrokeEvent) -> None:
        """Process a new keystroke event"""
        try:
            if self._check_session_timeout():
                self.end_session()
            
            self.current_session['keystroke_events'].append(event)
            self._update_risk_score()
            self._cleanup_old_sessions()
        except Exception as e:
            logger.error(f"Error processing keystroke event: {str(e)}")
            raise
    
    def process_mouse_event(self, event: MouseEvent) -> None:
        """Process a new mouse event"""
        try:
            if self._check_session_timeout():
                self.end_session()
            
            self.current_session['mouse_events'].append(event)
            self._update_risk_score()
            self._cleanup_old_sessions()
        except Exception as e:
            logger.error(f"Error processing mouse event: {str(e)}")
            raise
    
    def _update_risk_score(self) -> None:
        """Update the composite risk score based on both analyzers"""
        try:
            keystroke_risk = self.keystroke_analyzer.calculate_risk_score(
                self.current_session['keystroke_events']
            )
            mouse_risk = self.mouse_analyzer.calculate_risk_score(
                self.current_session['mouse_events']
            )
            
            # Weighted combination of risk scores
            composite_risk = (
                settings.KEYSTROKE_WEIGHT * keystroke_risk +
                settings.MOUSE_WEIGHT * mouse_risk
            )
            
            self.current_session['risk_scores'].append({
                'timestamp': datetime.now(),
                'keystroke_risk': keystroke_risk,
                'mouse_risk': mouse_risk,
                'composite_risk': composite_risk
            })
        except Exception as e:
            logger.error(f"Error updating risk score: {str(e)}")
            raise
    
    def get_current_risk_score(self) -> float:
        """Get the current composite risk score"""
        if not self.current_session['risk_scores']:
            return 0.0
        return self.current_session['risk_scores'][-1]['composite_risk']
    
    def detect_behavioral_drift(self) -> bool:
        """Detect if there's significant behavioral drift"""
        try:
            if len(self.current_session['risk_scores']) < settings.MIN_EVENTS_FOR_ANALYSIS:
                return False
                
            recent_scores = [
                score['composite_risk']
                for score in self.current_session['risk_scores'][-settings.DRIFT_DETECTION_WINDOW:]
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
            self.current_session['end_time'] = datetime.now()
            self.session_history.append(self.current_session)
            
            # Create new session
            self.current_session = {
                'keystroke_events': [],
                'mouse_events': [],
                'start_time': datetime.now(),
                'risk_scores': []
            }
            
            return self.session_history[-1]
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            raise
    
    def generate_forensic_evidence(self) -> Dict:
        """Generate forensic evidence for the current session"""
        try:
            if not self.current_session['risk_scores']:
                return {}
                
            latest_risk = self.current_session['risk_scores'][-1]
            
            return {
                'timestamp': datetime.now().isoformat(),
                'session_duration': (datetime.now() - self.current_session['start_time']).total_seconds(),
                'event_counts': {
                    'keystrokes': len(self.current_session['keystroke_events']),
                    'mouse_events': len(self.current_session['mouse_events'])
                },
                'risk_metrics': {
                    'current_composite_risk': latest_risk['composite_risk'],
                    'keystroke_risk': latest_risk['keystroke_risk'],
                    'mouse_risk': latest_risk['mouse_risk'],
                    'risk_trend': self._calculate_risk_trend()
                },
                'behavioral_indicators': {
                    'has_drift': self.detect_behavioral_drift(),
                    'event_frequency': self._calculate_event_frequency()
                }
            }
        except Exception as e:
            logger.error(f"Error generating forensic evidence: {str(e)}")
            return {}
    
    def _calculate_risk_trend(self) -> str:
        """Calculate the trend of risk scores"""
        try:
            if len(self.current_session['risk_scores']) < 2:
                return "insufficient_data"
                
            recent_scores = [
                score['composite_risk']
                for score in self.current_session['risk_scores'][-5:]
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
            duration = (datetime.now() - self.current_session['start_time']).total_seconds()
            if duration == 0:
                return {'keystrokes': 0, 'mouse_events': 0}
                
            return {
                'keystrokes': len(self.current_session['keystroke_events']) / duration,
                'mouse_events': len(self.current_session['mouse_events']) / duration
            }
        except Exception as e:
            logger.error(f"Error calculating event frequency: {str(e)}")
            return {'keystrokes': 0, 'mouse_events': 0} 