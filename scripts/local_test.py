#!/usr/bin/env python3
"""
Local testing script - test Lambda locally without AWS
"""
import sys
import json
from pathlib import Path

# Add lambda to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lambda'))

from scripts.setup_env import setup
setup()

from lambda_function import HubSpotDudaIntegration

def test_local():
    """Test the integration locally"""
    print("🧪 Testing HubSpot to Duda Integration Locally")
    print("=" * 50)
    
    try:
        integration = HubSpotDudaIntegration()
        print("✅ Successfully initialized integration")
        print(f"   Config: {integration.config}")
        
        # Test configuration validation
        if not integration.config.validate():
            print("⚠️  Warning: Some environment variables are missing")
            print("   Set them in .env file to enable full testing")
        else:
            print("✅ All required environment variables are set")
        
        # Show what would be called
        print("\n📋 Ready to process webhooks with:")
        print(f"   - HubSpot API Key: {'***' if integration.config.HUBSPOT_API_KEY else 'NOT SET'}")
        print(f"   - Duda API User: {'***' if integration.config.DUDA_API_USER else 'NOT SET'}")
        print(f"   - OpenAI API Key: {'***' if integration.config.OPENAI_API_KEY else 'NOT SET'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_local()
    sys.exit(0 if success else 1)
