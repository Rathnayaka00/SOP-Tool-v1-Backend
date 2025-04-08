from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from app.routes.sop_routes import router as sop_router
import time
import logging
from typing import Callable
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SOP Generator API",
    description="API for generating and managing Standard Operating Procedures",
    version="1.4.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Error handling middleware
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next: Callable):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.4.0"
    }

# Include routers
app.include_router(sop_router, prefix="/api")

# Root endpoint
@app.get("/")
async def home():
    return {
        "message": "Welcome to the SOP Generator Tool",
        "version": "1.4.0",
        "docs_url": "/api/docs"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up SOP Generator API")
    # Add any startup tasks here (e.g., database connection)

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down SOP Generator API")
    # Add any cleanup tasks here
