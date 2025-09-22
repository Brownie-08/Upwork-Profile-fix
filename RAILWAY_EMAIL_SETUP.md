# 📧 Railway Email Setup Guide - Fix "Network Unreachable" Issue

## 🚨 **Problem: Railway Blocks Gmail SMTP**

Railway (like many cloud platforms) blocks outbound SMTP connections to external email providers like Gmail for security reasons. This causes the `[Errno 101] Network is unreachable` error.

## ✅ **Solution: Use Railway-Compatible Email Services**

### **Option 1: Resend (Recommended - FREE)**

Resend is designed for developers and works perfectly with Railway.

**Free Tier**: 3,000 emails/month (perfect for OTP verification)

#### Setup Steps:

1. **Create Resend Account**:
   - Go to https://resend.com
   - Sign up with your email
   - Verify your account

2. **Get API Key**:
   - Go to your Resend dashboard
   - Navigate to "API Keys" 
   - Click "Create API Key"
   - Copy the API key (starts with `re_`)

3. **Configure Railway**:
   - Go to Railway Dashboard
   - Select your project
   - Go to Variables tab
   - Add new variable:
     ```
     RESEND_API_KEY=re_your_api_key_here
     ```

4. **Verify Domain (Optional but Recommended)**:
   - In Resend dashboard, go to "Domains"
   - Add your domain (e.g., `lusitohub.com`)
   - Follow verification instructions
   - This improves deliverability and removes "via Resend" branding

#### Test Setup:
```bash
# Your Railway environment variables should include:
RESEND_API_KEY=re_your_api_key_here
DEFAULT_FROM_EMAIL=noreply@yourdomain.com  # or youremail@gmail.com
```

### **Option 2: SendGrid (Alternative - FREE)**

SendGrid also works well with Railway.

**Free Tier**: 100 emails/day (sufficient for small apps)

#### Setup Steps:

1. **Create SendGrid Account**:
   - Go to https://sendgrid.com
   - Sign up and verify your account
   - Complete the sender verification process

2. **Get API Key**:
   - Go to Settings > API Keys
   - Click "Create API Key"
   - Choose "Full Access" or "Restricted Access" with Mail Send permissions
   - Copy the API key (starts with `SG.`)

3. **Configure Railway**:
   ```
   SENDGRID_API_KEY=SG.your_api_key_here
   DEFAULT_FROM_EMAIL=noreply@yourdomain.com
   ```

### **Option 3: Keep Gmail SMTP (May Not Work)**

If you want to try Gmail SMTP (though it may be blocked):

#### Alternative Gmail Settings:
Try these settings which sometimes work better on cloud platforms:

```bash
# In Railway Variables:
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_SSL=true
EMAIL_USE_TLS=false
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

## 🔧 **Current Code Changes**

The code now automatically detects and tries multiple email services:

1. **Resend API** (if `RESEND_API_KEY` is set)
2. **SendGrid API** (if `SENDGRID_API_KEY` is set) 
3. **Gmail SMTP** (if credentials are set - may fail)
4. **Console fallback** (for development)

## 🎯 **Recommended Setup for Production**

For your Railway deployment, I recommend:

```bash
# Railway Environment Variables (RECOMMENDED):
RESEND_API_KEY=re_your_resend_api_key
DEFAULT_FROM_EMAIL=noreply@lusitohub.com

# Keep your Gmail settings as backup:
EMAIL_HOST_USER=udohpeterbrown@gmail.com
EMAIL_HOST_PASSWORD=fdachcuqlibcctsb
```

## 🚀 **Deployment Steps**

1. **Set up Resend account** (5 minutes)
2. **Add `RESEND_API_KEY` to Railway**
3. **Deploy the updated code** (already done)
4. **Test registration** - users should now receive emails!

## 📊 **Email Service Comparison**

| Service | Free Tier | Setup Time | Railway Compatible | Recommended |
|---------|-----------|------------|-------------------|-------------|
| **Resend** | 3,000/month | 5 minutes | ✅ Yes | ⭐ **BEST** |
| **SendGrid** | 100/day | 10 minutes | ✅ Yes | ✅ Good |
| **Gmail SMTP** | Unlimited | Already done | ❌ Blocked | ❌ Won't work |

## 🔍 **Troubleshooting**

### If emails still don't work after setting up Resend:

1. **Check Railway logs** for "Production Resend API configured" message
2. **Verify API key** is correctly set (no quotes around the value)
3. **Check Resend dashboard** for sending activity and errors
4. **Test with `/csrf-debug/`** to ensure other systems work

### Common Issues:

- **"RESEND_API_KEY not configured"**: The API key is not set in Railway
- **"Resend API error: 403"**: Invalid API key or domain not verified
- **"Resend API error: 422"**: Invalid email format or missing required fields

## 💡 **Pro Tips**

1. **Domain Verification**: Verify your domain in Resend to improve deliverability
2. **Email Templates**: Resend supports HTML templates for better-looking emails
3. **Analytics**: Resend provides email analytics (opens, clicks, bounces)
4. **Multiple Providers**: The code tries multiple services, so you can set up both Resend AND SendGrid as backups

## 🎉 **Expected Result**

After setting up Resend:

```
📧 Production Resend API configured  
✅ Users will receive OTP codes via Resend
🚀 Production environment detected: Railway=True
```

**Users will receive OTP codes in their email inbox instead of getting "Network unreachable" errors!**