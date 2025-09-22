# 🔒 Security Guide - Credential Management

## ⚠️ Important Security Notice

This guide explains how to properly manage credentials and sensitive data in this project to prevent accidental exposure.

## 🚫 What Should NEVER Be Committed

### Environment Files
- `.env` (main environment file)
- `.env.*` (any environment variant)
- `.env.railway`, `.env.heroku`, `.env.vercel`, etc.
- `config.ini`, `secrets.json`

### Credential Files
- `admin_credentials.txt`
- `credentials.txt`
- `*.credentials`
- `api_keys.txt`

### Security Keys
- `*.key`
- `*.pem`
- `*.secret`

## ✅ Safe Files to Commit

### Template Files (OK to commit)
- `.env.example` - Template showing required variables
- `.env.template` - Another template format
- Documentation files explaining setup

## 🛠️ Local Development Setup

### 1. Copy Environment Template
```bash
# Copy the template to create your local environment file
copy .env.example .env
# OR
copy .env.template .env
```

### 2. Fill in Your Credentials
Edit `.env` with your actual values:
```bash
# Django Core Settings
SECRET_KEY=your-actual-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Email Configuration
EMAIL_HOST_USER=your-actual-email@gmail.com
EMAIL_HOST_PASSWORD=your-actual-16-character-app-password

# Google Maps API Keys
Server-Side_API_KEY=your-actual-server-api-key
Client_API_KEY=your-actual-client-api-key

# MTN Mobile Money Configuration
MOMO_SUBSCRIPTION_KEY=your-actual-momo-subscription-key
MOMO_API_USER_ID=your-actual-momo-user-id
MOMO_API_KEY=your-actual-momo-api-key
```

## 🚀 Production Deployment

### Railway
1. Set environment variables in Railway dashboard
2. Never commit `.env.railway` with real credentials

### Render/Heroku
1. Use platform environment variable settings
2. Never commit platform-specific `.env` files

### Vercel/Netlify
1. Use platform environment variable UI
2. Keep `.env.local` files out of git

## 🔍 How to Check for Exposed Credentials

### Check Git Status
```bash
git status
# Should not show any .env files (except templates)
```

### Check What's Being Tracked
```bash
git ls-files | grep -i "\.env"
# Should only show .env.example, .env.template, etc.
```

### Verify .gitignore is Working
```bash
git check-ignore .env
# Should return ".env" indicating it's ignored
```

## 🆘 If Credentials Are Accidentally Committed

### 1. Immediate Actions
- **Change all exposed credentials immediately**
- Rotate API keys, passwords, and secrets
- Update production environment variables

### 2. Clean Git History
```bash
# Remove file from tracking
git rm --cached .env.railway

# Update .gitignore
echo ".env.railway" >> .gitignore
git add .gitignore
git commit -m "Remove credentials and update .gitignore"

# Clean history (WARNING: This rewrites history!)
git filter-branch --force --index-filter \
"git rm --cached --ignore-unmatch .env.railway" \
--prune-empty --tag-name-filter cat -- --all

# Force push (coordinate with team first!)
git push origin --force --all
```

### 3. Verify Cleanup
- Check GitHub repository - file should be gone
- Check commit history - no traces of credentials
- Confirm `.gitignore` is working

## 🛡️ Best Practices

### 1. Use Environment Variables
```python
# In settings.py
import os
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
```

### 2. Keep Templates Updated
- Update `.env.example` when adding new variables
- Document required vs optional variables
- Never put real values in templates

### 3. Regular Security Checks
- Review `.gitignore` regularly
- Check `git status` before committing
- Use git hooks to prevent credential commits

### 4. Team Communication
- Share this guide with all contributors
- Establish credential rotation procedures
- Document incident response procedures

## 🔗 Additional Resources

- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) - Alternative to git filter-branch
- [python-decouple](https://pypi.org/project/python-decouple/) - Environment variable management

---

**Remember**: When in doubt, keep it out of git! It's better to be safe than sorry with credentials.