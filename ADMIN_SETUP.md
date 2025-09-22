# 🔐 Production Admin Setup Guide

## 🚀 Automatic Admin User Creation

Your deployment can automatically create a superuser, but **REQUIRES** environment variables for security.

### 🔒 REQUIRED Environment Variables

**You MUST set these environment variables in Railway** for admin creation:

```bash
ADMIN_USERNAME=your-chosen-username
ADMIN_EMAIL=your-email@domain.com
ADMIN_PASSWORD=your-secure-password
```

### ⚠️ SECURITY: No Default Credentials!

```bash
ADMIN_USERNAME=your-preferred-username
ADMIN_EMAIL=your-email@domain.com
ADMIN_PASSWORD=your-secure-password
```

## 🌐 Accessing the Admin Panel

1. **Go to your Railway app URL**
2. **Add `/admin/` to the URL**
   - Example: `https://your-app-name.railway.app/admin/`
3. **Login with the credentials above**
4. **IMMEDIATELY change the password** (Admin → Users → admin → Change password)

## 🔧 Manual Admin Creation (Alternative Method)

If the automatic creation doesn't work, you can create an admin manually:

### Option 1: Railway Web Terminal
1. Go to Railway dashboard
2. Open your service
3. Go to Settings → Console/Terminal
4. Run: `python manage.py createsuperuser`
5. Follow the prompts

### Option 2: Railway CLI
```bash
railway login
railway link your-project-id
railway run python manage.py createsuperuser
```

## 🛡️ Security Best Practices

### Immediately After First Login:
1. **Change the default password**
2. **Update the email address**
3. **Create additional admin users if needed**
4. **Consider renaming the default 'admin' username**

### Ongoing Security:
1. **Use strong, unique passwords**
2. **Enable 2FA if available**
3. **Regularly audit admin users**
4. **Remove unused admin accounts**
5. **Monitor admin login logs**

## 📍 Admin Panel Features

Your Django admin panel includes:
- **User Management**: Create/edit users and permissions
- **Content Management**: Manage all app models
- **Jazzmin Interface**: Enhanced admin UI with dashboard
- **Transport System**: Manage transport requests, bids, etc.
- **Profile Management**: Handle user profiles and documents
- **Wallet System**: Monitor transactions and wallets

## 🎨 Admin Panel Customization

The admin panel uses **Jazzmin** for enhanced UI:
- Modern, responsive interface
- Dashboard widgets
- Custom navigation
- Brand customization

## 🚨 Troubleshooting

### Admin user not created automatically:
```bash
# Check Railway logs for errors
# If needed, create manually via Railway terminal:
python manage.py createsuperuser
```

### Can't access /admin/:
- Verify the URL includes `/admin/` at the end
- Check that the app is fully deployed
- Ensure migrations completed successfully

### Login not working:
- Double-check username and password
- Try the manual creation method
- Check Railway environment variables

## 🎯 Next Steps After Admin Setup

1. **Login and change default password**
2. **Create additional admin users if needed**  
3. **Configure app-specific settings**
4. **Set up user roles and permissions**
5. **Test all admin functionality**

---

**Admin URL**: `https://your-railway-app-name.railway.app/admin/`

**Admin Credentials**: Set via Railway environment variables:
- `ADMIN_USERNAME`
- `ADMIN_EMAIL` 
- `ADMIN_PASSWORD`
