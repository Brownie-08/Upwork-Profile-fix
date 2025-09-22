# 🚀 Final Environment Variables for Render Deployment

## Your Deployed App: https://upwork-profile-fix.onrender.com

### 🔒 **Critical CSRF Fix Variable**

**Add this to your Render environment variables immediately:**

```bash
RENDER_EXTERNAL_HOSTNAME=upwork-profile-fix.onrender.com
```

### 📋 **Complete Environment Variables List**

Copy and paste these exact values into your Render service environment:

| Variable Name | Value |
|---------------|--------|
| `DEBUG` | `False` |
| `SECRET_KEY` | `nl%h2phh-8` |
| `DJANGO_SETTINGS_MODULE` | `lusitohub.settings` |
| `ALLOWED_HOSTS` | `.onrender.com,127.0.0.1,localhost` |
| `RENDER_EXTERNAL_HOSTNAME` | `upwork-profile-fix.onrender.com` |
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | `udohpeterbrown@gmail.com` |
| `EMAIL_HOST_PASSWORD` | `fdachcuqlibcctsb` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_USE_SSL` | `False` |
| `DEFAULT_FROM_EMAIL` | `udohpeterbrown@gmail.com` |
| `EMAIL_TIMEOUT` | `30` |
| `Client_API_KEY` | `AIzaSyDGcTDai2bvoTT1OYqasDO63BotbnE6eIc` |
| `Server-Side_API_KEY` | `AIzaSyDGcTDai2bvoTT1OYqasDO63BotbnE6eIc` |
| `MOMO_BASE_URL` | `https://sandbox.momodeveloper.mtn.com` |
| `MOMO_SUBSCRIPTION_KEY` | `43b433c16c694726819a42a1ad8a6f4b` |
| `MOMO_API_USER_ID` | `dbec4133-4cda-4081-98bb-f9ea753b609f` |
| `MOMO_API_KEY` | `71e6f6449bf8406da440cdf583d33d59` |
| `MOMO_ENVIRONMENT` | `sandbox` |
| `MOMO_CURRENCY` | `SZL` |
| `MOMO_CALLBACK_URL` | `https://upwork-profile-fix.onrender.com/momo/callback/` |
| `MOMO_PROVIDER_CALLBACK_HOST` | `https://upwork-profile-fix.onrender.com` |
| `DJANGO_SUPERUSER_USERNAME` | `admin` |
| `DJANGO_SUPERUSER_EMAIL` | `admin@gmail.com` |
| `DJANGO_SUPERUSER_PASSWORD` | `hW3k5bvshp@EUW3i` |
| `SITE_URL` | `https://upwork-profile-fix.onrender.com` |
| `MEDIA_URL` | `/media/` |

### 📁 **Cloudinary Media Storage (NEW - CRITICAL)**

| Variable Name | Value |
|---------------|--------|
| `CLOUDINARY_CLOUD_NAME` | `de9i7id2b` |
| `CLOUDINARY_API_KEY` | `547248818221456` |
| `CLOUDINARY_API_SECRET` | `611drBROvgh5Bkip4HZYaLRoddI` |

## 🔧 **How CSRF Will Now Work**

1. **Your domain** `https://upwork-profile-fix.onrender.com` is now explicitly trusted
2. **CSRF cookies** will be set with `Secure=True` for HTTPS
3. **Frontend JavaScript** will automatically include CSRF tokens in uploads
4. **File uploads** and **experience forms** will work without 403 errors

## ⚡ **Immediate Steps**

1. **Go to your Render dashboard**
2. **Add the environment variable**: `RENDER_EXTERNAL_HOSTNAME=upwork-profile-fix.onrender.com`
3. **Redeploy** your service (should happen automatically)
4. **Test** document uploads and experience forms

## 🎯 **Test These After Setting Environment Variables**

✅ **User Registration** → OTP emails should work  
✅ **Upload Face Photo** → Should work without CSRF errors  
✅ **Add Work Experience** → Should save successfully  
✅ **Upload ID Documents** → Should work without 403 errors  
✅ **Upload Profile Files** → Should work without CSRF errors  
✅ **Portfolio Images** → Should persist across redeploys (Cloudinary)
✅ **Profile Pictures** → Should load correctly from Cloudinary CDN

## 📝 **Expected Results**

- No more `403 Forbidden (CSRF token from POST incorrect)` errors
- No more `/ws/notifications/` 404 errors in browser console
- No more `Not Found: /media/portfolio/user_x/images/<filename>.png` errors
- All file uploads and form submissions working properly
- Gmail SMTP emails working for OTP verification
- **Persistent media storage**: Images survive redeploys and load from Cloudinary CDN

---

**Status**: Ready to fix CSRF issues with your specific deployed domain! 🎉