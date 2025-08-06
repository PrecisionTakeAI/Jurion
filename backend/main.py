"""
FastAPI application for LegalAI Hub Backend
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import os
import logging

from .database import create_tables, check_database_health
from .auth.routes import router as auth_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LegalAI Hub API",
    description="Multi-tenant legal practice management platform with AI integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(auth_router)

# Import and include case management routers
from .api.case_routes import router as case_router
from .api.document_routes import router as document_router

app.include_router(case_router)
app.include_router(document_router)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting LegalAI Hub API...")
    
    # Create database tables if they don't exist
    try:
        create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    logger.info("LegalAI Hub API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down LegalAI Hub API...")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "LegalAI Hub API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_healthy = check_database_health()
    
    status = "healthy" if db_healthy else "unhealthy"
    status_code = 200 if db_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "database": "connected" if db_healthy else "disconnected",
            "timestamp": "2025-01-28T12:00:00Z"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT", "production") == "development"
    )