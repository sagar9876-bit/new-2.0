import asyncio
import websockets
import aiohttp
import json
from datetime import datetime
import random
import time
from typing import Dict, Optional, Tuple, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BehavioralClient:
    def __init__(
        self,
        server_url: str = "ws://localhost:8000/ws",
        api_url: str = "http://localhost:8000/api/v1"
    ):
        self.server_url = server_url
        self.api_url = api_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.session_id: Optional[str] = None
        self.is_connected: bool = False
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.response_queue: asyncio.Queue = asyncio.Queue()
        
    async def connect(self) -> bool:
        """Connect to the WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            self.is_connected = True
            self.session_id = f"session_{datetime.now().timestamp()}"
            
            # Start event processing
            asyncio.create_task(self._process_events())
            
            logger.info(f"Connected to server with session ID: {self.session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to server: {str(e)}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the WebSocket server"""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps({
                    'type': 'disconnect',
                    'data': {}
                }))
                await self.websocket.close()
                self.is_connected = False
                self.session_id = None
                logger.info("Disconnected from server")
            except Exception as e:
                logger.error(f"Error during disconnect: {str(e)}")
    
    async def send_event(self, event_type: str, event_data: Dict) -> Dict:
        """Send an event to the server"""
        if not self.is_connected:
            raise ConnectionError("Not connected to server")
            
        try:
            # Add session ID to event data
            event_data['session_id'] = self.session_id
            
            # Send event
            await self.websocket.send(json.dumps({
                'type': event_type,
                'data': event_data
            }))
            
            # Wait for response
            response = await self.websocket.recv()
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error sending event: {str(e)}")
            return {'error': str(e)}
    
    async def get_status(self) -> Dict:
        """Get current session status"""
        if not self.session_id:
            raise ValueError("No active session")
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/sessions/{self.session_id}/status") as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Error getting status: {str(e)}")
            return {'error': str(e)}
    
    async def end_session(self) -> Dict:
        """End the current session"""
        if not self.session_id:
            raise ValueError("No active session")
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/sessions/{self.session_id}/end") as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            return {'error': str(e)}
    
    async def simulate_behavior(self, num_events: int = 10) -> None:
        """Simulate user behavior by generating random events"""
        if not self.is_connected:
            raise ConnectionError("Not connected to server")
            
        for _ in range(num_events):
            # Randomly choose event type
            event_type = random.choice(['keystroke', 'mouse'])
            
            if event_type == 'keystroke':
                event_data = {
                    'key': random.choice('abcdefghijklmnopqrstuvwxyz'),
                    'press_time': time.time(),
                    'release_time': time.time() + random.uniform(0.1, 0.3),
                    'pressure': random.uniform(0.0, 1.0),
                    'x_coord': random.uniform(0, 1920),
                    'y_coord': random.uniform(0, 1080),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                event_data = {
                    'event_type': random.choice(['move', 'click', 'drag']),
                    'x_coord': random.uniform(0, 1920),
                    'y_coord': random.uniform(0, 1080),
                    'pressure': random.uniform(0.0, 1.0),
                    'timestamp': datetime.now().isoformat(),
                    'velocity': random.uniform(0, 100),
                    'acceleration': random.uniform(-10, 10)
                }
            
            await self.event_queue.put((event_type, event_data))
            await asyncio.sleep(random.uniform(0.1, 0.5))
    
    async def _process_events(self) -> None:
        """Process events from the queue"""
        while self.is_connected:
            try:
                event_type, event_data = await self.event_queue.get()
                response = await self.send_event(event_type, event_data)
                await self.response_queue.put(response)
                self.event_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing event: {str(e)}")
                await asyncio.sleep(1)
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make an HTTP request to the API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, f"{self.api_url}/{endpoint}", json=data) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Error making request: {str(e)}")
            return {'error': str(e)}

async def main():
    # Create client
    client = BehavioralClient()
    
    try:
        # Connect to server
        if not await client.connect():
            logger.error("Failed to connect to server")
            return
        
        # Simulate some behavior
        await client.simulate_behavior(num_events=5)
        
        # Get status
        status = await client.get_status()
        logger.info(f"Current status: {status}")
        
        # Wait for responses
        while not client.response_queue.empty():
            response = await client.response_queue.get()
            logger.info(f"Received response: {response}")
        
        # End session
        session_data = await client.end_session()
        logger.info(f"Session ended: {session_data}")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 