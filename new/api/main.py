from fastapi import FastAPI, WebSocket, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, Optional, Set
from pydantic import BaseModel, Field
import time
from collections import defaultdict
import asyncio

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

# Rate limiting and IP blocking
rate_limit = defaultdict(list)
ip_blocks = {}
failed_attempts = defaultdict(int)
active_connections = defaultdict(set)

async def check_rate_limit(request: Request) -> None:
    client_ip = request.client.host
    current_time = time.time()
    
    # Check if IP is blocked
    if client_ip in ip_blocks:
        block_end = ip_blocks[client_ip]
        if current_time < block_end:
            raise HTTPException(
                status_code=403,
                detail=f"IP address blocked until {datetime.fromtimestamp(block_end)}"
            )
        else:
            del ip_blocks[client_ip]
    
    # Clean old requests
    rate_limit[client_ip] = [
        t for t in rate_limit[client_ip]
        if current_time - t < settings.SECURITY.RATE_LIMIT_WINDOW
    ]
    
    # Check rate limit
    if len(rate_limit[client_ip]) >= settings.SECURITY.RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        )
    
    rate_limit[client_ip].append(current_time)

async def check_connection_limit(request: Request) -> None:
    client_ip = request.client.host
    user_id = request.headers.get("X-User-ID")
    
    # Check IP connection limit
    if len(active_connections[client_ip]) >= settings.SECURITY.MAX_CONNECTIONS_PER_IP:
        raise HTTPException(
            status_code=429,
            detail="Too many connections from this IP"
        )
    
    # Check user connection limit
    if user_id and len(active_connections[user_id]) >= settings.SECURITY.MAX_CONNECTIONS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail="Too many connections for this user"
        )
    
    # Add connection
    active_connections[client_ip].add(current_time)
    if user_id:
        active_connections[user_id].add(current_time)

async def cleanup_connections():
    """Clean up expired connections"""
    while True:
        current_time = time.time()
        for key in list(active_connections.keys()):
            active_connections[key] = {
                t for t in active_connections[key]
                if current_time - t < settings.SECURITY.RATE_LIMIT_WINDOW
            }
            if not active_connections[key]:
                del active_connections[key]
        await asyncio.sleep(60)  # Run every minute

# Start cleanup task
asyncio.create_task(cleanup_connections())

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
    allowed_hosts=settings.CORS.ALLOWED_ORIGINS
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
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.API.VERSION
    }

@app.post("/api/v1/events/keystroke")
async def process_keystroke_event(event: KeystrokeEvent, request: Request):
    """Process a keystroke event"""
    try:
        await check_rate_limit(request)
        await check_connection_limit(request)
        
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
        await check_rate_limit(request)
        await check_connection_limit(request)
        
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
        await check_rate_limit(request)
        await check_connection_limit(request)
        
        status = risk_engine.get_session_status(user_id)
        return status
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/sessions/{user_id}/end")
async def end_session(user_id: str, request: Request):
    """End a user session"""
    try:
        await check_rate_limit(request)
        await check_connection_limit(request)
        
        session_data = risk_engine.end_session(user_id)
        return session_data
    except Exception as e:
        logger.error(f"Error ending session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/risk-levels")
async def get_risk_levels(request: Request):
    """Get risk level thresholds"""
    await check_rate_limit(request)
    await check_connection_limit(request)
    return settings.RISK_THRESHOLDS

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event processing"""
    client_ip = websocket.client.host
    
    # Check rate limit for WebSocket connection
    if len(active_connections[client_ip]) >= settings.SECURITY.MAX_CONNECTIONS_PER_IP:
        await websocket.close(code=1008, reason="Too many connections")
        return
    
    await websocket.accept()
    active_connections[client_ip].add(time.time())
    
    try:
        while True:
            try:
                # Receive event with timeout
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                
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
                
            except asyncio.TimeoutError:
                await websocket.send_json({
                    'error': 'Connection timeout'
                })
                break
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
            # Clean up connection
            if client_ip in active_connections:
                active_connections[client_ip].remove(time.time())
                if not active_connections[client_ip]:
                    del active_connections[client_ip]
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