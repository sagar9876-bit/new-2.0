from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import json
import aiohttp
from ldap3 import Server, Connection, SUBTREE
from config.settings import settings

logger = logging.getLogger(__name__)

class RiskEngine:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.last_cleanup = datetime.now()
        self._setup_ad_connection()
        self._setup_siem_connection()
    
    def _setup_ad_connection(self) -> None:
        """Setup Active Directory connection"""
        try:
            self.ad_server = Server(
                settings.AD_SERVER,
                port=settings.AD_PORT,
                use_ssl=settings.AD_USE_SSL
            )
            self.ad_conn = Connection(
                self.ad_server,
                user=settings.AD_USER,
                password=settings.AD_PASSWORD,
                auto_bind=True
            )
            logger.info("Successfully connected to Active Directory")
        except Exception as e:
            logger.error(f"Failed to connect to Active Directory: {str(e)}")
            self.ad_conn = None
    
    def _setup_siem_connection(self) -> None:
        """Setup SIEM connection"""
        try:
            self.siem_session = aiohttp.ClientSession(
                base_url=settings.SIEM_ENDPOINT,
                headers={'Authorization': f'Bearer {settings.SIEM_API_KEY}'}
            )
            logger.info("Successfully setup SIEM connection")
        except Exception as e:
            logger.error(f"Failed to setup SIEM connection: {str(e)}")
            self.siem_session = None
    
    def _cleanup_sessions(self) -> None:
        """Clean up expired sessions"""
        try:
            current_time = datetime.now()
            if (current_time - self.last_cleanup).total_seconds() < settings.SESSION_CLEANUP_INTERVAL:
                return
                
            timeout = timedelta(seconds=settings.SESSION_TIMEOUT)
            expired_sessions = [
                session_id for session_id, session in self.sessions.items()
                if current_time - session['last_activity'] > timeout
            ]
            
            for session_id in expired_sessions:
                self.end_session(session_id)
                
            self.last_cleanup = current_time
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {str(e)}")
    
    def _get_user_info(self, username: str) -> Optional[Dict]:
        """Get user information from Active Directory"""
        if not self.ad_conn:
            logger.warning("AD connection not available")
            return None
            
        try:
            self.ad_conn.search(
                settings.AD_BASE_DN,
                f'(sAMAccountName={username})',
                search_scope=SUBTREE,
                attributes=['*']
            )
            
            if self.ad_conn.entries:
                entry = self.ad_conn.entries[0]
                return {
                    'username': entry.sAMAccountName.value,
                    'email': entry.mail.value if hasattr(entry, 'mail') else None,
                    'department': entry.department.value if hasattr(entry, 'department') else None,
                    'last_login': entry.lastLogon.value if hasattr(entry, 'lastLogon') else None,
                    'account_status': entry.userAccountControl.value if hasattr(entry, 'userAccountControl') else None
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user info from AD: {str(e)}")
            return None
    
    async def _log_to_siem(self, event: Dict) -> None:
        """Log event to SIEM system"""
        if not self.siem_session:
            logger.warning("SIEM connection not available")
            return
            
        try:
            async with self.siem_session.post('/events', json=event) as response:
                if response.status != 200:
                    logger.error(f"Failed to log to SIEM: {await response.text()}")
        except Exception as e:
            logger.error(f"Error logging to SIEM: {str(e)}")
    
    def process_event(self, session_id: str, event: Dict) -> Dict:
        """Process a new behavioral event"""
        try:
            self._cleanup_sessions()
            
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    'events': [],
                    'risk_scores': [],
                    'start_time': datetime.now(),
                    'last_activity': datetime.now(),
                    'user_info': self._get_user_info(event.get('username'))
                }
            
            session = self.sessions[session_id]
            session['events'].append(event)
            session['last_activity'] = datetime.now()
            
            risk_score = self._calculate_risk_score(session)
            session['risk_scores'].append({
                'timestamp': datetime.now(),
                'score': risk_score
            })
            
            risk_level = self._determine_risk_level(risk_score)
            actions = self._get_actions(risk_level)
            
            # Log to SIEM asynchronously
            event_data = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'event_type': event.get('type'),
                'risk_score': risk_score,
                'risk_level': risk_level,
                'actions_taken': actions
            }
            asyncio.create_task(self._log_to_siem(event_data))
            
            return {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'actions': actions
            }
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
            return {
                'risk_score': 0,
                'risk_level': 'unknown',
                'actions': []
            }
    
    def _calculate_risk_score(self, session: Dict) -> float:
        """Calculate risk score based on event history"""
        try:
            if not session['events']:
                return 0.0
                
            # Calculate base risk from event patterns
            base_risk = sum(
                event.get('risk_weight', 1.0)
                for event in session['events'][-settings.RISK_CALCULATION_WINDOW:]
            )
            
            # Adjust for behavioral anomalies
            if len(session['events']) >= settings.MIN_EVENTS_FOR_ANALYSIS:
                anomaly_score = self._detect_anomalies(session['events'])
                base_risk *= (1 + anomaly_score)
            
            return min(base_risk, 100.0)
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 0.0
    
    def _detect_anomalies(self, events: List[Dict]) -> float:
        """Detect behavioral anomalies"""
        try:
            # Calculate event timing patterns
            timestamps = [
                datetime.fromisoformat(event['timestamp'])
                for event in events
            ]
            intervals = [
                (timestamps[i] - timestamps[i-1]).total_seconds()
                for i in range(1, len(timestamps))
            ]
            
            if not intervals:
                return 0.0
                
            mean_interval = sum(intervals) / len(intervals)
            std_interval = (
                sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
            ) ** 0.5
            
            # Detect unusual patterns
            anomaly_score = 0.0
            for interval in intervals:
                if abs(interval - mean_interval) > 2 * std_interval:
                    anomaly_score += 0.1
            
            return min(anomaly_score, 1.0)
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            return 0.0
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level based on score"""
        if risk_score >= settings.RISK_THRESHOLDS.CRITICAL:
            return 'critical'
        elif risk_score >= settings.RISK_THRESHOLDS.HIGH:
            return 'high'
        elif risk_score >= settings.RISK_THRESHOLDS.MEDIUM:
            return 'medium'
        else:
            return 'low'
    
    def _get_actions(self, risk_level: str) -> List[str]:
        """Get actions to take based on risk level"""
        actions = []
        
        if risk_level == 'critical':
            actions.extend(settings.RESPONSE_ACTIONS.CRITICAL)
        elif risk_level == 'high':
            actions.extend(settings.RESPONSE_ACTIONS.HIGH)
        elif risk_level == 'medium':
            actions.extend(settings.RESPONSE_ACTIONS.MEDIUM)
        else:
            actions.extend(settings.RESPONSE_ACTIONS.LOW)
        
        return actions
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get current status of a session"""
        try:
            if session_id not in self.sessions:
                return None
                
            session = self.sessions[session_id]
            current_risk = session['risk_scores'][-1]['score'] if session['risk_scores'] else 0
            
            return {
                'session_id': session_id,
                'start_time': session['start_time'].isoformat(),
                'last_activity': session['last_activity'].isoformat(),
                'event_count': len(session['events']),
                'current_risk_score': current_risk,
                'risk_level': self._determine_risk_level(current_risk),
                'user_info': session['user_info']
            }
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            return None
    
    def end_session(self, session_id: str) -> Optional[Dict]:
        """End a session and return summary"""
        try:
            if session_id not in self.sessions:
                return None
                
            session = self.sessions[session_id]
            session['end_time'] = datetime.now()
            
            # Generate session summary
            summary = {
                'session_id': session_id,
                'start_time': session['start_time'].isoformat(),
                'end_time': session['end_time'].isoformat(),
                'duration': (session['end_time'] - session['start_time']).total_seconds(),
                'event_count': len(session['events']),
                'risk_history': session['risk_scores'],
                'user_info': session['user_info']
            }
            
            # Log final session data to SIEM
            asyncio.create_task(self._log_to_siem({
                'type': 'session_end',
                'session_summary': summary
            }))
            
            del self.sessions[session_id]
            return summary
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            return None
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.siem_session:
                await self.siem_session.close()
            if self.ad_conn:
                self.ad_conn.unbind()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}") 