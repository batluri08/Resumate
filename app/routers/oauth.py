"""
Google OAuth2 Login Router for RestlessResume
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
import httpx
from app.database import get_db, User
from app.services.auth_service import AuthService
from app.logging_config import get_logger
import os

logger = get_logger(__name__)

router = APIRouter(prefix="/oauth", tags=["oauth"])

# Initialize OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID', ''),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET', ''),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get('/login/google')
async def login_via_google(request: Request):
    try:
        logger.info("Google OAuth login initiated")
        # Use request.url_for to get the callback URL
        redirect_uri = request.url_for('auth_via_google')
        logger.debug(f"OAuth redirect URI: {redirect_uri}")
        return await oauth.google.authorize_redirect(request, str(redirect_uri))
    except Exception as e:
        logger.error(f"Google OAuth login failed: {str(e)}")
        error_msg = str(e).replace(' ', '%20').replace(':', '%3A')
        return RedirectResponse(url=f"/auth/login?error=OAuth%20Error:%20{error_msg}", status_code=303)

@router.get('/auth/google', name='auth_via_google')
async def auth_via_google(request: Request, db: Session = Depends(get_db)):
    try:
        logger.info("Google OAuth callback received")
        # Get the token from the OAuth provider
        token = await oauth.google.authorize_access_token(request)
        logger.debug("OAuth token obtained from Google")
        
        # Get user info from Google's userinfo endpoint
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                'https://openidconnect.googleapis.com/v1/userinfo',
                headers={'Authorization': f'Bearer {token["access_token"]}'}
            )
            resp.raise_for_status()
            user_info = resp.json()
        
        logger.debug(f"User info fetched from Google: email={user_info.get('email')}")
        email = user_info.get('email')
        name = user_info.get('name')
        if not email:
            logger.warning("Google account missing email field")
            return RedirectResponse(url="/auth/login?error=Google%20account%20missing%20email", status_code=303)

        # Find or create user
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            logger.info(f"Creating new user from Google OAuth: email={email}")
            try:
                user = AuthService.create_user(db, email=email, password=os.urandom(16).hex(), name=name)
                logger.info(f"New user created successfully: id={user.id}, email={email}")
            except ValueError as e:
                logger.error(f"Failed to create user from Google OAuth: {str(e)}")
                error_msg = str(e).replace(' ', '%20')
                return RedirectResponse(url=f"/auth/login?error={error_msg}", status_code=303)
        else:
            logger.info(f"Existing user found: id={user.id}, email={email}")

        # Issue JWT and session cookie
        access_token = AuthService.create_access_token({"sub": str(user.id)})
        session_token = AuthService.create_session(user.id)
        logger.info(f"Google OAuth login successful: id={user.id}, email={email}")
        
        response = RedirectResponse(url="/resume", status_code=303)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            max_age=60*60*24*7,
            httponly=True,
            samesite="lax",
            path="/"
        )
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=60*60*24*7,
            httponly=True,
            samesite="lax",
            path="/"
        )
        return response
    except httpx.HTTPError as e:
        logger.error(f"HTTP error during Google OAuth callback: {str(e)}")
        error_msg = f"Failed%20to%20fetch%20user%20info:%20{str(e)[:50]}"
        return RedirectResponse(url=f"/auth/login?error={error_msg}", status_code=303)
    except Exception as e:
        logger.error(f"Unexpected error during Google OAuth callback: {str(e)}")
        error_msg = str(e).replace(' ', '%20').replace(':', '%3A')[:100]
        return RedirectResponse(url=f"/auth/login?error=Unexpected%20error:%20{error_msg}", status_code=303)
