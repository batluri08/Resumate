
"""
Resume Router - Handles resume upload, optimization, and download endpoints
"""

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
import uuid
import shutil
import json

from app.services.document_parser import DocumentParser
from app.services.ai_optimizer import AIOptimizer
from app.services.document_writer_v2 import DocumentWriter
from app.services.preview_generator import PreviewGenerator
from app.services.embedding_generator import generate_embedding
from app.services.vector_store import add_vector
from app.database import get_db, Resume, OptimizationHistory, User
from app.routers.auth import get_current_user, COOKIE_NAME
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/resume", tags=["resume"])
templates = Jinja2Templates(directory="app/templates")

# Store uploaded resumes temporarily (in production, use a database)
resume_storage = {}


@router.get("")
async def resume_page(request: Request, user: User = Depends(get_current_user)):
    """Render the main resume optimization page"""
    if not user:
        logger.warning("Resume page accessed without authentication")
        return RedirectResponse(url="/auth/login", status_code=302)
    logger.info(f"Resume page accessed by user: id={user.id}")
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@router.get("/profile")
async def profile_page(request: Request, user: User = Depends(get_current_user)):
    """Render the profile page"""
    if not user:
        logger.warning("Profile page accessed without authentication")
        return RedirectResponse(url="/auth/login", status_code=302)
    logger.info(f"Profile page accessed by user: id={user.id}")
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})


@router.post("/api/profile/picture")
async def upload_profile_picture(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and save user's profile picture to database"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        data = await request.json()
        picture_data = data.get("picture")
        
        if not picture_data:
            raise HTTPException(status_code=400, detail="No picture data provided")
        
        # Save to user's profile
        user.profile_picture = picture_data
        db.commit()
        
        logger.info(f"Profile picture updated for user: id={user.id}")
        return JSONResponse({
            "success": True,
            "message": "Profile picture saved",
            "picture": picture_data
        })
    except Exception as e:
        logger.error(f"Error uploading profile picture: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving picture: {str(e)}")


@router.get("/api/profile/picture")
async def get_profile_picture(
    request: Request,
    user: User = Depends(get_current_user)
):
    """Get user's profile picture from database"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return JSONResponse({
        "success": True,
        "picture": user.profile_picture
    })


@router.get("/history")
async def history_page(request: Request, user: User = Depends(get_current_user)):
    """Render the optimization history page"""
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse("history.html", {"request": request, "user": user})


@router.get("/api/history")
async def get_history(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's optimization history"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get history entries for this user
    history = db.query(OptimizationHistory).filter(
        OptimizationHistory.user_id == user.id
    ).order_by(OptimizationHistory.created_at.desc()).limit(50).all()
    
    return [{
        "id": h.id,
        "job_title": h.job_title,
        "company_name": h.company_name,
        "created_at": h.created_at.isoformat(),
        "match_score": h.match_score,
        "has_file": bool(h.optimized_file_path)
    } for h in history]


@router.get("/api/history/{history_id}")
async def get_history_detail(history_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get details of a specific optimization"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    entry = db.query(OptimizationHistory).filter(
        OptimizationHistory.id == history_id,
        OptimizationHistory.user_id == user.id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")
    
    return {
        "id": entry.id,
        "job_title": entry.job_title,
        "company_name": entry.company_name,
        "job_description": entry.job_description,
        "changes_made": json.loads(entry.changes_made) if entry.changes_made else [],
        "suggestions": json.loads(entry.suggestions) if entry.suggestions else [],
        "created_at": entry.created_at.isoformat(),
        "match_score": entry.match_score
    }


@router.get("/api/resumes")
async def get_user_resumes(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all resumes for the current user"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    resumes = db.query(Resume).filter(Resume.user_id == user.id).order_by(
        Resume.is_default.desc(),
        Resume.created_at.desc()
    ).all()
    
    return [{
        "id": r.id,
        "name": r.name,
        "file_name": r.file_name,
        "file_ext": r.file_ext,
        "is_default": r.is_default,
        "created_at": r.created_at.isoformat(),
        "preview_image": r.preview_image
    } for r in resumes]


@router.get("/api/default-resume")
async def get_default_resume(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get the user's default resume"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    resume = db.query(Resume).filter(
        Resume.user_id == user.id,
        Resume.is_default == True
    ).first()
    
    if not resume:
        return JSONResponse({"resume": None})
    
    # Load the resume into memory session
    session_id = str(uuid.uuid4())
    try:
        parser = DocumentParser()
        content, structure = parser.parse(resume.file_path)
        
        resume_storage[session_id] = {
            "resume_id": resume.id,
            "file_path": resume.file_path,
            "file_ext": resume.file_ext,
            "original_filename": resume.file_name,
            "content": content,
            "structure": structure,
            "preview_image": resume.preview_image
        }
        
        return JSONResponse({
            "resume": {
                "id": resume.id,
                "name": resume.name,
                "file_name": resume.file_name,
                "file_ext": resume.file_ext,
                "is_default": resume.is_default,
                "created_at": resume.created_at.isoformat(),
                "preview_image": resume.preview_image,
                "session_id": session_id,
                "content": content
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading resume: {str(e)}")


@router.post("/set-default-resume/{resume_id}")
async def set_default_resume(
    resume_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set a resume as the user's default"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Unset all other defaults
    db.query(Resume).filter(Resume.user_id == user.id).update({"is_default": False})
    
    # Set this one as default
    resume.is_default = True
    db.commit()
    
    return JSONResponse({"success": True, "message": "Resume set as default"})


@router.delete("/api/resumes/{resume_id}")
async def delete_resume(
    resume_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user's resume"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Delete the file if it exists
    if resume.file_path and os.path.exists(resume.file_path):
        os.remove(resume.file_path)

    # Delete vector from ChromaDB
    try:
        from app.services.vector_store import delete_vector
        delete_vector(str(resume.id))
    except Exception as e:
        print(f"[WARNING] Failed to delete vector for resume {resume.id}: {e}")
    
    was_default = resume.is_default
    
    # Delete from database
    db.delete(resume)
    db.commit()
    
    # If this was the default, set another one as default
    if was_default:
        other_resume = db.query(Resume).filter(Resume.user_id == user.id).first()
        if other_resume:
            other_resume.is_default = True
            db.commit()
    
    return JSONResponse({"success": True, "message": "Resume deleted"})


@router.put("/api/resumes/{resume_id}")
async def update_resume(
    resume_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a resume's name"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    body = await request.json()
    new_name = body.get("name", "").strip()
    
    if not new_name:
        raise HTTPException(status_code=400, detail="Name is required")
    
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    resume.name = new_name
    db.commit()
    
    return JSONResponse({"success": True, "message": "Resume updated", "name": new_name})


@router.post("/api/resumes/{resume_id}/select")
async def select_resume(
    resume_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Select a resume and load it into session for optimization"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Load the resume into memory session
    session_id = str(uuid.uuid4())
    try:
        # Try to parse from stored content first (works in cloud environments)
        # If content is stored, use it; otherwise try to read from file
        if resume.content:
            content = resume.content
            structure = {
                "type": resume.file_ext.lower().replace(".", ""),
                "paragraphs": [],
                "tables": [],
                "sections": []
            }
        else:
            # Fallback: parse from file path (for local development)
            parser = DocumentParser()
            content, structure = parser.parse(resume.file_path)
        
        resume_storage[session_id] = {
            "resume_id": resume.id,
            "file_path": resume.file_path,
            "file_ext": resume.file_ext,
            "original_filename": resume.file_name,
            "content": content,
            "structure": structure,
            "preview_image": resume.preview_image
        }
        
        return JSONResponse({
            "success": True,
            "session_id": session_id,
            "resume": {
                "id": resume.id,
                "name": resume.name,
                "file_name": resume.file_name,
                "file_ext": resume.file_ext,
                "is_default": resume.is_default,
                "preview_image": resume.preview_image
            }
        })
    except Exception as e:
        logger.error(f"Error loading resume {resume_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading resume: {str(e)}")


@router.get("/download/history/{history_id}")
async def download_history_resume(history_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Download optimized resume from history"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    entry = db.query(OptimizationHistory).filter(
        OptimizationHistory.id == history_id,
        OptimizationHistory.user_id == user.id
    ).first()
    
    if not entry or not entry.optimized_file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not os.path.exists(entry.optimized_file_path):
        raise HTTPException(status_code=404, detail="File no longer exists")
    
    filename = f"resume_optimized_{entry.job_title or 'job'}".replace(' ', '_')[:50]
    ext = os.path.splitext(entry.optimized_file_path)[1]
    
    return FileResponse(
        entry.optimized_file_path,
        media_type="application/octet-stream",
        filename=f"{filename}{ext}"
    )


@router.post("/analyze-keywords")
async def analyze_keywords(
    request: Request,
    session_id: str = Form(...),
    job_description: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze keywords from job description and match with resume"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if session_id not in resume_storage:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    resume_content = resume_storage[session_id]["content"].lower()
    
    import re
    
    # Clean job description
    job_text = job_description.lower()
    
    # Extract keywords - improved patterns with more comprehensive matching
    keywords = set()
    
    # Technical skills patterns - more comprehensive
    tech_patterns = [
        # Programming Languages
        r'\b(python|java|javascript|typescript|c\+\+|c#|ruby|golang|go|rust|scala|kotlin|swift|php|sql|r|matlab|perl|haskell|elixir|clojure)\b',
        # Frontend Frameworks
        r'\b(react|reactjs|react\.js|angular|angularjs|vue|vuejs|vue\.js|svelte|next\.?js|nuxt|gatsby|remix)\b',
        # Backend Frameworks  
        r'\b(node\.?js|express|express\.js|django|flask|fastapi|spring|spring boot|\.net|asp\.net|rails|ruby on rails|laravel|phoenix|gin|fiber)\b',
        # Cloud Platforms
        r'\b(aws|amazon web services|azure|microsoft azure|gcp|google cloud|google cloud platform|heroku|digitalocean|vercel|netlify)\b',
        # AWS Services
        r'\b(ec2|s3|lambda|rds|dynamodb|sqs|sns|cloudwatch|cloudformation|ecs|eks|fargate|sagemaker|redshift|athena|glue|kinesis|step functions)\b',
        # DevOps & Infrastructure
        r'\b(kubernetes|k8s|docker|terraform|ansible|puppet|chef|jenkins|circleci|travis|github actions|gitlab ci|argocd|helm|istio)\b',
        # Databases
        r'\b(postgresql|postgres|mysql|mariadb|mongodb|mongo|redis|elasticsearch|elastic|cassandra|dynamodb|sqlite|oracle|sql server|mssql|neo4j|cockroachdb)\b',
        # Data Warehouses
        r'\b(snowflake|bigquery|redshift|databricks|synapse|clickhouse|dremio|presto|trino)\b',
        # Data Engineering
        r'\b(spark|apache spark|pyspark|hadoop|hive|airflow|apache airflow|kafka|apache kafka|flink|beam|dbt|fivetran|airbyte|nifi|prefect|dagster)\b',
        # ML/AI
        r'\b(machine learning|deep learning|nlp|natural language processing|computer vision|neural network|neural networks|llm|large language model|generative ai|gen ai)\b',
        # ML Frameworks
        r'\b(tensorflow|pytorch|keras|scikit-learn|sklearn|xgboost|lightgbm|hugging face|huggingface|transformers|langchain|openai|mlflow|kubeflow|ray)\b',
        # Data Science
        r'\b(pandas|numpy|scipy|matplotlib|seaborn|plotly|jupyter|anaconda|conda)\b',
        # Monitoring & Observability
        r'\b(prometheus|grafana|datadog|splunk|new relic|dynatrace|elastic|elk|kibana|logstash|jaeger|zipkin|opentelemetry)\b',
        # Version Control & Collaboration
        r'\b(git|github|gitlab|bitbucket|svn|mercurial)\b',
        # CI/CD & Methodologies
        r'\b(ci/?cd|continuous integration|continuous delivery|continuous deployment|agile|scrum|kanban|devops|devsecops|sre|site reliability)\b',
        # API & Architecture
        r'\b(rest|restful|graphql|grpc|soap|microservices|micro-services|serverless|event-driven|event driven|api gateway|swagger|openapi)\b',
        # Testing
        r'\b(unit testing|integration testing|e2e|end-to-end|pytest|jest|mocha|selenium|cypress|playwright|testng|junit)\b',
        # Security
        r'\b(oauth|jwt|saml|sso|single sign-on|encryption|ssl|tls|https|iam|rbac|security|authentication|authorization)\b',
        # Messaging & Queues
        r'\b(rabbitmq|activemq|celery|sidekiq|bull|sqs|pub/?sub|pubsub)\b',
        # Other Tools
        r'\b(jira|confluence|slack|notion|figma|linear|asana|trello)\b',
        # General Tech Terms
        r'\b(etl|elt|data pipeline|data pipelines|data warehouse|data lake|data lakehouse|data modeling|data governance|data quality)\b',
    ]
    
    for pattern in tech_patterns:
        matches = re.findall(pattern, job_text)
        keywords.update(matches)
    
    # Also look for capitalized technical terms that might be product names
    cap_terms = re.findall(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b', job_description)
    for term in cap_terms:
        term_lower = term.lower()
        # Filter out common non-technical capitalized words
        skip_words = {'the', 'and', 'for', 'with', 'this', 'that', 'will', 'you', 'your', 'our', 'are', 'have', 'has', 'from', 'about', 'what', 'when', 'where', 'who', 'how', 'why', 'all', 'can', 'could', 'would', 'should', 'may', 'might', 'must', 'need', 'want', 'like', 'just', 'also', 'other', 'any', 'each', 'every', 'both', 'few', 'more', 'most', 'some', 'such', 'than', 'too', 'very', 'own', 'same', 'able', 'about', 'above', 'across', 'after', 'against', 'along', 'among', 'around', 'before', 'behind', 'below', 'between', 'beyond', 'during', 'inside', 'into', 'near', 'over', 'through', 'under', 'upon', 'within', 'without', 'experience', 'years', 'year', 'work', 'working', 'team', 'teams', 'role', 'position', 'job', 'company', 'engineering', 'engineer', 'developer', 'senior', 'junior', 'lead', 'manager', 'director', 'staff', 'principal', 'responsibilities', 'requirements', 'qualifications', 'skills', 'strong', 'excellent', 'good', 'knowledge', 'understanding', 'ability', 'required', 'preferred', 'plus', 'bonus', 'including', 'such', 'well', 'high', 'highly', 'looking', 'seeking', 'join', 'opportunity', 'exciting', 'dynamic', 'fast-paced', 'collaborative', 'environment'}
        if term_lower not in skip_words and len(term) > 2:
            keywords.add(term_lower)
    
    # Categorize keywords - improved matching
    found_keywords = []
    missing_keywords = []
    
    for kw in keywords:
        kw_clean = kw.strip()
        if kw_clean and len(kw_clean) > 1:
            # More thorough checking - handle variations
            kw_variations = [
                kw_clean,
                kw_clean.replace('.', ''),
                kw_clean.replace('.', ' '),
                kw_clean.replace('-', ''),
                kw_clean.replace('-', ' '),
                kw_clean.replace(' ', ''),
                kw_clean.replace(' ', '-'),
            ]
            
            # Also handle common abbreviations
            if kw_clean == 'k8s':
                kw_variations.append('kubernetes')
            elif kw_clean == 'kubernetes':
                kw_variations.append('k8s')
            elif kw_clean == 'js':
                kw_variations.extend(['javascript', 'node.js', 'nodejs'])
            elif kw_clean == 'ts':
                kw_variations.append('typescript')
            elif kw_clean == 'postgres':
                kw_variations.append('postgresql')
            elif kw_clean == 'mongo':
                kw_variations.append('mongodb')
            elif kw_clean == 'ml':
                kw_variations.append('machine learning')
            elif kw_clean == 'ai':
                kw_variations.append('artificial intelligence')
            
            found = any(var in resume_content for var in kw_variations)
            
            if found:
                found_keywords.append(kw_clean)
            else:
                missing_keywords.append(kw_clean)
    
    # Calculate match score
    total = len(found_keywords) + len(missing_keywords)
    match_score = int((len(found_keywords) / total * 100)) if total > 0 else 0
    
    return {
        "found_keywords": sorted(list(set(found_keywords))),
        "missing_keywords": sorted(list(set(missing_keywords))),
        "match_score": match_score,
        "total_keywords": total
    }


@router.get("/verify/{session_id}")
async def verify_session(session_id: str):
    """Check if a session ID is valid (resume exists on server)"""
    return {"valid": session_id in resume_storage}


@router.post("/upload")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    resume_name: str = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a resume file (PDF or DOCX) - saves to database and associates with user
    """
    logger.info(f"Resume upload initiated: user_id={user.id}, filename={file.filename}")
    
    # Check authentication
    if not user:
        logger.warning("Resume upload attempted without authentication")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate file type
    allowed_extensions = [".pdf", ".docx"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        logger.warning(f"Resume upload failed: invalid file type={file_ext}, user_id={user.id}")
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Please upload a PDF or DOCX file."
        )
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Save file to uploads/resumes directory
    os.makedirs("uploads/resumes", exist_ok=True)
    upload_path = f"uploads/resumes/{user.id}_{session_id}{file_ext}"
    
    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.debug(f"Resume file saved: path={upload_path}")
        
        # Parse the document to extract content
        parser = DocumentParser()
        content, structure = parser.parse(upload_path)
        logger.debug(f"Resume content parsed: user_id={user.id}, content_length={len(content)}")
        
        # Generate preview image
        preview_gen = PreviewGenerator()
        preview_image = preview_gen.generate_preview(upload_path)
        logger.debug(f"Resume preview generated: user_id={user.id}")
        
        # Check if user has any resumes - if not, make this the default
        existing_resumes = db.query(Resume).filter(Resume.user_id == user.id).first()
        is_default = existing_resumes is None
        
        # Use provided name or default to filename
        display_name = resume_name.strip() if resume_name else file.filename
        
        # Save to database
        db_resume = Resume(
            user_id=user.id,
            name=display_name,
            file_name=file.filename,
            file_path=upload_path,
            file_ext=file_ext,
            content=content,
            preview_image=preview_image,
            is_default=is_default
        )
        db.add(db_resume)
        db.commit()
        db.refresh(db_resume)
        logger.info(f"Resume saved to database: id={db_resume.id}, user_id={user.id}")
        
        # Generate and store embedding in ChromaDB
        embedding = generate_embedding(content)
        add_vector(str(db_resume.id), embedding, metadata={
            "user_id": user.id,
            "resume_name": display_name,
            "file_name": file.filename
        })
        logger.debug(f"Resume embedding stored in ChromaDB: resume_id={db_resume.id}")

        # Also store in memory session for current work
        resume_storage[session_id] = {
            "resume_id": db_resume.id,
            "file_path": upload_path,
            "file_ext": file_ext,
            "original_filename": file.filename,
            "content": content,
            "structure": structure,
            "preview_image": preview_image
        }
        logger.info(f"Resume upload successful: id={db_resume.id}, user_id={user.id}, session_id={session_id}")

        return JSONResponse({
            "success": True,
            "session_id": session_id,
            "resume_id": db_resume.id,
            "filename": file.filename,
            "file_ext": file_ext,
            "content_preview": content,
            "preview_image": preview_image,
            "is_default": is_default
        })
        
    except Exception as e:
        logger.error(f"Resume upload failed: user_id={user.id}, filename={file.filename}, error={str(e)}")
        # Clean up on error
        if os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/optimize")
async def optimize_resume(
    request: Request,
    session_id: str = Form(...),
    job_description: str = Form(...),
    job_title: str = Form(""),
    company_name: str = Form(""),
    # Profile preferences (optional)
    must_have_skills: str = Form(""),
    secondary_skills: str = Form(""),
    target_role: str = Form(""),
    pref_conservative: bool = Form(True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Optimize the uploaded resume for a specific job description
    """
    logger.info(f"Resume optimization started: session_id={session_id}, user_id={user.id}")
    
    # Get current user
    if not user:
        logger.warning("Resume optimization attempted without authentication")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    logger.debug(f"Optimize called with session_id: {session_id}")
    logger.debug(f"Available sessions: {list(resume_storage.keys())}")
    
    # Check if session exists
    if session_id not in resume_storage:
        logger.warning(f"Resume optimization failed: session not found, session_id={session_id}, user_id={user.id}")
        raise HTTPException(
            status_code=404, 
            detail=f"Resume not found (session: {session_id}). Please upload your resume first."
        )
    
    resume_data = resume_storage[session_id]
    logger.debug(f"Resume found in storage: size={len(resume_data.get('content', ''))}")
    
    # Build profile context for AI
    profile_context = ""
    if must_have_skills:
        profile_context += f"\nMUST KEEP SKILLS (never remove): {must_have_skills}"
    if secondary_skills:
        profile_context += f"\nSECONDARY SKILLS (can swap if needed): {secondary_skills}"
    if target_role:
        profile_context += f"\nTARGET ROLE: {target_role}"
    if pref_conservative:
        profile_context += "\nPREFERENCE: Make minimal, conservative changes only."
    
    try:
        logger.debug(f"Starting AI optimization with profile context: {profile_context[:100]}")
        # Use AI to optimize the resume
        optimizer = AIOptimizer()
        # changes is now a list of {find, replace, reason} dicts
        changes, suggestions = await optimizer.optimize(
            resume_content=resume_data["content"],
            job_description=job_description,
            profile_context=profile_context
        )
        
        logger.info(f"AI optimization complete: changes_count={len(changes)}, suggestions_count={len(suggestions)}")
        logger.debug(f"Original content length: {len(resume_data['content'])}")
        logger.debug(f"Number of changes from AI: {len(changes)}")
        
        # Reconstruct the original file from database content (for Railway compatibility with ephemeral filesystem)
        import tempfile
        import shutil
        temp_dir = tempfile.mkdtemp()
        actual_output_path = None
        try:
            temp_original_path = os.path.join(temp_dir, f"resume_original{resume_data['file_ext']}")
            
            # Write content to temporary file for processing
            if resume_data['file_ext'] == '.pdf':
                # For PDF, we need to write bytes
                import base64
                if isinstance(resume_data['content'], str) and resume_data['content'].startswith('data:'):
                    # If it's base64 encoded
                    base64_data = resume_data['content'].split(',')[1]
                    with open(temp_original_path, 'wb') as f:
                        f.write(base64.b64decode(base64_data))
                else:
                    # Assume it's plain text, write as is
                    with open(temp_original_path, 'w', encoding='utf-8') as f:
                        f.write(resume_data['content'])
            else:
                # For DOCX, write the content
                with open(temp_original_path, 'w', encoding='utf-8') as f:
                    f.write(resume_data['content'])
            
            logger.debug(f"Reconstructed resume file: {temp_original_path}")
            
            # Write the optimized content back to a new file
            writer = DocumentWriter()
            output_path = f"uploads/{session_id}_optimized{resume_data['file_ext']}"
            
            actual_output_path = writer.write(
                original_path=temp_original_path,
                output_path=output_path,
                changes=changes,
                file_type=resume_data['file_ext']
            )
            logger.debug(f"Optimized document written: path={actual_output_path}")
        except Exception as file_err:
            logger.error(f"Error reconstructing/writing resume file: {str(file_err)}")
            # Continue without file output (still have the text content)
            actual_output_path = None
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Build optimized content for preview by applying changes to text
        optimized_content = resume_data["content"]
        for change in changes:
            if change.get("find") and change.get("replace"):
                optimized_content = optimized_content.replace(
                    change["find"], 
                    change["replace"]
                )
        
        # Generate diff HTML to show changes
        preview_gen = PreviewGenerator()
        diff_html = preview_gen.generate_diff_html(
            resume_data["content"], 
            optimized_content
        )
        logger.debug("Diff HTML generated")
        
        # Generate preview of optimized document
        optimized_preview_image = None
        if os.path.exists(actual_output_path):
            try:
                optimized_preview_image = preview_gen.generate_preview(actual_output_path)
                logger.debug("Optimized preview image generated")
            except Exception as preview_err:
                logger.warning(f"Preview generation failed: {str(preview_err)}")
                pass  # Preview generation is optional
        
        # Update storage
        resume_storage[session_id]["optimized_path"] = actual_output_path
        resume_storage[session_id]["optimized_content"] = optimized_content
        
        # Save optimization to database
        try:
            # Extract job title and company from job description if not provided
            extracted_title = job_title
            extracted_company = company_name
            
            # Try to extract company and title from job description
            import re
            jd_lower = job_description.lower()
            lines = job_description.strip().split('\n')
            
            # Common patterns for company names
            if not extracted_company:
                # Look for "at Company" or "Company is hiring" patterns
                company_patterns = [
                    r'(?:at|@)\s+([A-Z][A-Za-z0-9\s&.,]+?)(?:\s+is|\s+we|\.|,|\n)',
                    r'([A-Z][A-Za-z0-9\s&]+?)\s+is\s+(?:hiring|looking|seeking)',
                    r'(?:company|employer)[:\s]+([A-Za-z0-9\s&.,]+?)(?:\n|,|\.|$)',
                    r'(?:about|join)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\n|,|\.|:)',
                ]
                for pattern in company_patterns:
                    match = re.search(pattern, job_description, re.IGNORECASE)
                    if match:
                        extracted_company = match.group(1).strip()[:100]
                        break
                # If still no company, check first few lines for a capitalized name
                if not extracted_company and lines:
                    for line in lines[:5]:
                        line = line.strip()
                        # Skip lines that look like job titles
                        if line and not any(kw in line.lower() for kw in ['engineer', 'developer', 'manager', 'analyst', 'designer', 'specialist']):
                            if len(line) < 50 and line[0].isupper():
                                extracted_company = line[:100]
                                break
            
            if not extracted_title:
                # Try to extract from job description using common job title keywords
                job_keywords = ['engineer', 'developer', 'manager', 'analyst', 'designer', 'specialist', 'consultant', 'lead', 'director', 'architect', 'scientist', 'administrator', 'officer', 'coordinator', 'strategist', 'technician', 'intern', 'executive', 'assistant', 'associate', 'product', 'project', 'qa', 'tester', 'writer', 'editor', 'sales', 'marketing', 'account', 'business', 'operations', 'support', 'trainer', 'coach', 'teacher', 'professor', 'researcher']
                found_title = None
                for line in lines:
                    line_lower = line.lower()
                    if any(kw in line_lower for kw in job_keywords):
                        found_title = line.strip()[:200]
                        break
                if found_title:
                    extracted_title = found_title
                elif lines:
                    extracted_title = lines[0][:200]  # Fallback: first line, max 200 chars
            
            history_entry = OptimizationHistory(
                user_id=user.id,
                resume_id=None,  # We'll link this when we have proper resume storage
                job_title=extracted_title,
                company_name=extracted_company,
                job_description=job_description,
                changes_made=json.dumps(changes),
                suggestions=json.dumps(suggestions),
                optimized_file_path=actual_output_path,
                match_score=None  # Will implement later
            )
            db.add(history_entry)
            db.commit()
            db.refresh(history_entry)
            
            history_id = history_entry.id
            logger.info(f"Optimization history saved: id={history_id}, user_id={user.id}")
        except Exception as db_error:
            logger.error(f"Failed to save optimization to database: {str(db_error)}")
            history_id = None
        
        logger.info(f"Resume optimization completed successfully: session_id={session_id}, user_id={user.id}")
        return JSONResponse({
            "success": True,
            "message": "Resume optimized successfully!",
            "history_id": history_id,
            "suggestions": suggestions,
            "original_content": resume_data["content"],
            "optimized_content": optimized_content,
            "diff_html": diff_html,
            "original_preview": resume_data.get("preview_image"),
            "optimized_preview": optimized_preview_image
        })
        
    except Exception as e:
        logger.error(f"Resume optimization failed: session_id={session_id}, user_id={user.id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Error optimizing resume: {str(e)}")


@router.get("/download/{session_id}")
async def download_resume(session_id: str):
    """
    Download the optimized resume
    """
    logger.info(f"Resume download requested: session_id={session_id}")
    
    if session_id not in resume_storage:
        logger.warning(f"Download failed: resume not found, session_id={session_id}")
        raise HTTPException(status_code=404, detail="Resume not found.")
    
    resume_data = resume_storage[session_id]
    
    if "optimized_path" not in resume_data:
        logger.warning(f"Download failed: resume not optimized, session_id={session_id}")
        raise HTTPException(
            status_code=400, 
            detail="Resume has not been optimized yet."
        )
    
    optimized_path = resume_data["optimized_path"]
    
    if not os.path.exists(optimized_path):
        logger.error(f"Download failed: optimized file not found, path={optimized_path}")
        raise HTTPException(status_code=404, detail="Optimized file not found.")
    
    original_name = os.path.splitext(resume_data["original_filename"])[0]
    download_name = f"{original_name}_optimized.docx"
    
    logger.info(f"Resume download successful: session_id={session_id}, filename={download_name}")
    
    return FileResponse(
        path=optimized_path,
        filename=download_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@router.delete("/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """
    Clean up uploaded files and session data
    """
    logger.info(f"Session cleanup requested: session_id={session_id}")
    
    if session_id in resume_storage:
        resume_data = resume_storage[session_id]
        
        # Remove files
        for key in ["file_path", "optimized_path"]:
            if key in resume_data and os.path.exists(resume_data[key]):
                try:
                    os.remove(resume_data[key])
                    logger.debug(f"File deleted: path={resume_data[key]}")
                except Exception as e:
                    logger.warning(f"Failed to delete file: path={resume_data[key]}, error={str(e)}")
        
        # Remove from storage
        del resume_storage[session_id]
        logger.info(f"Session cleanup complete: session_id={session_id}")
    else:
        logger.warning(f"Cleanup: session not found, session_id={session_id}")
    
    return JSONResponse({"success": True, "message": "Session cleaned up."})
