"""
Cover Letter Router
Generate and manage cover letters
"""

from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db, CoverLetter, JobApplication, Resume, User
from app.routers.auth import get_current_user
from app.services.cover_letter_generator import CoverLetterGenerator

router = APIRouter(prefix="/api/cover-letters", tags=["cover-letters"])


def check_auth(request: Request, db: Session) -> User:
    """Check if user is authenticated"""
    return get_current_user(request, db)


@router.post("/generate")
async def generate_cover_letter(
    request: Request,
    resume_id: int = Form(...),
    job_title: str = Form(...),
    company_name: str = Form(...),
    job_description: str = Form(...),
    tone: str = Form("professional"),
    additional_notes: str = Form(""),
    job_application_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """Generate a new cover letter"""
    user = check_auth(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get the resume
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Generate cover letter
    result = CoverLetterGenerator.generate(
        resume_content=resume.content,
        job_description=job_description,
        job_title=job_title,
        company_name=company_name,
        user_name=user.name or "",
        tone=tone,
        additional_notes=additional_notes
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))
    
    # If linked to a job application, save it there
    if job_application_id:
        app = db.query(JobApplication).filter(
            JobApplication.id == job_application_id,
            JobApplication.user_id == user.id
        ).first()
        if app:
            app.cover_letter = result["cover_letter"]
            db.commit()
    
    return {
        "cover_letter": result["cover_letter"],
        "key_points": result.get("key_points", []),
        "opening_hook": result.get("opening_hook", "")
    }


@router.post("/refine")
async def refine_cover_letter(
    request: Request,
    cover_letter: str = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db)
):
    """Refine an existing cover letter"""
    user = check_auth(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = CoverLetterGenerator.refine(
        original_letter=cover_letter,
        feedback=feedback
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Refinement failed"))
    
    return {
        "cover_letter": result["cover_letter"]
    }


@router.post("/save")
async def save_cover_letter(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    job_title: str = Form(""),
    company_name: str = Form(""),
    job_application_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """Save a cover letter to the library"""
    user = check_auth(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    cover_letter = CoverLetter(
        user_id=user.id,
        job_application_id=job_application_id,
        title=title,
        content=content,
        job_title=job_title,
        company_name=company_name
    )
    
    db.add(cover_letter)
    db.commit()
    db.refresh(cover_letter)
    
    return {
        "id": cover_letter.id,
        "message": "Cover letter saved successfully!"
    }


@router.get("/list")
async def list_cover_letters(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get all saved cover letters"""
    user = check_auth(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    letters = db.query(CoverLetter).filter(
        CoverLetter.user_id == user.id
    ).order_by(CoverLetter.created_at.desc()).all()
    
    return {
        "cover_letters": [
            {
                "id": cl.id,
                "title": cl.title,
                "job_title": cl.job_title,
                "company_name": cl.company_name,
                "content": cl.content[:200] + "..." if len(cl.content) > 200 else cl.content,
                "created_at": cl.created_at.isoformat()
            }
            for cl in letters
        ]
    }


@router.get("/{letter_id}")
async def get_cover_letter(
    letter_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get a specific cover letter"""
    user = check_auth(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    letter = db.query(CoverLetter).filter(
        CoverLetter.id == letter_id,
        CoverLetter.user_id == user.id
    ).first()
    
    if not letter:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    return {
        "id": letter.id,
        "title": letter.title,
        "content": letter.content,
        "job_title": letter.job_title,
        "company_name": letter.company_name,
        "created_at": letter.created_at.isoformat()
    }


@router.delete("/{letter_id}")
async def delete_cover_letter(
    letter_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a cover letter"""
    user = check_auth(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    letter = db.query(CoverLetter).filter(
        CoverLetter.id == letter_id,
        CoverLetter.user_id == user.id
    ).first()
    
    if not letter:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    db.delete(letter)
    db.commit()
    
    return {"message": "Cover letter deleted successfully"}
