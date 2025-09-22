# 🔧 Admin User Creation Troubleshooting

## 🚨 If Admin Creation Still Not Working

### Step 1: Check Railway Environment Variables

**Go to Railway Dashboard → Your Service → Variables**

Make sure these are **EXACTLY** set:

```bash
RAILWAY_ENVIRONMENT=production
ADMIN_USERNAME=admin
ADMIN_EMAIL=your-email@gmail.com
ADMIN_PASSWORD=your-secure-password
```

### Step 2: Check Railway Deployment Logs

**Go to Railway Dashboard → Your Service → Deployments → Latest → View Logs**

Look for these messages during deployment:
```
🔍 Starting admin user creation process...
Railway Environment: production
Found ADMIN_USERNAME: admin
Found ADMIN_EMAIL: your-email@gmail.com
Found ADMIN_PASSWORD: ✅ SET
```

## 🛠️ Common Issues & Solutions

### Issue 1: "This command should only be run in production"
**Problem**: `RAILWAY_ENVIRONMENT` variable not set
**Solution**: Add `RAILWAY_ENVIRONMENT=production` to Railway variables

### Issue 2: "Missing required environment variables"
**Problem**: Admin credentials not set properly
**Solution**: Double-check variable names (case-sensitive):
- `ADMIN_USERNAME`
- `ADMIN_EMAIL` 
- `ADMIN_PASSWORD`

### Issue 3: Command not running at all
**Problem**: Command not in nixpacks.toml or build failed
**Solution**: Check deployment logs for build errors

### Issue 4: Database connection issues
**Problem**: Admin creation runs before database is ready
**Solution**: Already handled by running after migrations

## 🚀 Manual Admin Creation Methods

### Method 1: Railway Web Terminal
1. Go to Railway Dashboard
2. Your Service → Settings → "Connect" (web terminal)
3. Run: `python manage.py createsuperuser`
4. Follow prompts

### Method 2: Using Our Manual Script
1. In Railway web terminal, run:
```bash
python create_admin_manual.py
```

### Method 3: Django Shell Method
1. In Railway web terminal:
```bash
python manage.py shell
```
2. Then run:
```python
from django.contrib.auth import get_user_model
User = get_user_model()

# Replace with your actual credentials
username = "admin"
email = "your-email@gmail.com"
password = "your-secure-password"

# Check if user exists
if User.objects.filter(username=username).exists():
    print(f"User '{username}' already exists")
    user = User.objects.get(username=username)
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print("Updated existing user with admin privileges")
else:
    user = User.objects.create_superuser(username, email, password)
    print(f"Created superuser: {username}")

exit()
```

## 🔍 Debugging Steps

### 1. Check if Railway Variables are Set
In Railway terminal:
```bash
echo $RAILWAY_ENVIRONMENT
echo $ADMIN_USERNAME
echo $ADMIN_EMAIL
# Don't echo password for security
```

### 2. Test Management Command Manually
```bash
python manage.py create_production_superuser
```

### 3. Check Database Tables
```bash
python manage.py shell
```
```python
from django.contrib.auth import get_user_model
User = get_user_model()
print(f"Total users: {User.objects.count()}")
print(f"Superusers: {User.objects.filter(is_superuser=True).count()}")
for user in User.objects.filter(is_superuser=True):
    print(f"Superuser: {user.username} - {user.email}")
```

### 4. Force Database Migration
If tables don't exist:
```bash
python manage.py migrate --noinput
python manage.py migrate auth
python manage.py migrate contenttypes
```

## 📋 Current Environment Check

Run this in Railway terminal to diagnose:

```bash
echo "=== ENVIRONMENT CHECK ==="
echo "Railway Environment: $RAILWAY_ENVIRONMENT"
echo "Admin Username: $ADMIN_USERNAME"
echo "Admin Email: $ADMIN_EMAIL"
echo "Password Set: $(if [ -n "$ADMIN_PASSWORD" ]; then echo 'YES'; else echo 'NO'; fi)"
echo
echo "=== DATABASE CHECK ==="
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
print(f'Database accessible: True')
print(f'User table exists: {User._meta.db_table}')
print(f'Total users: {User.objects.count()}')
print(f'Superusers: {User.objects.filter(is_superuser=True).count()}')
"
```

## ✅ Verification Steps

After creating admin user:

1. **Go to**: `https://your-railway-app.railway.app/admin/`
2. **Login with your credentials**
3. **You should see the Django admin dashboard**

## 🆘 Emergency Admin Access

If all else fails, you can create a temporary admin via direct database access:

```bash
python manage.py shell
```
```python
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

User = get_user_model()

# Emergency admin - CHANGE PASSWORD IMMEDIATELY AFTER LOGIN
User.objects.create(
    username='emergency_admin',
    email='admin@lusitohub.com',
    password=make_password('EMERGENCY123!'),
    is_staff=True,
    is_superuser=True,
    is_active=True
)
print("Emergency admin created: emergency_admin / EMERGENCY123!")
print("⚠️  CHANGE PASSWORD IMMEDIATELY AFTER LOGIN!")
```

## 📞 Next Steps

1. **Try Method 1 first** (Railway web terminal)
2. **If that fails, use Method 2** (manual script)
3. **If still failing, use Method 3** (Django shell)
4. **Share the deployment logs** so we can see exactly what's happening