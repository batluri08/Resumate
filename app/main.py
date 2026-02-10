"""
RestlessResume - AI-Powered Resume Optimizer
FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os
import secrets

from app.routers import resume, auth, resumes, cover_letters, analytics
from app.routers import oauth
from app.database import init_db
from app.logging_config import get_logger
from app.exceptions import RestlessResumeException

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="RestlessResume",
    description="AI-Powered Resume Optimizer - Tailor your resume to any job description",
    version="3.0.0"
)

# Session secret key - use environment variable or generate one
SESSION_SECRET = os.getenv("SESSION_SECRET_KEY", secrets.token_urlsafe(32))

# Add SessionMiddleware (required for OAuth) - MUST be first middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(resumes.router)
app.include_router(cover_letters.router)
app.include_router(analytics.router)
app.include_router(oauth.router)

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/resumes", exist_ok=True)


# Exception handlers
@app.exception_handler(RestlessResumeException)
async def restless_exception_handler(request: Request, exc: RestlessResumeException):
    """Handle custom RestlessResume exceptions"""
    logger.error(f"RestlessResume error: {exc.message}", exc_info=exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.exception(f"Unexpected error: {str(exc)}")
    # Don't expose internal error details to client
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    try:
        init_db()
        logger.info("✅ Database initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 RestlessResume shutting down")


@app.get("/")
async def root():
    """Redirect to the main page"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/resume")
