from fastapi import FastAPI, WebSocket, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from datetime import datetime
import json
import logging
from typing import Dict, Optional
from pydantic import BaseModel, Field
import time
from collections import defaultdict

from core.behavioral_analysis.context_processor import ContextProcessor
from security.risk_engine import RiskEngine
from security.response_system import ResponseSystem
from config.settings import settings, setup_directories

# Setup required directories
setup_directories()

# Configure logging
logging.basicConfig(
    level=settings.LOGGING.LEVEL,
    format=settings.LOGGING.FORMAT,
    filename=settings.LOGGING.FILE
)

logger = logging.getLogger(__name__)

# Rate limiting
rate_limit = defaultdict(list)

def check_rate_limit(request: Request, limit: int = 100, window: int = 60):
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old requests
    rate_limit[client_ip] = [t for t in rate_limit[client_ip] if current_time - t < window]
    
    # Check rate limit
    if len(rate_limit[client_ip]) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests")
    
    rate_limit[client_ip].append(current_time)

# Input validation models
class KeystrokeEvent(BaseModel):
    user_id: str
    key: str
    timestamp: float
    pressure: Optional[float] = None
    hold_time: Optional[float] = None
    flight_time: Optional[float] = None

class MouseEvent(BaseModel):
    user_id: str
    x: float
    y: float
    timestamp: float
    pressure: Optional[float] = None
    velocity: Optional[float] = None
    acceleration: Optional[float] = None

app = FastAPI(
    title="Behavioral Biometrics API",
    description="API for behavioral biometrics analysis and risk assessment",
    version=settings.API.VERSION
)

# Configure CORS and trusted hosts
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS.ALLOWED_ORIGINS,
    allow_credentials=settings.CORS.ALLOW_CREDENTIALS,
    allow_methods=settings.CORS.ALLOWED_METHODS,
    allow_headers=settings.CORS.ALLOWED_HEADERS,
    max_age=settings.CORS.MAX_AGE
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure this based on your deployment
)

# Initialize components
risk_engine = RiskEngine(
    ad_integration=settings.ENTERPRISE_INTEGRATION.AD_ENABLED,
    siem_endpoint=settings.ENTERPRISE_INTEGRATION.SIEM_ENDPOINT
)

response_system = ResponseSystem(
    risk_thresholds=settings.RISK_THRESHOLDS,
    actions=settings.RESPONSE_ACTIONS
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/api/v1/events/keystroke")
async def process_keystroke_event(event: KeystrokeEvent, request: Request):
    """Process a keystroke event"""
    try:
        check_rate_limit(request)
        result = risk_engine.process_event(
            user_id=event.user_id,
            event_type='keystroke',
            event_data=event.dict()
        )
        return result
    except Exception as e:
        logger.error(f"Error processing keystroke event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/events/mouse")
async def process_mouse_event(event: MouseEvent, request: Request):
    """Process a mouse event"""
    try:
        check_rate_limit(request)
        result = risk_engine.process_event(
            user_id=event.user_id,
            event_type='mouse',
            event_data=event.dict()
        )
        return result
    except Exception as e:
        logger.error(f"Error processing mouse event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sessions/{user_id}/status")
async def get_session_status(user_id: str, request: Request):
    """Get current session status"""
    try:
        check_rate_limit(request)
        status = risk_engine.get_session_status(user_id)
        return status
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/sessions/{user_id}/end")
async def end_session(user_id: str, request: Request):
    """End a user session"""
    try:
        check_rate_limit(request)
        session_data = risk_engine.end_session(user_id)
        return session_data
    except Exception as e:
        logger.error(f"Error ending session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/risk-levels")
async def get_risk_levels(request: Request):
    """Get risk level thresholds"""
    check_rate_limit(request)
    return settings.RISK_THRESHOLDS

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event processing"""
    await websocket.accept()
    
    try:
        while True:
            try:
                # Receive event with timeout
                data = await websocket.receive_json()
                
                # Process event
                event_type = data.get('type')
                event_data = data.get('data', {})
                
                if event_type not in ['keystroke', 'mouse', 'disconnect']:
                    await websocket.send_json({
                        'error': 'Invalid event type'
                    })
                    continue
                
                if event_type == 'disconnect':
                    break
                
                # Process event through risk engine
                result = risk_engine.process_event(
                    user_id=event_data.get('user_id'),
                    event_type=event_type,
                    event_data=event_data
                )
                
                # Send response
                await websocket.send_json(result)
                
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await websocket.send_json({
                    'error': str(e)
                })
                continue
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.send_json({
            'error': str(e)
        })
    finally:
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.SERVER.HOST,
        port=settings.SERVER.PORT,
        reload=settings.SERVER.RELOAD,
        workers=settings.SERVER.WORKERS,
        log_level=settings.SERVER.LOG_LEVEL
    ) 