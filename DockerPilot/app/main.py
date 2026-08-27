"""
DockerPilot - Main Application
"""

import os
import yaml
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Load config
config_path = os.environ.get("CONFIG_PATH", "config.yaml")
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Setup logging
log_level = config.get('app', {}).get('log_level', 'INFO')
log_file = config.get('app', {}).get('log_file', '/config/pilot.log')

# Ensure config directory exists
config_dir = '/config'
Path(config_dir).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    logger.info("[DockerPilot] Starting up...")

    # Init database
    from app.db.database import db
    logger.info("[DockerPilot] Database initialized")

    yield

    logger.info("[DockerPilot] Shutting down...")


app = FastAPI(
    title="DockerPilot",
    description="Docker Visual Management Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
from app.api import docker, registries, images, projects, profiles, batches, containers, logs, settings

app.include_router(docker.router)
app.include_router(registries.router)
app.include_router(images.router)
app.include_router(projects.router)
app.include_router(profiles.router)
app.include_router(batches.router)
app.include_router(containers.router)
app.include_router(logs.router)
app.include_router(settings.router)

# Serve static frontend files
web_dir = Path(__file__).parent.parent / "web" / "dist"
if web_dir.exists():
    # SPA fallback - serve index.html for all non-API routes
    from starlette.responses import FileResponse

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Check if the requested file exists in web/dist
        file_path = web_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # Otherwise serve index.html for SPA routing
        return FileResponse(str(web_dir / "index.html"))
else:
    logger.warning(f"[DockerPilot] Frontend build not found at {web_dir}")


# Read port from environment variable, fall back to config file
app_port = int(os.environ.get("APP_PORT", config['app']['port']))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config['app']['host'],
        port=app_port,
        reload=config['app'].get('debug', False)
    )
