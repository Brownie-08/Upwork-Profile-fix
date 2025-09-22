# 🔧 Railway Environment Variables Fix

## 🚨 URGENT: Remove Quotes from Railway Variables

Your current Railway environment variables have quotes around them, which is causing issues:

### ❌ **WRONG** (Current):
```
ADMIN_USERNAME="admin"
ADMIN_EMAIL="admin@gmail.com"
ADMIN_PASSWORD="hW3k5bvshp@EUW3i"
```

### ✅ **CORRECT** (Fix):
```
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@gmail.com
ADMIN_PASSWORD=hW3k5bvshp@EUW3i
```

## 🛠️ How to Fix Railway Variables

1. **Go to Railway Dashboard**
2. **Your Service → Variables tab**
3. **Edit each variable and remove the quotes:**
   - Click on `ADMIN_USERNAME`
   - Change from `"admin"` to `admin`
   - Click on `ADMIN_EMAIL`
   - Change from `"admin@gmail.com"` to `admin@gmail.com`
   - Click on `ADMIN_PASSWORD`
   - Change from `"hW3k5bvshp@EUW3i"` to `hW3k5bvshp@EUW3i`

4. **Also ensure you have:**
   ```
   RAILWAY_ENVIRONMENT=production
   ```

## 📋 Complete Variable List

Set these **EXACTLY** in Railway (no quotes):

```bash
# Required for deployment
RAILWAY_ENVIRONMENT=production

# Admin credentials (no quotes!)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@gmail.com
ADMIN_PASSWORD=hW3k5bvshp@EUW3i

# Core Django settings
SECRET_KEY=7DGq-UMI2TINdQJPsCdnuZYb4fn57UUrhl_M_qppLWbbBxdnHdADEduv8RV7Yz-1l_w
DEBUG=False
ALLOWED_HOSTS=.railway.app

# Your API keys (replace with actual values)
Client_API_KEY=your-google-maps-client-key
Server-Side_API_KEY=your-google-maps-server-key

# MTN Mobile Money (replace with actual values)
MOMO_BASE_URL=https://sandbox.momodeveloper.mtn.com
MOMO_SUBSCRIPTION_KEY=your-actual-subscription-key
MOMO_API_USER_ID=your-actual-user-id
MOMO_API_KEY=your-actual-api-key
MOMO_CALLBACK_URL=https://your-railway-app.railway.app/momo/callback/
MOMO_PROVIDER_CALLBACK_HOST=https://your-railway-app.railway.app
MOMO_ENVIRONMENT=sandbox
MOMO_CURRENCY=SZL
```

## 🚀 After Fixing Variables

1. **Save all variables in Railway**
2. **Railway will auto-redeploy**
3. **Check deployment logs for:**
   ```
   🔍 Starting admin user creation process...
   Railway Environment: production
   Found ADMIN_USERNAME: admin
   Found ADMIN_EMAIL: admin@gmail.com
   Found ADMIN_PASSWORD: ✅ SET
   ✅ Successfully created superuser "admin"
   ```

## 🧪 Testing Registration After Fix

1. **Try registering a new user**
2. **If email fails, you should see:**
   ```
   📧 FALLBACK OTP for user@email.com: 123456
   📧 Email failed (Network is unreachable), using console fallback
   ```
3. **Registration should complete successfully**
4. **Use OTP from Railway logs to verify account**

## ⚡ Quick Fix Commands

If admin still doesn't work after fixing variables, run in Railway terminal:

```bash
# Quick admin creation
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if User.objects.filter(username='admin').exists():
    user = User.objects.get(username='admin')
    user.set_password('hW3k5bvshp@EUW3i')
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print('Updated admin user')
else:
    User.objects.create_superuser('admin', 'admin@gmail.com', 'hW3k5bvshp@EUW3i')
    print('Created admin user')
"
```

## 🎯 Expected Results

After fixing the variables:

✅ **Admin user will be created automatically**  
✅ **Registration will work with email fallback**  
✅ **OTP codes will appear in Railway logs**  
✅ **No more registration failures**

## 🔍 Verification

Admin URL: `https://your-railway-app.railway.app/admin/`  
Login: `admin` / `hW3k5bvshp@EUW3i`