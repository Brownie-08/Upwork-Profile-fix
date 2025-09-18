#!/usr/bin/env python3
"""
Validation script to check Render deployment readiness
Run this locally to verify your Django app is ready for Render deployment
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lusitohub.settings')

def validate_render_readiness():
    """Validate that the Django app is ready for Render deployment"""
    
    print("🔍 Validating Render Deployment Readiness...")
    print("=" * 50)
    
    issues = []
    warnings = []
    
    # Check required files
    required_files = [
        'manage.py',
        'build.sh',
        'requirements.txt',
        'runtime.txt',
        'lusitohub/settings.py',
        'lusitohub/wsgi.py'
    ]
    
    print("📁 Checking required files...")
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            issues.append(f"Missing required file: {file_path}")
            print(f"  ❌ {file_path}")
    
    # Check build script permissions and content
    print("\n🔧 Checking build script...")
    build_script = Path('build.sh')
    if build_script.exists():
        content = build_script.read_text()
        if 'pip install -r requirements.txt' in content:
            print("  ✅ Dependencies installation")
        else:
            issues.append("build.sh missing dependency installation")
            
        if 'python manage.py migrate' in content:
            print("  ✅ Database migrations")
        else:
            issues.append("build.sh missing database migrations")
            
        if 'collectstatic' in content:
            print("  ✅ Static files collection")
        else:
            issues.append("build.sh missing static files collection")
    
    # Check requirements.txt
    print("\n📦 Checking requirements.txt...")
    requirements_file = Path('requirements.txt')
    if requirements_file.exists():
        requirements = requirements_file.read_text()
        essential_packages = ['django', 'gunicorn', 'psycopg2-binary', 'whitenoise']
        
        for package in essential_packages:
            if package.lower() in requirements.lower():
                print(f"  ✅ {package}")
            else:
                issues.append(f"Missing essential package in requirements.txt: {package}")
                print(f"  ❌ {package}")
    
    # Initialize Django and check settings
    print("\n⚙️ Checking Django configuration...")
    try:
        django.setup()
        from django.conf import settings
        
        # Check production settings
        if hasattr(settings, 'ALLOWED_HOSTS'):
            if '.onrender.com' in str(settings.ALLOWED_HOSTS):
                print("  ✅ ALLOWED_HOSTS configured for Render")
            else:
                warnings.append("ALLOWED_HOSTS should include .onrender.com for Render")
                print("  ⚠️ ALLOWED_HOSTS missing .onrender.com")
        
        # Check static files configuration
        if hasattr(settings, 'STATIC_ROOT'):
            print("  ✅ STATIC_ROOT configured")
        else:
            issues.append("STATIC_ROOT not configured")
            print("  ❌ STATIC_ROOT missing")
            
        # Check WhiteNoise middleware
        middleware = getattr(settings, 'MIDDLEWARE', [])
        if 'whitenoise.middleware.WhiteNoiseMiddleware' in middleware:
            print("  ✅ WhiteNoise middleware configured")
        else:
            warnings.append("WhiteNoise middleware recommended for static files")
            print("  ⚠️ WhiteNoise middleware missing")
            
        # Check database configuration
        if hasattr(settings, 'DATABASES'):
            print("  ✅ Database configuration present")
        else:
            issues.append("Database configuration missing")
            print("  ❌ Database configuration missing")
            
        # Check email configuration
        if hasattr(settings, 'EMAIL_BACKEND'):
            backend = settings.EMAIL_BACKEND
            if 'smtp' in backend.lower():
                print("  ✅ SMTP email backend configured")
            else:
                warnings.append("Consider using SMTP email backend for production")
                print("  ⚠️ Non-SMTP email backend")
        
        print("  ✅ Django configuration loaded successfully")
        
    except Exception as e:
        issues.append(f"Django configuration error: {str(e)}")
        print(f"  ❌ Django configuration error: {str(e)}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    if not issues:
        print("🎉 ALL CHECKS PASSED! Your app is ready for Render deployment.")
        print("\n📋 Next steps:")
        print("1. Commit and push your changes to GitHub")
        print("2. Create a new Web Service on Render")
        print("3. Add a PostgreSQL database")
        print("4. Configure environment variables")
        print("5. Deploy!")
        print("\n📖 See RENDER_DEPLOYMENT_GUIDE.md for detailed instructions")
    else:
        print(f"❌ {len(issues)} CRITICAL ISSUES FOUND:")
        for issue in issues:
            print(f"  • {issue}")
    
    if warnings:
        print(f"\n⚠️ {len(warnings)} WARNINGS:")
        for warning in warnings:
            print(f"  • {warning}")
    
    print("\n🔗 Helpful Resources:")
    print("• Render Documentation: https://render.com/docs")
    print("• Django Deployment: https://docs.djangoproject.com/en/stable/howto/deployment/")
    
    return len(issues) == 0

if __name__ == "__main__":
    success = validate_render_readiness()
    sys.exit(0 if success else 1)