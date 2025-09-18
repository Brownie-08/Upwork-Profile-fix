# 🔒 CSRF Fix for Render Deployment

## Current Issues Fixed

### ✅ 1. CSRF Trusted Origins
**Problem**: 403 Forbidden on document uploads and form submissions
**Fix**: Updated `CSRF_TRUSTED_ORIGINS` in settings.py to include Render domains

### ✅ 2. WebSocket 404 Errors  
**Problem**: Frontend polling `/ws/notifications/` causing 404 errors
**Fix**: Temporarily disabled WebSocket connections until Django Channels is properly configured

## 🚀 Updated Environment Variables for Render

Add this additional variable to your Render environment:

```bash
RENDER_EXTERNAL_HOSTNAME=your-app-name.onrender.com
```

This will automatically be added to `CSRF_TRUSTED_ORIGINS` for proper CSRF token validation.

## 🔧 Technical Changes Made

1. **Settings.py Updates**:
   - Updated production environment detection for Render
   - Fixed CSRF configuration for `.onrender.com` domains
   - Added automatic hostname detection from `RENDER_EXTERNAL_HOSTNAME`

2. **JavaScript Updates**:
   - Temporarily disabled WebSocket notifications (prevents 404 errors)
   - Enhanced CSRF token handling in upload forms
   - Better error handling for AJAX requests

3. **Static Files Updates**:
   - Updated media configuration for Render instead of Railway

## 📝 Next Steps After Deployment

1. **Set Environment Variables** in Render dashboard:
   - Add `RENDER_EXTERNAL_HOSTNAME=your-actual-app-name.onrender.com`
   - Replace `your-actual-app-name` with your real Render service name

2. **Test Critical Functions**:
   - User registration and OTP emails ✅ (Should work)
   - Document uploads (face photo, ID documents) ✅ (Should work now)
   - Add experience forms ✅ (Should work now)
   - File uploads in profile ✅ (Should work now)

## 🔮 Future WebSocket Configuration (Optional)

To re-enable real-time notifications:

1. **Update Render Service Configuration**:
   - Change from WSGI to ASGI application
   - Update start command to use `daphne` instead of `gunicorn`

2. **Environment Variables**:
   ```bash
   # For WebSocket support (future)
   DJANGO_ASGI_APPLICATION=lusitohub.asgi.application
   ```

3. **Start Command** (when ready for WebSockets):
   ```bash
   daphne -b 0.0.0.0 -p $PORT lusitohub.asgi:application
   ```

## ⚡ Quick Verification

After deployment, test these critical workflows:

1. **Register new user** → Should receive OTP email via Gmail
2. **Upload face photo** → Should work without CSRF errors  
3. **Add work experience** → Should save without CSRF errors
4. **Upload ID documents** → Should work without CSRF errors

The 404 WebSocket errors will be gone from the browser console.

---

**Status**: Ready for deployment to Render with CSRF fixes! 🎉