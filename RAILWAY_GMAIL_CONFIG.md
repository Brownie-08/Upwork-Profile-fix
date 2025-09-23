# 📧 URGENT: Railway Gmail SMTP Configuration

## 🚨 **IMMEDIATE ACTION REQUIRED**

Configure these environment variables in Railway Dashboard:

**Go to:** https://railway.app/dashboard → Your Project → Variables

---

## 📧 **Gmail SMTP Configuration**

### **Step 1: Remove Resend**
```
❌ DELETE this variable:
RESEND_API_KEY
```

### **Step 2: Add Gmail SMTP Variables**
```
✅ ADD these variables:

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-gmail-address@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password-here
DEFAULT_FROM_EMAIL=your-gmail-address@gmail.com
```

⚠️ **IMPORTANT:** The `EMAIL_HOST_PASSWORD` above is your Gmail App Password (16 characters), NOT your regular Gmail password.

---

## 🔍 **Expected Results After Configuration**

### ✅ **What Should Work:**
1. **User Registration:**
   - User fills registration form
   - OTP email sent via Gmail SMTP  
   - User redirected to `/verify-account/` (NOT login page)
   - User enters OTP code and account is verified

2. **Email Logging:**
   - All email attempts logged to Railway console
   - Success/failure clearly indicated
   - SMTP connection details logged

3. **Error Handling:**
   - Clear error messages if email fails
   - Detailed logging for debugging
   - User-friendly error messages in production

### 🚨 **Current Problems Fixed:**
1. ✅ **Email Backend:** Switched from Resend to Gmail SMTP
2. ✅ **Redirect Flow:** Fixed registration redirect to go to verify-account page
3. ✅ **Error Logging:** Added comprehensive logging for email issues
4. ✅ **Production Handling:** Better error messages for production environment

---

## 🧪 **Testing Instructions**

After configuring the variables:

1. **Wait for Railway to restart** (30-60 seconds)
2. **Visit:** https://web-production-53602.up.railway.app/profiles/register/
3. **Register a test user** with your email
4. **Check Railway logs** for email sending confirmation
5. **Check your Gmail inbox** for OTP code
6. **Verify:** You should be redirected to verify-account page, NOT login

---

## 🔧 **Troubleshooting**

### **If emails still don't work:**
1. **Check Railway logs** for SMTP connection errors
2. **Verify Gmail App Password** matches your generated 16-character password
3. **Confirm 2FA is enabled** on Gmail account
4. **Try regenerating** the Gmail App Password if needed

### **If redirect still goes to login:**
- This should be fixed with the code changes
- Check Railway logs for "Redirecting to verify_account page" message

---

## 📝 **Code Changes Made**

1. **settings.py:** Prioritized Gmail SMTP over Resend
2. **otp.py:** Enhanced logging for email send attempts  
3. **views.py:** Better error handling and redirect logging
4. **All changes** committed and ready for Railway deployment

---

## ⚡ **Quick Summary**

**BEFORE:** Resend API not working, users redirected to login
**AFTER:** Gmail SMTP working, users redirected to OTP verification

**ACTION:** Configure the Gmail variables above in Railway → Variables