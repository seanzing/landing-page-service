#!/usr/bin/env python3
"""
Deploy Lambda function to AWS
"""
import os
import sys
import zipfile
from pathlib import Path
import subprocess

def create_deployment_package():
    """Create Lambda deployment zip"""
    project_root = Path(__file__).parent.parent
    lambda_dir = project_root / 'lambda'
    output_zip = project_root / 'lambda-deployment.zip'
    
    # Remove old zip if exists
    if output_zip.exists():
        output_zip.unlink()
    
    # Create new zip
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in lambda_dir.glob('*.py'):
            zf.write(file, arcname=file.name)
    
    print(f"✅ Created deployment package: {output_zip}")
    print(f"   Size: {output_zip.stat().st_size / 1024 / 1024:.1f} MB")
    
    return output_zip

def deploy_to_aws():
    """Deploy zip to AWS Lambda"""
    zip_file = create_deployment_package()
    
    print("\n📦 To deploy manually:")
    print(f"   1. Go to AWS Lambda console")
    print(f"   2. Upload {zip_file.name}")
    print(f"   3. Set environment variables")
    print(f"   4. Test with CloudWatch logs")
    
    print("\n🤖 Or use AWS CLI:")
    print(f"   aws lambda update-function-code \\")
    print(f"     --function-name hubspot-duda-integration \\")
    print(f"     --zip-file fileb://{zip_file}")

if __name__ == '__main__':
    try:
        deploy_to_aws()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
