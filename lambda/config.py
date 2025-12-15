"""
Configuration module for Lambda function
Loads all settings from environment variables
"""

import os
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration class - loads all settings from environment variables"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        # HubSpot Configuration
        self.HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY')
        if not self.HUBSPOT_API_KEY:
            logger.warning("HUBSPOT_API_KEY not set in environment variables")
        
        # Duda Configuration
        self.DUDA_API_USER = os.environ.get('DUDA_API_USER')
        self.DUDA_API_PASS = os.environ.get('DUDA_API_PASS')
        if not self.DUDA_API_USER or not self.DUDA_API_PASS:
            logger.warning("DUDA_API_USER or DUDA_API_PASS not set in environment variables")
        
        # OpenAI Configuration
        self.OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
        if not self.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set in environment variables")
        
        # Content Generation Settings - from your environment variables
        self.CONTENT_LENGTH = os.environ.get('CONTENT_LENGTH', '3-4 sentences')
        self.CONTENT_TONE = os.environ.get('CONTENT_TONE', 'professional')
        self.DEFAULT_NUM_PAGES = int(os.environ.get('DEFAULT_NUM_PAGES', 10))
        self.OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        # Logging Configuration - from your environment variables
        self.LOGS_TABLE_NAME = os.environ.get('LOGS_TABLE_NAME', 'hubspot-duda-logs')
        self.NOTIFICATION_EMAIL = os.environ.get('NOTIFICATION_EMAIL')
        self.NOTIFICATION_EMAIL_FROM = os.environ.get('NOTIFICATION_EMAIL_FROM')
        
        # Lambda Configuration
        self.ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')
        self.LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
        
        # Rate Limiting
        self.API_CALL_DELAY = float(os.environ.get('API_CALL_DELAY', 0.5))
        self.MAX_RETRIES = int(os.environ.get('MAX_RETRIES', 3))
        self.RETRY_DELAY = float(os.environ.get('RETRY_DELAY', 1.0))
    
    def validate(self) -> bool:
        """
        Validate that all required configuration is present
        
        Returns:
            True if all required config is valid
        """
        required = ['HUBSPOT_API_KEY', 'DUDA_API_USER', 'DUDA_API_PASS', 'OPENAI_API_KEY']
        for key in required:
            if not getattr(self, key):
                logger.error(f"Missing required configuration: {key}")
                return False
        return True
    
    def __repr__(self):
        """String representation - masks sensitive values"""
        return (
            f"Config(env={self.ENVIRONMENT}, "
            f"hubspot={'***' if self.HUBSPOT_API_KEY else 'MISSING'}, "
            f"duda={'***' if self.DUDA_API_USER else 'MISSING'}, "
            f"openai={'***' if self.OPENAI_API_KEY else 'MISSING'}, "
            f"content_tone={self.CONTENT_TONE}, "
            f"default_pages={self.DEFAULT_NUM_PAGES})"
        )
