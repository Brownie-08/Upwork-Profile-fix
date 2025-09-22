# 🔧 LusitoHub Environment Setup Guide

This guide helps you configure all the necessary environment variables for LusitoHub.

## 📋 Quick Setup

1. **Copy the template**:
   ```bash
   cp .env.template .env
   ```

2. **Edit the .env file** with your actual credentials
3. **Follow the detailed setup instructions** below

## 🔑 Credential Setup Instructions

### 1. Gmail Configuration (Email Sending)

**Current Email**: `ncabamatse@gmail.com`

#### Step 1: Enable 2-Factor Authentication
1. Go to https://myaccount.google.com/security
2. Sign in with `ncabamatse@gmail.com`
3. Click "2-Step Verification" and follow setup

#### Step 2: Generate App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Other (custom name)"
3. Name it "LusitoHub Django App"
4. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)

#### Step 3: Update .env file
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=ncabamatse@gmail.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=ncabamatse@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password-here
EMAIL_USE_TLS=True
```

### 2. Google Maps API Setup

#### Step 1: Get API Keys
1. Go to https://console.cloud.google.com/
2. Create/select a project
3. Enable Google Maps JavaScript API and Places API
4. Create two API keys:
   - **Server-side key**: Restrict to your server IP
   - **Client-side key**: Restrict to your domain

#### Step 2: Update .env file
```env
Server-Side_API_KEY=AIza...your-server-key
Client_API_KEY=AIza...your-client-key
```

### 3. MTN MoMo API Setup

#### Step 1: Create MTN Developer Account
1. Visit https://momodeveloper.mtn.com/
2. Sign up/login
3. Create a new subscription for Collection API
4. Get your subscription key

#### Step 2: Generate API User and Key
```bash
# Use MTN MoMo API to create user and get API key
# Follow MTN documentation for your region
```

#### Step 3: Update .env file
```env
MOMO_BASE_URL=https://sandbox.momodeveloper.mtn.com
MOMO_SUBSCRIPTION_KEY=your-subscription-key
MOMO_API_USER_ID=your-api-user-id
MOMO_API_KEY=your-api-key
MOMO_CALLBACK_URL=https://yourdomain.com/momo/callback/
MOMO_PROVIDER_CALLBACK_HOST=https://yourdomain.com
MOMO_ENVIRONMENT=sandbox
MOMO_CURRENCY=SZL
```

### 4. Database Configuration

#### Development (SQLite)
```env
DATABASE_URL=sqlite:///db.sqlite3
```

#### Production (PostgreSQL)
```env
DATABASE_URL=postgres://username:password@localhost:5432/lusitohub
```

### 5. SMS Provider Setup (Optional)

Choose one of these providers:

#### Twilio
```env
SMS_API_KEY=your-twilio-auth-token
SMS_SENDER=your-twilio-phone-number
```

#### Africa's Talking
```env
SMS_API_KEY=your-africastalking-api-key
SMS_SENDER=your-sender-name
```

## 🧪 Testing Your Configuration

### Test Email Sending
```bash
python manage.py shell
```

```python
from django.core.mail import send_mail
send_mail(
    'Test Email',
    'This is a test email from LusitoHub.',
    'ncabamatse@gmail.com',
    ['test@example.com'],
    fail_silently=False,
)
```

### Test Database Connection
```bash
python manage.py migrate
python manage.py createsuperuser
```

### Test Application
```bash
python manage.py runserver
# Visit http://127.0.0.1:8000/admin/
```

## 🚀 Production Environment

### Additional Production Settings
```env
# Security
SECRET_KEY=generate-a-new-secret-key-for-production
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgres://lusitohub:strong-password@db-server:5432/lusitohub

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

# Caching
REDIS_URL=redis://redis-server:6379/1

# File Storage (optional)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_STORAGE_BUCKET_NAME=your-s3-bucket
```

## 🔒 Security Best Practices

1. **Never commit .env files** to version control
2. **Use different credentials** for development/production
3. **Rotate credentials regularly**
4. **Restrict API keys** by IP/domain where possible
5. **Monitor API usage** for unusual activity
6. **Use strong passwords** for all accounts
7. **Enable 2FA** on all service accounts

## 📞 Support

If you need help with credential setup:

### Gmail Issues
- Check if 2FA is enabled
- Verify app password is correct (16 characters, no spaces)
- Try generating a new app password

### API Key Issues
- Verify billing is enabled (Google Maps)
- Check API quotas and limits
- Ensure proper API restrictions

### Database Issues
- Check connection string format
- Verify database server is running
- Ensure user has proper permissions

## 🔄 Credential Rotation Schedule

- **Gmail App Password**: Every 6 months
- **Google Maps API Keys**: Every 12 months
- **MTN MoMo Keys**: As required by MTN
- **Database Passwords**: Every 3 months
- **Django Secret Key**: For each deployment

---

**Remember**: Keep this information secure and never share credentials in public channels!
