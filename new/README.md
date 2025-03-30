# Behavioral Biometrics System

A robust behavioral biometrics system that analyzes user behavior patterns through keystroke and mouse dynamics to detect potential security threats.

## Features

- Real-time behavioral analysis of keystroke and mouse patterns
- Risk scoring and threat detection
- Active Directory integration for user management
- SIEM integration for security event logging
- Configurable risk thresholds and response actions
- Session management and timeout handling
- Comprehensive logging and monitoring

## Requirements

- Python 3.8+
- FastAPI
- Uvicorn
- NumPy
- Pandas
- scikit-learn
- PyTorch
- python-jose
- pydantic
- python-multipart
- pytest
- pytest-asyncio
- black
- mypy
- python-dotenv
- joblib
- requests
- python-ldap

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/behavioral-biometrics.git
cd behavioral-biometrics
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the example environment file and configure your settings:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

The system can be configured through environment variables or by editing the `.env` file. Key configuration areas include:

- API and server settings
- Security settings (JWT, encryption)
- Active Directory integration
- SIEM integration
- Risk thresholds
- Behavioral analysis parameters
- Logging configuration
- Performance settings

See `.env.example` for all available configuration options.

## Usage

1. Start the server:
```bash
python run_server.py
```

2. The API will be available at `http://localhost:8000` with documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

3. Use the WebSocket endpoint for real-time event processing:
```python
import websockets
import json

async def connect():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Send keystroke event
        await websocket.send(json.dumps({
            "type": "keystroke",
            "key": "a",
            "timestamp": "2024-01-01T00:00:00Z",
            "duration": 0.1
        }))
        
        # Send mouse event
        await websocket.send(json.dumps({
            "type": "mouse",
            "event_type": "move",
            "x": 100,
            "y": 200,
            "timestamp": "2024-01-01T00:00:01Z"
        }))
        
        # Receive risk assessment
        response = await websocket.recv()
        print(json.loads(response))
```

## API Endpoints

### REST API

- `GET /api/v1/health`: Health check endpoint
- `POST /api/v1/keystroke`: Process keystroke event
- `POST /api/v1/mouse`: Process mouse event
- `GET /api/v1/session/{session_id}`: Get session status
- `POST /api/v1/session/{session_id}/end`: End session

### WebSocket API

- `ws://localhost:8000/ws`: WebSocket endpoint for real-time event processing

## Development

1. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Run tests:
```bash
pytest
```

3. Format code:
```bash
black .
```

4. Type checking:
```bash
mypy .
```

## Project Structure

```
behavioral-biometrics/
├── api/
│   └── main.py              # FastAPI application
├── core/
│   └── behavioral_analysis/
│       ├── context_processor.py
│       ├── keystroke_analyzer_v2.py
│       └── mouse_analyzer_v2.py
├── security/
│   └── risk_engine.py       # Risk assessment engine
├── config/
│   ├── settings.py          # Configuration settings
│   └── .env                 # Environment variables
├── models/                  # Trained models
├── logs/                    # Application logs
├── tests/                   # Test files
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
└── README.md               # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI for the web framework
- scikit-learn for machine learning capabilities
- PyTorch for deep learning support
- All other open-source libraries used in this project 