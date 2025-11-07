"""
Configuration module for the AI Trip Planner application.
Handles environment variables and application settings.
"""
import os
from typing import Dict, Any


class Config:
    """Base configuration class."""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Google Cloud Configuration
    GOOGLE_PROJECT_ID = os.environ.get('GOOGLE_PROJECT_ID')
    VERTEX_LOCATION = 'asia-south1'
    
    # API Keys
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')
    
    # Cloud Function URLs
    SAVE_TRIP_FUNCTION_URL = "https://asia-south1-principal-lane-470311-j4.cloudfunctions.net/save-trip"
    GET_TRIPS_FUNCTION_URL = "https://asia-south1-principal-lane-470311-j4.cloudfunctions.net/get-trips"
    BOOK_TRIP_FUNCTION_URL = "https://asia-south1-principal-lane-470311-j4.cloudfunctions.net/book-trip"
    MANAGE_SHARES_FUNCTION_URL = "https://asia-south1-principal-lane-470311-j4.cloudfunctions.net/manage-trip-shares"
    
    # Default Values
    DEFAULT_HOTEL_PRICE = 3500.0
    MAX_TOOL_CALLS = 5
    MAX_RETRIES = 3
    
    @classmethod
    def validate_required_config(cls) -> Dict[str, str]:
        """
        Validate that all required configuration is present.
        
        Returns:
            Dict[str, str]: Dictionary of missing required variables
        """
        required_vars = {
            'GOOGLE_PROJECT_ID': cls.GOOGLE_PROJECT_ID,
            'GOOGLE_MAPS_API_KEY': cls.GOOGLE_MAPS_API_KEY
        }
        
        missing_vars = {var: value for var, value in required_vars.items() if not value}
        return missing_vars
    
    @classmethod
    def get_optional_config_warnings(cls) -> Dict[str, str]:
        """
        Get warnings for missing optional configuration.
        
        Returns:
            Dict[str, str]: Dictionary of optional variables and their warnings
        """
        optional_vars = {
            'RAPIDAPI_KEY': 'Hotel pricing will use default values',
            'OPENWEATHER_API_KEY': 'Weather features will be disabled'
        }
        
        warnings = {}
        for var, warning in optional_vars.items():
            if not getattr(cls, var):
                warnings[var] = warning
        
        return warnings


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    @classmethod
    def validate_production_config(cls):
        """Additional validation for production environment."""
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            raise ValueError("FLASK_SECRET_KEY must be set in production!")


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = None) -> Config:
    """
    Get configuration class based on environment.
    
    Args:
        config_name (str): Configuration name ('development', 'production')
        
    Returns:
        Config: Configuration class instance
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config.get(config_name, config['default'])