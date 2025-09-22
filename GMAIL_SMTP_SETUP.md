# 🔧 Gmail SMTP Configuration for Railway

## 📋 What You'll Need:
1. Gmail account: `simplythehub@gmail.com`
2. Gmail App Password (not your regular password)
3. Railway dashboard access

## 🚀 Step 1: Generate Gmail App Password

1. **Go to:** https://myaccount.google.com/security
2. **Enable 2-Factor Authentication** (if not already enabled)
3. **Go to:** https://myaccount.google.com/apppasswords
4. **Select:** Mail
5. **Select:** Other (custom name)
6. **Type:** "Railway Django App"
7. **Click:** Generate
8. **Copy the 16-character password** (example: `abcd efgh ijkl mnop`)

## 🔧 Step 2: Configure Railway Variables

**Go to Railway Dashboard:** https://railway.app/dashboard
**Click:** Your project → Variables tab

### **SET these variables:**
```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=simplythehub@gmail.com
EMAIL_HOST_PASSWORD=your_16_character_app_password_here
DEFAULT_FROM_EMAIL=simplythehub@gmail.com
```

### **REMOVE these variables:**
- `RESEND_API_KEY` (delete this completely)

## ⚡ Quick Action Steps:

1. **Delete RESEND_API_KEY** from Railway variables
2. **Add the Gmail SMTP variables above**
3. **Save and let Railway restart**
4. **Test registration** at your site

## 🎯 Step 3: Test Configuration

After Railway restarts, try registering at:
https://web-production-53602.up.railway.app

## 📝 Notes:
- Use the 16-character app password, NOT your regular Gmail password
- Keep 2-Factor Authentication enabled
- Gmail SMTP is free and reliable for moderate email volumes
- No domain verification needed with Gmail SMTP