# Render Deployment Guide for LusitoHub Django App

## 🚀 Render Deployment Steps

### 1. Create a Render Account
- Go to [render.com](https://render.com)
- Sign up or log in with your GitHub account

### 2. Create a New Web Service
1. Click "New +" > "Web Service"
2. Connect your GitHub repository: `https://github.com/Brownie-08/Updated-Car-Rental`
3. Configure the service:
   - **Name**: `lusitohub-app` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn lusitohub.wsgi:application`
   - **Instance Type**: `Starter` (free tier)

### 3. Add PostgreSQL Database
1. Go to Dashboard > "New +" > "PostgreSQL"
2. Choose:
   - **Name**: `lusitohub-db`
   - **Database**: `lusitohub`
   - **User**: `lusitohub_user`
   - **Region**: Same as your web service
   - **PostgreSQL Version**: 15 (latest)
   - **Plan**: `Starter` (free tier - $0/month)

3. After creation, copy the **External Database URL** from the database dashboard

### 4. Configure Environment Variables

Go to your web service > Environment tab and add these variables:

#### 🔧 Core Django Settings
```
DEBUG=False
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
DJANGO_SETTINGS_MODULE=lusitohub.settings
ALLOWED_HOSTS=.onrender.com,yourdomain.com
```

#### 🗄️ Database Configuration
```
DATABASE_URL=postgresql://username:password@host:port/database
```
*Copy this from your PostgreSQL service on Render*

#### 📧 Gmail SMTP Configuration (CRITICAL for OTP emails)
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-gmail-address@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password-here
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=your-gmail-address@gmail.com
EMAIL_TIMEOUT=30
```

#### 👤 Admin User (Optional - for automatic superuser creation)
```
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@lusitohub.com
DJANGO_SUPERUSER_PASSWORD=your-secure-password
```

#### 🗺️ Google Maps API Keys
```
Server-Side_API_KEY=your-google-maps-server-api-key
Client_API_KEY=your-google-maps-client-api-key
```

#### 💳 MTN MoMo Configuration (if using mobile payments)
```
MOMO_BASE_URL=https://sandbox.momodeveloper.mtn.com
MOMO_SUBSCRIPTION_KEY=your-momo-subscription-key
MOMO_API_USER_ID=your-momo-api-user-id
MOMO_API_KEY=your-momo-api-key
MOMO_CALLBACK_URL=https://your-render-url.onrender.com/momo/callback/
MOMO_PROVIDER_CALLBACK_HOST=https://your-render-url.onrender.com
MOMO_ENVIRONMENT=sandbox
MOMO_CURRENCY=SZL
```

#### 🌍 Site Configuration
```
SITE_URL=https://your-app-name.onrender.com
MEDIA_URL=/media/
```

## 🔧 Build Process

Render will automatically run `./build.sh` which:
1. ✅ Installs Python dependencies
2. ✅ Runs database migrations
3. ✅ Collects static files
4. ✅ Creates superuser (if credentials provided)

## 📧 Email Configuration Verification

After deployment, check the logs to ensure Gmail SMTP is working:
- Look for: `"📧 Production Gmail SMTP configured"`
- Verify: `"✅ Gmail SMTP configured for your-gmail-address@gmail.com"`

## 🎯 Post-Deployment Checklist

1. **Verify deployment**: Visit your Render app URL
2. **Test registration**: Create a new user account
3. **Check OTP emails**: Ensure OTP codes are sent via Gmail
4. **Admin access**: Go to `/admin/` and log in
5. **Static files**: Verify CSS/JS loads correctly

## 🆘 Troubleshooting

### Email Issues
- Check environment variables are set correctly
- Verify Gmail app password is valid
- Check Render logs for email errors

### Database Issues
- Ensure DATABASE_URL is correctly copied from PostgreSQL service
- Check database connection in Render logs

### Static Files Issues
- Verify `STATIC_ROOT` and `STATIC_URL` settings
- Check if `collectstatic` ran successfully in build logs

## 🔄 Updating Your App

1. Push changes to your GitHub repository
2. Render will automatically rebuild and deploy
3. Check deployment logs for any errors

## 💡 Benefits of Render over Railway

- ✅ Better SMTP support (no email delivery issues)
- ✅ Free PostgreSQL database included
- ✅ Automatic SSL certificates
- ✅ Better build logs and debugging
- ✅ More reliable deployments
- ✅ Built-in domain management

## 🎉 Your App Will Be Live At:
`https://your-service-name.onrender.com`

---

**Note**: Replace `your-service-name` with the actual name you choose for your Render service.