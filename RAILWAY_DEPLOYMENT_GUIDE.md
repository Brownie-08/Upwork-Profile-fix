# Railway Deployment Guide

## Environment Variables to Set in Railway

You need to set these environment variables in your Railway project dashboard:

### Required Environment Variables

1. **Django Core Settings**
   ```
   SECRET_KEY=your-super-secret-production-key-make-it-very-long-and-random
   DEBUG=False
   ALLOWED_HOSTS=.railway.app
   RAILWAY_ENVIRONMENT=production
   ```

2. **Google Maps API Keys**
   ```
   Client_API_KEY=AIzaSyDGcTDai2bvoTT1OYqasDO63BotbnE6eIc
   Server-Side_API_KEY=AIzaSyDGcTDai2bvoTT1OYqasDO63BotbnE6eIc
   ```

3. **MTN Mobile Money Configuration**
   ```
   MOMO_BASE_URL=https://sandbox.momodeveloper.mtn.com
   MOMO_SUBSCRIPTION_KEY=43b433c16c694726819a42a1ad8a6f4b
   MOMO_API_USER_ID=dbec4133-4cda-4081-98bb-f9ea753b609f
   MOMO_API_KEY=71e6f6449bf8406da440cdf583d33d59
   MOMO_CALLBACK_URL=https://your-app-name.railway.app/momo/callback/
   MOMO_PROVIDER_CALLBACK_HOST=https://your-app-name.railway.app
   MOMO_ENVIRONMENT=sandbox
   MOMO_CURRENCY=SZL
   ```

4. **Email Configuration (Optional)**
   ```
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=ncabamatse@gmail.com
   EMAIL_HOST_PASSWORD=sdcijeyzjnvirlgo
   DEFAULT_FROM_EMAIL=ncabamatse@gmail.com
   ```

### Database Configuration

Railway will automatically provide the `DATABASE_URL` environment variable when you add a PostgreSQL database to your project.

## Steps to Fix the 500 Error

1. **Set Environment Variables in Railway Dashboard:**
   - Go to your Railway project dashboard
   - Navigate to the "Variables" tab
   - Add all the environment variables listed above
   - Replace `your-app-name` with your actual Railway app name in URLs

2. **Generate a Secure SECRET_KEY:**
   ```python
   # Run this in Python to generate a secure key
   import secrets
   print(secrets.token_urlsafe(50))
   ```

3. **Add PostgreSQL Database:**
   - In Railway dashboard, click "New" → "Database" → "PostgreSQL"
   - Railway will automatically set the DATABASE_URL

4. **Deploy Again:**
   - Your nixpacks.toml now includes:
     - Database migrations
     - Static file collection
     - Proper build process

## Common Issues and Solutions

### Issue 1: SECRET_KEY Missing
- **Error:** `django.core.exceptions.ImproperlyConfigured: The SECRET_KEY setting must not be empty`
- **Solution:** Set SECRET_KEY environment variable in Railway

### Issue 2: Database Connection Error
- **Error:** `django.db.utils.OperationalError: FATAL: database does not exist`
- **Solution:** Ensure PostgreSQL database is added and DATABASE_URL is set

### Issue 3: Static Files Not Found
- **Error:** Static files (CSS/JS) not loading
- **Solution:** nixpacks.toml now includes `collectstatic` command

### Issue 4: Allowed Hosts Error
- **Error:** `DisallowedHost at / Invalid HTTP_HOST header`
- **Solution:** Set ALLOWED_HOSTS=.railway.app in environment variables

## After Setting Environment Variables

1. Commit and push your code changes
2. Railway will automatically redeploy
3. Check the deployment logs for any remaining errors
4. Visit your Railway app URL to test

## Checking Logs

To debug any remaining issues:
1. Go to Railway dashboard
2. Click on your service
3. Go to "Deployments" tab
4. Click on the latest deployment
5. Check the build and runtime logs