"""
Security utilities and configurations for the AI Trip Planner application.
"""
import os
import secrets
from typing import Optional
from flask import session
from functools import wraps


class SecurityConfig:
    """Security configuration and utilities."""
    
    # Session configuration
    SESSION_LIFETIME_HOURS = 24
    
    # Rate limiting (if implementing in future)
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_ITINERARY_GENERATIONS_PER_HOUR = 10
    
    # Content Security Policy headers
    CSP_HEADERS = {
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://maps.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.openweathermap.org https://maps.googleapis.com;"
        )
    }
    
    @staticmethod
    def generate_secure_key(length: int = 32) -> str:
        """
        Generate a cryptographically secure random key.
        
        Args:
            length (int): Length of the key to generate
            
        Returns:
            str: Secure random key
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def validate_session_token() -> bool:
        """
        Validate if the current session has a valid token.
        
        Returns:
            bool: True if session is valid
        """
        return 'user_id' in session and session.get('user_id') is not None
    
    @classmethod
    def check_environment_security(cls) -> list:
        """
        Check for common security misconfigurations.
        
        Returns:
            list: List of security warnings
        """
        warnings = []
        
        # Check if running in debug mode in production
        if os.environ.get('FLASK_ENV') == 'production' and os.environ.get('FLASK_DEBUG', '').lower() == 'true':
            warnings.append("DEBUG mode is enabled in production environment")
        
        # Check for default secret keys
        secret_key = os.environ.get('FLASK_SECRET_KEY', '')
        if any(default in secret_key.lower() for default in ['change', 'default', 'secret', 'dev']):
            warnings.append("Using default or weak secret key")
        
        # Check for missing HTTPS in production
        if os.environ.get('FLASK_ENV') == 'production':
            if not os.environ.get('FORCE_HTTPS'):
                warnings.append("HTTPS enforcement not configured for production")
        
        return warnings


def require_auth(f):
    """
    Decorator to require authentication for routes.
    
    Args:
        f: Function to wrap
        
    Returns:
        Wrapped function that checks authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not SecurityConfig.validate_session_token():
            from flask import redirect, url_for, flash
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def sanitize_input(input_string: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent basic attacks.
    
    Args:
        input_string (str): Input to sanitize
        max_length (int): Maximum allowed length
        
    Returns:
        str: Sanitized input
    """
    if not input_string:
        return ""
    
    # Limit length
    sanitized = input_string[:max_length]
    
    # Remove or escape potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&']
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Strip whitespace
    sanitized = sanitized.strip()
    
    return sanitized


def validate_api_key(api_key: Optional[str]) -> bool:
    """
    Validate API key format (basic validation).
    
    Args:
        api_key (str): API key to validate
        
    Returns:
        bool: True if API key appears valid
    """
    if not api_key:
        return False
    
    # Basic checks
    if len(api_key) < 10:
        return False
    
    # Check for obvious test/placeholder values
    test_values = ['test', 'demo', 'placeholder', 'your-api-key', 'change-me']
    if any(test in api_key.lower() for test in test_values):
        return False
    
    return True


def setup_security_headers(app):
    """
    Set up security headers for the Flask application.
    
    Args:
        app: Flask application instance
    """
    @app.after_request
    def add_security_headers(response):
        # Add security headers
        response.headers.update(SecurityConfig.CSP_HEADERS)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Force HTTPS in production
        if os.environ.get('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response