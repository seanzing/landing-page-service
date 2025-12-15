"""Test configuration module"""
import os
import sys
from pathlib import Path

# Add lambda to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lambda'))

from config import Config


def test_config_initialization():
    """Test that config initializes without errors"""
    config = Config()
    assert config is not None
    assert hasattr(config, 'HUBSPOT_API_KEY')
    assert hasattr(config, 'DUDA_API_USER')
    assert hasattr(config, 'OPENAI_API_KEY')


def test_config_defaults():
    """Test that config has sensible defaults"""
    config = Config()
    assert config.DEFAULT_NUM_PAGES == 10
    assert config.CONTENT_TONE == 'professional'
    assert config.CONTENT_LENGTH == '3-4 sentences'
    assert config.ENVIRONMENT == 'production'


def test_config_validation():
    """Test config validation"""
    config = Config()
    # Should fail if API keys not set
    if config.HUBSPOT_API_KEY and config.DUDA_API_USER:
        assert config.validate() == True
