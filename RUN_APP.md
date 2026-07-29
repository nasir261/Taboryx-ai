# RUN THE APP - Step by Step

## ✅ Before You Start
Make sure Python 3.11+ is installed:
```powershell
python --version
```

Should show: `Python 3.11.0` or higher

**If Python is not installed:**
1. Go to https://www.python.org/downloads/
2. Click "Download Python 3.12"
3. Run installer and check "Add Python to PATH"
4. Restart PowerShell
5. Try `python --version` again

---

## 🚀 Run These 5 Commands (Copy & Paste)

### Command 1: Navigate to project
```powershell
cd c:\Users\Home\Documents\project.inventory
```

### Command 2: Create virtual environment
```powershell
python -m venv venv
```

### Command 3: Activate virtual environment
```powershell
.\venv\Scripts\Activate.ps1
```

**If you get an error about execution policy:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then run Command 3 again.

**After this, your prompt should show `(venv)` at the beginning**

### Command 4: Install dependencies
```powershell
pip install -r requirements.txt
```

Wait for it to finish (2-3 minutes). You'll see lots of package names installing.

### Command 5: Run the application
```powershell
python -m src.app
```

**The login window should appear!**

---

## 🔐 Login Credentials
When the window opens:
- **Username:** `admin`
- **Password:** `password123`

Then click "Login"

---

## 📸 What You'll See

### 1. Login Window
- Professional login form
- Enter admin / password123

### 2. Dashboard
Shows:
- Total items in inventory
- Total stock value
- Low stock items count
- Expired items count
- Recent stock movements

### 3. Navigation
Three buttons to click:
- **Dashboard** - Shows metrics
- **Inventory** - Lists items
- **Stock Movements** - Shows recent changes
- **Logout** - Exit app

---

## 🎯 What to Try

1. **Explore the Dashboard**
   - Click the three navigation buttons
   - See what data is displayed

2. **Check the Inventory View**
   - Should show empty (no items added yet)
   - This is normal for a fresh installation

3. **Review the Database**
   - File located at: `data/Taboryx.db`
   - Can view with SQLite browser if you want

---

## ✅ Success Indicators

- ✅ Login window appears
- ✅ Can login with admin / password123
- ✅ Dashboard shows with statistics
- ✅ No error messages
- ✅ Can click buttons and navigate

---

## 🐛 Troubleshooting

### "python not found"
- Install Python from https://www.python.org/downloads/
- Check "Add Python to PATH"

### "(venv) doesn't appear in prompt"
- Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Then: `.\venv\Scripts\Activate.ps1`

### "No module named customtkinter"
- Make sure you ran: `pip install -r requirements.txt`
- Make sure venv is active (shows `(venv)` in prompt)

### Nothing happens when I run the app
- Check: `Get-Content .\logs\app.log`
- Make sure you're in the project directory

---

## 💡 Helpful Commands

```powershell
# Check if virtual environment is active
# (you should see (venv) in your prompt)

# Stop the application
# Press Ctrl+C in PowerShell

# Run again next time
# Just run: python -m src.app

# Deactivate virtual environment
# Type: deactivate
```

---

## 🎉 First Time Setup Complete!

After you run the app and see it working, you can:

1. **Close the app** - Press Ctrl+C or click close button
2. **Next time you run:**
   ```powershell
   cd c:\Users\Home\Documents\project.inventory
   .\venv\Scripts\Activate.ps1
   python -m src.app
   ```

3. **Eventually build features:**
   - Add new inventory items
   - Create stock movements
   - Generate reports
   - See DEVELOPMENT.md for coding guide

---

## 📞 Need Help?

- **Setup stuck?** → Check troubleshooting above
- **App won't start?** → Check logs: `Get-Content .\logs\app.log`
- **Want to code?** → Read DEVELOPMENT.md
- **Questions?** → Check README.md or QUICK_START.md

---

## ⚡ One-Click Start (Desktop + Mobile API)

Use [START_Taboryx_ONE_CLICK.bat](C:/Users/Home/Documents/project.inventory/START_Taboryx_ONE_CLICK.bat)

1. Open [START_Taboryx_ONE_CLICK.bat](C:/Users/Home/Documents/project.inventory/START_Taboryx_ONE_CLICK.bat)
2. It will:
   - start the mobile API server on port 8000 (if not already running)
   - launch the desktop app
3. On iPhone (same Wi-Fi), open:
   - `http://<your-pc-ip>:8000/`

Tip: Right-click [START_Taboryx_ONE_CLICK.bat](C:/Users/Home/Documents/project.inventory/START_Taboryx_ONE_CLICK.bat) and create a desktop shortcut for daily use.
