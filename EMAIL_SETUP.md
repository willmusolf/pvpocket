# 📧 Email Setup for Support Tickets

Your support ticket email system is ready! Just need to install Flask-Mail and add your Gmail App Password.

## 🚀 Quick Setup

### 1. Install Flask-Mail in your virtual environment
```bash
pip install Flask-Mail==0.10.0
```

### 2. Get Gmail App Password
1. Go to [myaccount.google.com](https://myaccount.google.com) → Security
2. Enable 2-Step Verification (if not already enabled)
3. Go to 2-Step Verification → App passwords
4. Generate → Mail → Other → "PvPocket Support"
5. Copy the 16-character password (like `abcd efgh ijkl mnop`)

### 3. Update the password in Google Secret Manager
```bash
gcloud secrets versions add mail-password --data-file=<(echo "YOUR-APP-PASSWORD-HERE") --project=pvpocket-dd286
```

Replace `YOUR-APP-PASSWORD-HERE` with your actual 16-character Gmail App Password.

### 4. Test the system
```bash
python run.py
```

Go to: `http://localhost:5001/admin/dashboard`
Click the **"Test Email"** button in the Support section.

## 🔐 Security Features

✅ **No real password used** - Only Gmail App Passwords  
✅ **Google Secret Manager** - Enterprise-grade encryption  
✅ **No credentials in code** - Completely secure  
✅ **Auto-deploy ready** - Works in production automatically  

## 🎯 How It Works

1. **User submits support ticket** → Stored in Firestore
2. **Admin clicks "Quick Reply"** → Opens reply form
3. **Admin sends reply** → Email sent + stored in ticket
4. **User receives email** → Professional formatted reply
5. **Admin sees reply history** → In resolved/closed tickets

## ✨ What You'll See

- 🟢 **Green checkmark**: Email sent successfully
- 🟡 **Yellow warning**: Email failed (with error details)  
- 📧 **Admin reply sections**: In resolved/closed tickets
- 🧪 **"Test Email" button**: In admin dashboard

Your support ticket system is now enterprise-grade secure! 🎉