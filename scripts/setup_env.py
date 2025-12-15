#!/usr/bin/env python3
"""
Setup environment variables from .env file
"""
import os
from pathlib import Path

def setup():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent / '.env'
    
    if not env_file.exists():
        print(f"❌ .env file not found at {env_file}")
        print("   Copy .env.example to .env and fill in your values")
        return False
    
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    print("✅ Environment variables loaded from .env")
    return True

if __name__ == '__main__':
    setup()
