# 🚨 URGENT EMAIL FIX - Railway Production

## Problem
Resend is rejecting emails because `simplythehub@gmail.com` is not a verified domain.

## 🎯 **QUICK FIX (Choose ONE option):**

### Option 1: Use Resend's Test Domain (IMMEDIATE FIX)
**Go to Railway Dashboard → Your Project → Variables:**

```
DEFAULT_FROM_EMAIL=onboarding@resend.dev
```

This will work immediately as `resend.dev` is pre-verified.

### Option 2: Use Your Own Domain (BETTER)
**Go to Railway Dashboard → Your Project → Variables:**

```
DEFAULT_FROM_EMAIL=noreply@lusitohub.com
```

**Then go to [Resend Domains](https://resend.com/domains) and:**
1. Click "Add Domain"
2. Enter: `lusitohub.com`
3. Add the DNS records to your domain provider
4. Verify the domain

### Option 3: Switch to Gmail SMTP (BACKUP PLAN)
**Go to Railway Dashboard → Your Project → Variables and ADD these:**

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=simplythehub@gmail.com
EMAIL_HOST_PASSWORD=your_app_password_here
DEFAULT_FROM_EMAIL=simplythehub@gmail.com
```

**Remove these variables:**
```
RESEND_API_KEY (delete this)
```

## 🚀 **RECOMMENDED: Option 1 (Quick Test)**

1. **Go to:** https://railway.app/dashboard
2. **Click:** Your project
3. **Click:** Variables tab
4. **Find:** `DEFAULT_FROM_EMAIL`
5. **Change to:** `onboarding@resend.dev`
6. **Click:** Save

**Your app will restart automatically and emails should work immediately!**

## 🔍 Test After Fix
Try registering again at: https://web-production-53602.up.railway.app

## Notes
- `onboarding@resend.dev` is Resend's test domain - works instantly
- Users will still receive emails normally
- For production, consider using your own verified domain later