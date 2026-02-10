"""
Authentication Service for RestlessResume
Handles user registration, login, password hashing, and session management
"""


import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
import secrets
from jose import JWTError, jwt
from app.database import User

# JWT settings
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Session storage (legacy, for compatibility)
active_sessions = {}


class AuthService:
    """Authentication service for user management"""

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> Optional[dict]:
        """Decode a JWT access token and return the payload if valid"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storage"""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            password_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            return False
    
    @staticmethod
    def create_user(db: Session, email: str, password: str, name: str = None) -> User:
        """Create a new user account"""
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email.lower()).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create new user
        user = User(
            email=email.lower().strip(),
            password_hash=AuthService.hash_password(password),
            name=name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            return None
        if not AuthService.verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user
    
    @staticmethod
    def create_session(user_id: int) -> str:
        """Create a new session token for a user (legacy)"""
        token = secrets.token_urlsafe(32)
        active_sessions[token] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=7)
        }
        return token
    
    @staticmethod
    def validate_session(token: str) -> Optional[int]:
        """Validate a session token (legacy) and return user_id if valid"""
        if not token or token not in active_sessions:
            return None
        session = active_sessions[token]
        if datetime.utcnow() > session["expires_at"]:
            del active_sessions[token]
            return None
        return session["user_id"]
    
    @staticmethod
    def invalidate_session(token: str) -> bool:
        """Invalidate/logout a session"""
        if token in active_sessions:
            del active_sessions[token]
            return True
        return False
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email.lower()).first()
    
    @staticmethod
    def update_password(db: Session, user_id: int, new_password: str) -> bool:
        """Update user's password"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.password_hash = AuthService.hash_password(new_password)
        db.commit()
        return True
