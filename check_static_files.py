#!/usr/bin/env python
"""
Static file diagnostic script - checks if all required static files exist
Run this to verify static file configuration

Usage:
python check_static_files.py
"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lusitohub.settings')
django.setup()

from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static


def check_static_files():
    """Check if all required static files exist and are accessible"""
    
    print("🔧 Static Files Diagnostic")
    print("=" * 50)
    
    # Check settings
    print(f"📁 STATIC_URL: {settings.STATIC_URL}")
    print(f"📁 STATIC_ROOT: {settings.STATIC_ROOT}")
    print(f"📁 STATICFILES_DIRS: {settings.STATICFILES_DIRS}")
    
    # Check if directories exist
    print(f"\n📂 Directory Check:")
    for static_dir in settings.STATICFILES_DIRS:
        exists = static_dir.exists()
        print(f"   {static_dir}: {'✅ EXISTS' if exists else '❌ MISSING'}")
        
    if settings.STATIC_ROOT and Path(settings.STATIC_ROOT).exists():
        print(f"   {settings.STATIC_ROOT}: ✅ EXISTS")
    else:
        print(f"   {settings.STATIC_ROOT}: ⚠️  MISSING (created during collectstatic)")
    
    # Critical static files to check
    critical_files = [
        'images/user-avatar.svg',
        'images/lusito_logo.svg',
        'css/admin_custom.css',
        'js/admin_custom.js',
        'favicon.ico',
    ]
    
    print(f"\n🔍 Critical Files Check:")
    all_good = True
    
    for file_path in critical_files:
        # Try to find the file
        found = finders.find(file_path)
        if found:
            print(f"   ✅ {file_path}: Found at {found}")
        else:
            print(f"   ❌ {file_path}: NOT FOUND")
            all_good = False
            
        # Also check the URL resolution
        try:
            url = static(file_path)
            print(f"      URL: {url}")
        except Exception as e:
            print(f"      URL Error: {e}")
    
    # Check if the problematic file is resolved
    print(f"\n🚨 Problematic File Check:")
    problem_files = [
        'media/user-avatar.svg',
        'media/default.jpg',
    ]
    
    for file_path in problem_files:
        found = finders.find(file_path)
        if found:
            print(f"   ⚠️  {file_path}: Found at {found} (should be moved/fixed)")
        else:
            print(f"   ✅ {file_path}: NOT FOUND (good - means it's been fixed)")
    
    print(f"\n📊 Summary:")
    if all_good:
        print("✅ All critical static files found!")
        print("🚀 Your static file configuration looks good")
    else:
        print("❌ Some critical static files are missing")
        print("🔧 Run 'python manage.py collectstatic' to fix this")
    
    return all_good


def check_media_views():
    """Check if media views are configured correctly"""
    print(f"\n📷 Media Configuration Check:")
    print(f"📁 MEDIA_URL: {settings.MEDIA_URL}")
    print(f"📁 MEDIA_ROOT: {settings.MEDIA_ROOT}")
    
    media_root = Path(settings.MEDIA_ROOT)
    if media_root.exists():
        print(f"   {media_root}: ✅ EXISTS")
    else:
        print(f"   {media_root}: ❌ MISSING")
        media_root.mkdir(parents=True, exist_ok=True)
        print(f"   Created: {media_root}")


def suggest_fixes():
    """Suggest fixes for common static file issues"""
    print(f"\n🔧 Common Fixes:")
    print("1. For missing static files in production:")
    print("   python manage.py collectstatic --noinput")
    print()
    print("2. For Railway deployment, ensure these are set:")
    print("   - Static files are collected during build")
    print("   - WhiteNoise middleware is configured")
    print("   - STATICFILES_STORAGE is set for production")
    print()
    print("3. For avatar loading issues:")
    print("   - Check template paths use 'images/user-avatar.svg'")
    print("   - Avoid paths like 'media/user-avatar.svg' or 'media/default.jpg'")
    print("   - Use proper onerror handlers to prevent infinite loops")


if __name__ == "__main__":
    print("🚀 LusitoHub Static Files Diagnostic")
    print("=" * 60)
    
    static_success = check_static_files()
    check_media_views()
    suggest_fixes()
    
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC COMPLETE")
    print("=" * 60)
    
    if static_success:
        print("🎉 Static file configuration looks good!")
        print("📧 Avatar loading issues should be resolved")
    else:
        print("🚨 Static file issues found - follow the fixes above")
    
    print("=" * 60)