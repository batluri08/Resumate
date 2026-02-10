"""
Analytics Router
Dashboard statistics and insights based on optimization history
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from collections import Counter
import json
import re

from app.database import get_db, User, Resume, OptimizationHistory
from app.routers.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])
templates = Jinja2Templates(directory="app/templates")


def check_auth(request: Request, db: Session) -> User:
    """Check if user is authenticated"""
    return get_current_user(request, db)


@router.get("")
async def analytics_page(request: Request, db: Session = Depends(get_db)):
    """Render the analytics dashboard page"""
    user = check_auth(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse("analytics.html", {"request": request, "user": user})


@router.get("/api/dashboard")
async def get_dashboard_data(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard analytics based on optimization history"""
    user = check_auth(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Total optimizations
    total_optimizations = db.query(OptimizationHistory).filter(
        OptimizationHistory.user_id == user.id
    ).count()
    
    # Average match score (if available)
    avg_score = db.query(func.avg(OptimizationHistory.match_score)).filter(
        OptimizationHistory.user_id == user.id,
        OptimizationHistory.match_score != None
    ).scalar() or 0
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_optimizations = db.query(OptimizationHistory).filter(
        OptimizationHistory.user_id == user.id,
        OptimizationHistory.created_at >= thirty_days_ago
    ).count()
    
    # Optimizations over time (last 7 days)
    optimization_trend = []
    for i in range(7):
        date = datetime.utcnow() - timedelta(days=6-i)
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        count = db.query(OptimizationHistory).filter(
            OptimizationHistory.user_id == user.id,
            OptimizationHistory.created_at >= start,
            OptimizationHistory.created_at < end
        ).count()
        
        optimization_trend.append({
            "date": start.strftime("%b %d"),
            "count": count
        })
    
    # Get all optimizations for keyword analysis
    optimizations = db.query(OptimizationHistory).filter(
        OptimizationHistory.user_id == user.id
    ).order_by(OptimizationHistory.created_at.desc()).all()
    
    # Extract companies from optimizations
    companies = []
    for opt in optimizations:
        if opt.company_name:
            companies.append(opt.company_name)
    
    company_counts = Counter(companies).most_common(5)
    top_companies = [{"name": c[0], "count": c[1]} for c in company_counts]
    
    # Extract job titles
    job_titles = []
    for opt in optimizations:
        if opt.job_title:
            job_titles.append(opt.job_title[:50])  # Truncate long titles
    
    title_counts = Counter(job_titles).most_common(5)
    top_roles = [{"title": t[0], "count": t[1]} for t in title_counts]
    
    # Analyze suggestions for common missing skills
    all_suggestions = []
    for opt in optimizations:
        if opt.suggestions:
            try:
                suggestions = json.loads(opt.suggestions) if isinstance(opt.suggestions, str) else opt.suggestions
                if isinstance(suggestions, list):
                    all_suggestions.extend(suggestions)
            except:
                pass
    
    return {
        "overview": {
            "total_optimizations": total_optimizations,
            "recent_30_days": recent_optimizations,
            "avg_match_score": round(avg_score, 1)
        },
        "optimization_trend": optimization_trend,
        "top_companies": top_companies,
        "top_roles": top_roles,
        "total_suggestions": len(all_suggestions)
    }


@router.get("/api/keyword-analysis")
async def get_keyword_analysis(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get detailed keyword analysis from optimization history"""
    user = check_auth(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    optimizations = db.query(OptimizationHistory).filter(
        OptimizationHistory.user_id == user.id
    ).order_by(OptimizationHistory.created_at.desc()).limit(50).all()
    
    # Analyze job descriptions for common requirements
    all_text = " ".join([opt.job_description for opt in optimizations if opt.job_description])
    
    # Common tech keywords to look for
    tech_patterns = {
        "languages": r'\b(python|java|javascript|typescript|c\+\+|c#|ruby|go|rust|scala|kotlin|swift|php|sql|r)\b',
        "frameworks": r'\b(react|angular|vue|node\.?js|express|django|flask|spring|\.net|rails|laravel|fastapi|nextjs)\b',
        "cloud": r'\b(aws|azure|gcp|google cloud|kubernetes|docker|terraform|ansible|cloudformation)\b',
        "databases": r'\b(postgresql|mysql|mongodb|redis|elasticsearch|dynamodb|cassandra|oracle|sqlite)\b',
        "tools": r'\b(git|jenkins|github|gitlab|jira|confluence|slack|docker|kubernetes)\b'
    }
    
    keyword_analysis = {}
    for category, pattern in tech_patterns.items():
        matches = re.findall(pattern, all_text.lower())
        if matches:
            counts = Counter(matches)
            keyword_analysis[category] = [
                {"keyword": k, "count": c} 
                for k, c in counts.most_common(10)
            ]
    
    return {
        "total_analyzed": len(optimizations),
        "keyword_analysis": keyword_analysis
    }
