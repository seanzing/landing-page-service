"""Test content generator"""
import sys
from pathlib import Path

# Add lambda to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lambda'))

from content_generator import ContentGenerator


def test_content_generator_initialization():
    """Test that content generator initializes"""
    gen = ContentGenerator("test-key")
    assert gen is not None
    assert gen.api_key == "test-key"


def test_validate_content():
    """Test content validation"""
    gen = ContentGenerator("test-key")
    
    # Valid content
    valid = "This is professional plumbing service in Denver, Colorado. We provide quality work."
    assert gen.validate_content(valid) == True
    
    # Too short
    short = "Short."
    assert gen.validate_content(short) == False
    
    # Missing period
    no_period = "This is some content without proper punctuation"
    assert gen.validate_content(no_period) == False
