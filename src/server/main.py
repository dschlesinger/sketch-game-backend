import uvicorn

from server.settings import settings
from server.app import app

def main() -> None:
    
    uvicorn.run(app, port=8000)