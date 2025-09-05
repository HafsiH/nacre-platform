from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routes.files import router as files_router
from .routes.conversion import router as conversion_router
from .routes.export import router as export_router
from .routes.health import router as health_router
from .routes.sophie import router as sophie_router
from .routes.co2_analyzer import router as co2_router
from .routes.carbon_visualization import router as carbon_viz_router
from .services.embeddings import build_or_load_index
from .services.sophie import initialize_sophie
from .utils.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger = setup_logging()
    logger.info("Starting NACRE Conversion API")
    
    # Build/load embeddings index in background best-effort
    try:
        build_or_load_index(force=False)
        logger.info("Embeddings index loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load embeddings index: {e}")
    try:
        initialize_sophie()
        logger.info("Sophie initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Sophie: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NACRE Conversion API")


app = FastAPI(title="NACRE Conversion API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files_router, prefix="/files", tags=["files"])
app.include_router(conversion_router, prefix="/conversions", tags=["conversions"])
app.include_router(export_router, prefix="/exports", tags=["exports"])
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(sophie_router, prefix="/sophie", tags=["sophie"])
app.include_router(co2_router, prefix="/co2", tags=["co2"])
app.include_router(carbon_viz_router, prefix="/api", tags=["carbon_visualization"])

@app.get("/")
def root():
    return {"ok": True, "service": "nacre-api"}


