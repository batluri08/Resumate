"""
Authentication Router - Handles signup, login, logout endpoints
"""


from fastapi import APIRouter, Request, Form, HTTPException, Depends, Response, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta
from app.database import get_db, User
from app.services.auth_service import AuthService
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
templates = Jinja2Templates(directory="app/templates")


# Cookie settings
COOKIE_NAME = "session_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days

# OAuth2/JWT settings - auto_error=False allows optional auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)



# Unified current user getter: supports both JWT and session cookie
def get_current_user(request: Request = None, db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
    # Try JWT first (with proper error handling)
    if token:
        try:
            payload = AuthService.decode_access_token(token)
            if payload and "sub" in payload:
                user_id = int(payload["sub"])
                user = AuthService.get_user_by_id(db, user_id)
                if user:
                    logger.debug(f"Current user authenticated via JWT: id={user_id}")
                    return user
                else:
                    logger.warning(f"JWT token references non-existent user: id={user_id}")
        except Exception as e:
            logger.debug(f"JWT token validation failed: {str(e)}")
            pass  # Fall through to session cookie check
    # Fallback to session cookie
    if request:
        cookie_token = request.cookies.get(COOKIE_NAME)
        if cookie_token:
            user_id = AuthService.validate_session(cookie_token)
            if user_id:
                user = AuthService.get_user_by_id(db, user_id)
                if user:
                    logger.debug(f"Current user authenticated via session cookie: id={user_id}")
                    return user
                else:
                    logger.warning(f"Session token references non-existent user: id={user_id}")
    logger.debug("No valid authentication found (neither JWT nor session cookie)")
    return None



def require_auth(request: Request = None, db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)) -> User:
    user = get_current_user(request, db, token)
    if not user:
        logger.warning("Authentication required but no valid user found")
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/login")
async def login_page(request: Request):
    """Render login page"""
    # If already logged in, redirect to home
    token = request.cookies.get(COOKIE_NAME)
    if token and AuthService.validate_session(token):
        return RedirectResponse(url="/resume", status_code=302)

    # Show error message if present in query params
    error = request.query_params.get("error")
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.get("/signup")
async def signup_page(request: Request):
    """Render signup page"""
    # If already logged in, redirect to home
    token = request.cookies.get(COOKIE_NAME)
    if token and AuthService.validate_session(token):
        return RedirectResponse(url="/resume", status_code=302)
    
    return templates.TemplateResponse("signup.html", {"request": request})



@router.post("/signup")
async def signup(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(""),
    db: Session = Depends(get_db)
):
    """Handle user registration"""
    logger.info(f"Signup attempt for email: {email}")
    
    # Validate input
    if len(password) < 6:
        logger.warning(f"Signup failed for {email}: Password too short")
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Password must be at least 6 characters"
        })
    if not email or "@" not in email:
        logger.warning(f"Signup failed: Invalid email format - {email}")
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Invalid email address"
        })
    try:
        user = AuthService.create_user(db, email, password, name)
        logger.info(f"User signup successful: id={user.id}, email={email}")
        
        # Issue JWT
        access_token = AuthService.create_access_token({"sub": str(user.id)})
        # Also create legacy session cookie for compatibility
        session_token = AuthService.create_session(user.id)
        logger.debug(f"Session token created for user {user.id}")
        
        response = RedirectResponse(url="/resume", status_code=303)
        response.set_cookie(
            key=COOKIE_NAME,
            value=session_token,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/"
        )
        # Optionally, set JWT as cookie or return in response (for API clients)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/"
        )
        return response
    except ValueError as e:
        logger.error(f"Signup error for {email}: {str(e)}")
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": str(e)
        })



@router.post("/login")
async def login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle user login"""
    logger.info(f"Login attempt for email: {email}")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or \
              "application/json" in request.headers.get("Accept", "")
    user = AuthService.authenticate_user(db, email, password)
    if not user:
        logger.warning(f"Login failed for {email}: Invalid credentials")
        if is_ajax:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password"
        })
    
    logger.info(f"Login successful for user: id={user.id}, email={email}")
    # Issue JWT
    access_token = AuthService.create_access_token({"sub": str(user.id)})
    # Also create legacy session cookie for compatibility
    session_token = AuthService.create_session(user.id)
    logger.debug(f"Session and JWT tokens created for user {user.id}")
    
    response = RedirectResponse(url="/resume", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/"
    )
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/"
    )
    return response

# OAuth2 password flow endpoint for API clients
@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    logger.info(f"Token request for user: {form_data.username}")
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Token request failed for {form_data.username}: Invalid credentials")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = AuthService.create_access_token({"sub": str(user.id)})
    logger.info(f"Token successfully issued for user: id={user.id}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/logout")
@router.post("/logout")
async def logout(request: Request, response: Response):
    """Handle user logout"""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        user_id = AuthService.validate_session(token)
        logger.info(f"Logout for user: id={user_id}")
        AuthService.invalidate_session(token)
    else:
        logger.debug("Logout attempt with no session token")
    
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(key=COOKIE_NAME)
    return response



# JWT-protected user info endpoint
@router.get("/me")
async def get_current_user_info_jwt(current_user: User = Depends(require_auth)):
    logger.debug(f"User info requested for: id={current_user.id}, email={current_user.email}")
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "created_at": current_user.created_at.isoformat()
    }
