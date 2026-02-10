"""
Multiple Resume Profiles Router
Handles CRUD operations for multiple resume versions
"""

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
import os
import uuid
import shutil

from app.database import get_db, Resume, User
from app.routers.auth import get_current_user
from app.services.document_parser import DocumentParser
from app.services.preview_generator import PreviewGenerator

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

# Storage directory for resume files
RESUME_STORAGE_DIR = "uploads/resumes"
os.makedirs(RESUME_STORAGE_DIR, exist_ok=True)


@router.get("")
async def list_resumes(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get all resumes for the current user"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    resumes = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.created_at.desc()).all()
    
    return {
        "resumes": [
            {
                "id": r.id,
                "name": r.name,
                "file_name": r.file_name,
                "file_ext": r.file_ext,
                "is_default": r.is_default,
                "preview_image": r.preview_image,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat() if r.updated_at else None
            }
            for r in resumes
        ]
    }


@router.post("")
async def create_resume(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    is_default: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Upload a new resume profile"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate file type
    file_ext = '.' + file.filename.split('.')[-1].lower()
    if file_ext not in ['.pdf', '.docx']:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())
    stored_filename = f"{user.id}_{unique_id}{file_ext}"
    file_path = os.path.join(RESUME_STORAGE_DIR, stored_filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Extract content
    try:
        content = DocumentParser.extract_text(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {str(e)}")
    
    # Generate preview
    try:
        preview_image = PreviewGenerator.generate_preview(file_path)
    except:
        preview_image = None
    
    # If setting as default, unset other defaults
    if is_default:
        db.query(Resume).filter(Resume.user_id == user.id, Resume.is_default == True).update({"is_default": False})
    
    # If this is the first resume, make it default
    existing_count = db.query(Resume).filter(Resume.user_id == user.id).count()
    if existing_count == 0:
        is_default = True
    
    # Create resume record
    resume = Resume(
        user_id=user.id,
        name=name,
        file_name=file.filename,
        file_path=file_path,
        file_ext=file_ext,
        content=content,
        preview_image=preview_image,
        is_default=is_default
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    
    return {
        "id": resume.id,
        "name": resume.name,
        "file_name": resume.file_name,
        "file_ext": resume.file_ext,
        "is_default": resume.is_default,
        "preview_image": resume.preview_image,
        "message": "Resume uploaded successfully!"
    }


@router.get("/{resume_id}")
async def get_resume(
    resume_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get a specific resume"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return {
        "id": resume.id,
        "name": resume.name,
        "file_name": resume.file_name,
        "file_ext": resume.file_ext,
        "content": resume.content,
        "is_default": resume.is_default,
        "preview_image": resume.preview_image,
        "created_at": resume.created_at.isoformat()
    }


@router.put("/{resume_id}")
async def update_resume(
    resume_id: int,
    request: Request,
    name: str = Form(None),
    is_default: bool = Form(None),
    db: Session = Depends(get_db)
):
    """Update resume metadata"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if name is not None:
        resume.name = name
    
    if is_default is not None and is_default:
        # Unset other defaults
        db.query(Resume).filter(Resume.user_id == user.id, Resume.is_default == True).update({"is_default": False})
        resume.is_default = True
    
    db.commit()
    
    return {"message": "Resume updated successfully"}


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a resume"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Delete file
    if os.path.exists(resume.file_path):
        os.remove(resume.file_path)
    
    # Delete record
    db.delete(resume)
    db.commit()
    
    return {"message": "Resume deleted successfully"}


@router.get("/{resume_id}/download")
async def download_resume(
    resume_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Download the original resume file"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="Resume file not found")
    
    return FileResponse(
        resume.file_path,
        filename=resume.file_name,
        media_type="application/octet-stream"
    )


@router.post("/{resume_id}/set-default")
async def set_default_resume(
    resume_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Set a resume as the default"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Unset other defaults
    db.query(Resume).filter(Resume.user_id == user.id, Resume.is_default == True).update({"is_default": False})
    
    # Set this as default
    resume.is_default = True
    db.commit()
    
    return {"message": "Default resume updated"}
