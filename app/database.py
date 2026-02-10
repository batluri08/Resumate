"""
Database Configuration and Models for RestlessResume
Using SQLite with SQLAlchemy ORM
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()


# Database URL - PostgreSQL (read from environment variable)
# For Railway: DATABASE_URL is auto-injected by the PostgreSQL plugin
# For local: Use .env or .env.local files
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Only use localhost default for local development
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError(
            "DATABASE_URL environment variable is required for production deployment. "
            "Please add a PostgreSQL plugin to your Railway project."
        )
    DATABASE_URL = "postgresql+psycopg2://postgres:Bhumi@localhost:5432/restless_resume"

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Test connections before using them
    echo=os.getenv("ENVIRONMENT") != "production"  # SQL logging in dev only
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100))
    profile_picture = Column(Text, nullable=True)  # Base64 encoded profile picture
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    resumes = relationship("Resume", back_populates="owner", cascade="all, delete-orphan")
    optimization_history = relationship("OptimizationHistory", back_populates="user", cascade="all, delete-orphan")
    job_applications = relationship("JobApplication", back_populates="user", cascade="all, delete-orphan")
    cover_letters = relationship("CoverLetter", back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    """User's resume model - supports multiple resumes per user"""
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "Data Engineer Resume"
    file_name = Column(String(255), nullable=False)  # Original filename
    file_path = Column(String(500), nullable=False)  # Path to stored file
    file_ext = Column(String(10), nullable=False)  # .pdf or .docx
    content = Column(Text)  # Extracted text content
    preview_image = Column(Text)  # Base64 preview image
    is_default = Column(Boolean, default=False)  # User's default resume
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="resumes")
    applications = relationship("JobApplication", back_populates="resume")


class OptimizationHistory(Base):
    """History of resume optimizations"""
    __tablename__ = "optimization_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, nullable=True)  # Nullable - may not have saved resume (no FK constraint)
    job_title = Column(String(200))  # Extracted or user-provided job title
    company_name = Column(String(200))  # Extracted company name
    job_description = Column(Text, nullable=False)
    changes_made = Column(Text)  # JSON string of changes applied
    suggestions = Column(Text)  # JSON string of suggestions
    optimized_file_path = Column(String(500))  # Path to optimized file
    match_score = Column(Integer)  # 0-100 match percentage
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="optimization_history")


class UserSkills(Base):
    """User's master skills inventory"""
    __tablename__ = "user_skills"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skill_name = Column(String(100), nullable=False)
    category = Column(String(50))  # Languages, Frameworks, Tools, etc.
    proficiency = Column(String(20))  # Expert, Advanced, Intermediate, Beginner
    is_highlight = Column(Boolean, default=False)  # Never remove this skill
    created_at = Column(DateTime, default=datetime.utcnow)


class JobApplication(Base):
    """Track job applications"""
    __tablename__ = "job_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    
    # Job details
    job_title = Column(String(200), nullable=False)
    company_name = Column(String(200), nullable=False)
    job_url = Column(String(500))
    job_description = Column(Text)
    location = Column(String(200))
    salary_range = Column(String(100))
    
    # Application status
    status = Column(String(50), default="saved")  # saved, applied, interviewing, offered, rejected, withdrawn
    applied_date = Column(DateTime)
    
    # Notes and follow-up
    notes = Column(Text)
    follow_up_date = Column(DateTime)
    
    # Cover letter (if generated)
    cover_letter = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="job_applications")
    resume = relationship("Resume", back_populates="applications")


class CoverLetter(Base):
    """Saved cover letters"""
    __tablename__ = "cover_letters"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_application_id = Column(Integer, ForeignKey("job_applications.id"), nullable=True)
    
    title = Column(String(200))  # User-friendly name
    content = Column(Text, nullable=False)
    job_title = Column(String(200))
    company_name = Column(String(200))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="cover_letters")


# Dependency to get database session
def get_db():
    """Get database session - use as FastAPI dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")


if __name__ == "__main__":
    # Run directly to initialize database
    init_db()
