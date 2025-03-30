import os
import sys
import uvicorn
from config.settings import settings

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import the application
from api.main import app

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.SERVER.HOST,
        port=settings.SERVER.PORT,
        reload=settings.SERVER.RELOAD,
        workers=settings.SERVER.WORKERS,
        log_level=settings.SERVER.LOG_LEVEL
    ) 