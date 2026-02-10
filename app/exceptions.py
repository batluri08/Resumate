"""
Custom exceptions for RestlessResume
"""

from fastapi import HTTPException, status


class RestlessResumeException(Exception):
    """Base exception for RestlessResume"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(RestlessResumeException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(RestlessResumeException):
    """Raised when user lacks permission"""
    def __init__(self, message: str = "You don't have permission to access this resource"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ValidationError(RestlessResumeException):
    """Raised when input validation fails"""
    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class NotFoundError(RestlessResumeException):
    """Raised when requested resource is not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class FileProcessingError(RestlessResumeException):
    """Raised when file processing fails"""
    def __init__(self, message: str = "Failed to process file"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class AIOptimizationError(RestlessResumeException):
    """Raised when AI optimization fails"""
    def __init__(self, message: str = "Failed to optimize resume"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class DatabaseError(RestlessResumeException):
    """Raised when database operation fails"""
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class OAuthError(RestlessResumeException):
    """Raised when OAuth login fails"""
    def __init__(self, message: str = "OAuth login failed"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


def exception_to_http_exception(exc: RestlessResumeException) -> HTTPException:
    """Convert RestlessResumeException to HTTPException"""
    return HTTPException(status_code=exc.status_code, detail=exc.message)
