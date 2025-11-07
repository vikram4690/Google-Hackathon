"""
Error handling utilities for the AI Trip Planner application.
"""
import logging
from functools import wraps
from typing import Callable, Any
from flask import jsonify, flash, redirect, url_for
from google.api_core.exceptions import ResourceExhausted
import requests


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TripPlannerError(Exception):
    """Base exception for trip planner errors."""
    pass


class APIError(TripPlannerError):
    """Exception for external API errors."""
    pass


class ConfigurationError(TripPlannerError):
    """Exception for configuration errors."""
    pass


def handle_api_errors(func: Callable) -> Callable:
    """
    Decorator to handle common API errors.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            logger.error(f"Timeout error in {func.__name__}")
            raise APIError("Request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error in {func.__name__}")
            raise APIError("Unable to connect to external service.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error in {func.__name__}: {e}")
            if e.response.status_code == 429:
                raise APIError("Service is temporarily busy. Please try again later.")
            elif e.response.status_code >= 500:
                raise APIError("External service is temporarily unavailable.")
            else:
                raise APIError(f"API request failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise APIError(f"An unexpected error occurred: {str(e)}")
    
    return wrapper


def handle_vertex_ai_errors(func: Callable) -> Callable:
    """
    Decorator to handle Vertex AI specific errors.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ResourceExhausted:
            logger.warning(f"Rate limit exceeded in {func.__name__}")
            raise TripPlannerError("AI service is currently busy. Please try again in a few minutes.")
        except Exception as e:
            error_message = str(e)
            logger.error(f"Vertex AI error in {func.__name__}: {error_message}")
            
            if "Malformed function call" in error_message:
                raise TripPlannerError("Unable to process request with current parameters. Please try different inputs.")
            elif "quota" in error_message.lower():
                raise TripPlannerError("AI service quota exceeded. Please try again later.")
            else:
                raise TripPlannerError("AI service encountered an error. Please try again.")
    
    return wrapper


def handle_route_errors(func: Callable) -> Callable:
    """
    Decorator to handle Flask route errors and provide user feedback.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TripPlannerError as e:
            logger.warning(f"Trip planner error in {func.__name__}: {e}")
            flash(str(e), "error")
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Unexpected error in route {func.__name__}: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
            return redirect(url_for('index'))
    
    return wrapper


def handle_api_route_errors(func: Callable) -> Callable:
    """
    Decorator to handle API route errors and return JSON responses.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TripPlannerError as e:
            logger.warning(f"Trip planner error in API {func.__name__}: {e}")
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            logger.error(f"Unexpected error in API route {func.__name__}: {e}")
            return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500
    
    return wrapper


def log_function_call(func: Callable) -> Callable:
    """
    Decorator to log function calls for debugging.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with logging
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Calling {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"Successfully completed {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    
    return wrapper