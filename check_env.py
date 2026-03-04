#!/usr/bin/env python3
"""
Environment validation utility for ParaSmile Studio.

Verifies:
1. YOUTUBE_API_KEY is present in .env (REQUIRED)
2. AWS credentials and Budget API access (OPTIONAL)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path('.env')
if not env_path.exists():
    print("❌ ERROR: .env file not found!")
    print("   Create one by copying .env.example:")
    print("   cp .env.example .env")
    sys.exit(1)

load_dotenv(env_path)

def check_youtube_api_key():
    """Verify YouTube API key is present."""
    api_key = os.getenv('YOUTUBE_API_KEY')
    
    if not api_key:
        print("❌ YOUTUBE_API_KEY is missing in .env")
        return False
    
    if api_key == 'your_youtube_api_key_here':
        print("❌ YOUTUBE_API_KEY is still set to placeholder value")
        print("   Get your API key from: https://console.cloud.google.com/apis/credentials")
        return False
    
    if len(api_key) < 20:
        print("⚠️  YOUTUBE_API_KEY seems too short (might be invalid)")
        return False
    
    print(f"✅ YOUTUBE_API_KEY is present ({len(api_key)} characters)")
    return True

def check_aws_budget_api():
    """Verify AWS credentials and Budget API access (optional)."""
    print("\n--- AWS Budget API Check (Optional) ---")
    
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_account_id = os.getenv('AWS_ACCOUNT_ID')
    
    if not aws_access_key or not aws_secret_key:
        print("⏭️  AWS credentials not configured (skipping)")
        return True
    
    if aws_access_key == 'your_aws_access_key_here':
        print("⏭️  AWS credentials are placeholder values (skipping)")
        return True
    
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        print(f"✅ boto3 library is installed")
        
        # Test Budget API access
        client = boto3.client('budgets', region_name='us-east-1')
        
        # Verify account ID
        if not aws_account_id:
            print("⚠️  AWS_ACCOUNT_ID not set in .env")
            return False
        
        print(f"✅ AWS Account ID: {aws_account_id}")
        
        # Try to list budgets (this will fail if credentials are invalid)
        try:
            response = client.describe_budgets(AccountId=aws_account_id, MaxResults=1)
            print(f"✅ Successfully connected to AWS Budget API")
            print(f"   Found {len(response.get('Budgets', []))} budget(s)")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                print("❌ AWS credentials valid but lack Budget API permissions")
                print("   Required permission: budgets:ViewBudget")
            else:
                print(f"❌ AWS Budget API error: {error_code}")
            return False
        except NoCredentialsError:
            print("❌ AWS credentials are invalid")
            return False
            
    except ImportError:
        print("⚠️  boto3 not installed (run: pip install boto3)")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def main():
    """Run all environment checks."""
    print("=" * 50)
    print("Environment Validation for Research Agent")
    print("=" * 50)
    print()
    
    # Required checks
    youtube_ok = check_youtube_api_key()
    
    # Optional checks
    aws_ok = check_aws_budget_api()
    
    print()
    print("=" * 50)
    
    if youtube_ok:
        print("✅ Core environment is ready!")
        if aws_ok:
            print("✅ AWS monitoring is configured")
        else:
            print("⚠️  AWS monitoring is not configured (optional)")
        sys.exit(0)
    else:
        print("❌ Environment setup incomplete")
        print("   Fix the errors above and try again")
        sys.exit(1)

if __name__ == '__main__':
    main()
