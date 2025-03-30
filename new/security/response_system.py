from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import logging
import asyncio
import aiohttp
import json
from pathlib import Path
from config.settings import settings

logger = logging.getLogger(__name__)

class ResponseSystem:
    def __init__(self, risk_thresholds: Optional[Dict[str, float]] = None, actions: Optional[Dict[str, List[str]]] = None):
        self.risk_thresholds = risk_thresholds or settings.RISK_THRESHOLDS
        self.actions = actions or {
            'warning': ['notify_admin', 'increase_monitoring'],
            'critical': ['lock_session', 'collect_forensics']
        }
        self.active_responses: Dict[str, List[Dict]] = {}
        self.notification_queue = asyncio.Queue()
        self.blocked_users: Dict[str, datetime] = {}
        self.failed_attempts: Dict[str, int] = {}
        self.forensic_dir = Path("forensics")
        self.forensic_dir.mkdir(exist_ok=True)
        
        # Circuit breaker settings
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 300  # 5 minutes
        self.circuit_breaker_failures: Dict[str, int] = {}
        self.circuit_breaker_last_failure: Dict[str, datetime] = {}
    
    async def handle_risk_level(self, user_id: str, risk_level: str, risk_score: float) -> Dict:
        """Handle different risk levels with appropriate responses"""
        try:
            # Check if user is blocked
            if user_id in self.blocked_users:
                block_end = self.blocked_users[user_id]
                if datetime.now() < block_end:
                    logger.warning(f"Blocked user {user_id} attempted to access system")
                    return {
                        'error': 'User is blocked',
                        'block_until': block_end.isoformat()
                    }
                else:
                    del self.blocked_users[user_id]
            
            # Check circuit breaker
            if self._is_circuit_breaker_open(user_id):
                logger.warning(f"Circuit breaker open for user {user_id}")
                return {
                    'error': 'Service temporarily unavailable',
                    'retry_after': self._get_circuit_breaker_retry_time(user_id)
                }
            
            if risk_level == 'critical':
                return await self._handle_critical_risk(user_id, risk_score)
            elif risk_level == 'high':
                return await self._handle_high_risk(user_id, risk_score)
            elif risk_level == 'medium':
                return await self._handle_medium_risk(user_id, risk_score)
            else:
                return await self._handle_low_risk(user_id, risk_score)
        except Exception as e:
            logger.error(f"Error handling risk level: {str(e)}")
            self._record_circuit_breaker_failure(user_id)
            return {'error': str(e)}
    
    def _is_circuit_breaker_open(self, user_id: str) -> bool:
        """Check if circuit breaker is open for a user"""
        if user_id not in self.circuit_breaker_failures:
            return False
            
        failures = self.circuit_breaker_failures[user_id]
        last_failure = self.circuit_breaker_last_failure[user_id]
        
        if failures >= self.circuit_breaker_threshold:
            if datetime.now() - last_failure < timedelta(seconds=self.circuit_breaker_timeout):
                return True
            else:
                # Reset circuit breaker
                self.circuit_breaker_failures[user_id] = 0
                return False
        return False
    
    def _get_circuit_breaker_retry_time(self, user_id: str) -> int:
        """Get time until circuit breaker can be retried"""
        if user_id not in self.circuit_breaker_last_failure:
            return 0
            
        last_failure = self.circuit_breaker_last_failure[user_id]
        retry_time = (last_failure + timedelta(seconds=self.circuit_breaker_timeout) - datetime.now()).total_seconds()
        return max(0, int(retry_time))
    
    def _record_circuit_breaker_failure(self, user_id: str) -> None:
        """Record a circuit breaker failure"""
        self.circuit_breaker_failures[user_id] = self.circuit_breaker_failures.get(user_id, 0) + 1
        self.circuit_breaker_last_failure[user_id] = datetime.now()
    
    async def _handle_critical_risk(self, user_id: str, risk_score: float) -> Dict:
        """Handle critical risk level"""
        actions = self.actions['critical']
        response = {
            'timestamp': datetime.now().isoformat(),
            'risk_level': 'critical',
            'risk_score': risk_score,
            'actions_taken': []
        }
        
        try:
            for action in actions:
                if action == 'lock_session':
                    await self._lock_session(user_id)
                    response['actions_taken'].append('lock_session')
                elif action == 'collect_forensics':
                    await self._collect_forensics(user_id)
                    response['actions_taken'].append('collect_forensics')
            
            await self._notify_admin(user_id, 'critical', risk_score)
            self._block_user(user_id)
            return response
        except Exception as e:
            logger.error(f"Error handling critical risk: {str(e)}")
            self._record_circuit_breaker_failure(user_id)
            raise
    
    async def _handle_high_risk(self, user_id: str, risk_score: float) -> Dict:
        """Handle high risk level"""
        actions = self.actions['warning']
        response = {
            'timestamp': datetime.now().isoformat(),
            'risk_level': 'high',
            'risk_score': risk_score,
            'actions_taken': []
        }
        
        try:
            for action in actions:
                if action == 'notify_admin':
                    await self._notify_admin(user_id, 'high', risk_score)
                    response['actions_taken'].append('notify_admin')
                elif action == 'increase_monitoring':
                    await self._increase_monitoring(user_id)
                    response['actions_taken'].append('increase_monitoring')
            
            return response
        except Exception as e:
            logger.error(f"Error handling high risk: {str(e)}")
            self._record_circuit_breaker_failure(user_id)
            raise
    
    async def _handle_medium_risk(self, user_id: str, risk_score: float) -> Dict:
        """Handle medium risk level"""
        return {
            'timestamp': datetime.now().isoformat(),
            'risk_level': 'medium',
            'risk_score': risk_score,
            'actions_taken': ['monitor']
        }
    
    async def _handle_low_risk(self, user_id: str, risk_score: float) -> Dict:
        """Handle low risk level"""
        return {
            'timestamp': datetime.now().isoformat(),
            'risk_level': 'low',
            'risk_score': risk_score,
            'actions_taken': ['normal_monitoring']
        }
    
    async def _lock_session(self, user_id: str) -> None:
        """Lock user session"""
        try:
            # Implement session locking logic here
            logger.info(f"Locked session for user: {user_id}")
            self._block_user(user_id)
        except Exception as e:
            logger.error(f"Failed to lock session: {str(e)}")
            raise
    
    async def _collect_forensics(self, user_id: str) -> None:
        """Collect forensic evidence"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            forensic_file = self.forensic_dir / f"forensic_{user_id}_{timestamp}.json"
            
            forensic_data = {
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'active_responses': self.active_responses.get(user_id, []),
                'risk_scores': self._get_recent_risk_scores(user_id),
                'system_state': {
                    'blocked_users': list(self.blocked_users.keys()),
                    'failed_attempts': dict(self.failed_attempts),
                    'circuit_breaker_status': {
                        user: {
                            'failures': self.circuit_breaker_failures.get(user, 0),
                            'last_failure': self.circuit_breaker_last_failure.get(user, None)
                        }
                        for user in self.circuit_breaker_failures
                    }
                }
            }
            
            with open(forensic_file, 'w') as f:
                json.dump(forensic_data, f, indent=2)
            
            logger.info(f"Collected forensics for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to collect forensics: {str(e)}")
            raise
    
    def _get_recent_risk_scores(self, user_id: str) -> List[Dict]:
        """Get recent risk scores for a user"""
        if user_id not in self.active_responses:
            return []
            
        return [
            {
                'timestamp': response['timestamp'],
                'risk_score': response.get('risk_score', 0),
                'risk_level': response.get('risk_level', 'unknown')
            }
            for response in self.active_responses[user_id][-10:]  # Last 10 responses
        ]
    
    async def _notify_admin(self, user_id: str, risk_level: str, risk_score: float) -> None:
        """Notify administrators"""
        try:
            notification = {
                'user_id': user_id,
                'risk_level': risk_level,
                'risk_score': risk_score,
                'timestamp': datetime.now().isoformat(),
                'context': {
                    'blocked': user_id in self.blocked_users,
                    'failed_attempts': self.failed_attempts.get(user_id, 0),
                    'circuit_breaker_status': {
                        'failures': self.circuit_breaker_failures.get(user_id, 0),
                        'last_failure': self.circuit_breaker_last_failure.get(user_id, None)
                    }
                }
            }
            await self.notification_queue.put(notification)
            logger.info(f"Queued admin notification for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to queue admin notification: {str(e)}")
            raise
    
    async def _increase_monitoring(self, user_id: str) -> None:
        """Increase monitoring level for user"""
        try:
            if user_id not in self.active_responses:
                self.active_responses[user_id] = []
            
            self.active_responses[user_id].append({
                'action': 'increase_monitoring',
                'timestamp': datetime.now().isoformat(),
                'risk_level': 'high'
            })
            logger.info(f"Increased monitoring for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to increase monitoring: {str(e)}")
            raise
    
    def _block_user(self, user_id: str) -> None:
        """Block a user"""
        block_duration = timedelta(hours=1)  # Default 1 hour block
        self.blocked_users[user_id] = datetime.now() + block_duration
        logger.warning(f"Blocked user: {user_id} until {self.blocked_users[user_id]}")
    
    async def process_notifications(self) -> None:
        """Process queued notifications"""
        while True:
            try:
                notification = await self.notification_queue.get()
                # Implement notification processing logic here
                logger.info(f"Processed notification: {notification}")
                self.notification_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing notification: {str(e)}")
            await asyncio.sleep(1)
    
    def get_active_responses(self, user_id: str) -> List[Dict]:
        """Get active responses for a user"""
        return self.active_responses.get(user_id, [])
    
    async def cleanup_responses(self, user_id: str) -> None:
        """Clean up responses for a user"""
        if user_id in self.active_responses:
            del self.active_responses[user_id]
            logger.info(f"Cleaned up responses for user: {user_id}")
    
    async def start(self) -> None:
        """Start the response system"""
        # Start notification processor
        asyncio.create_task(self.process_notifications())
        logger.info("Response system started")
    
    async def stop(self) -> None:
        """Stop the response system"""
        # Clean up resources
        self.active_responses.clear()
        self.blocked_users.clear()
        self.failed_attempts.clear()
        self.circuit_breaker_failures.clear()
        self.circuit_breaker_last_failure.clear()
        logger.info("Response system stopped") 