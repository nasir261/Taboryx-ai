# 🚀 GET THE APP RUNNING - CHECKLIST

## Pre-Flight Check
- [ ] Read this entire checklist
- [ ] Open PowerShell on your computer
- [ ] Navigate to: `c:\Users\Home\Documents\project.inventory`

---

## Installation Checklist

### ✅ Step 1: Verify Python (2 minutes)
```powershell
python --version
```
- [ ] Shows `Python 3.11` or higher
- [ ] If not: Install from https://www.python.org/downloads/

### ✅ Step 2: Navigate to Project (1 minute)
```powershell
cd c:\Users\Home\Documents\project.inventory
```
- [ ] You're now in the project folder
- [ ] Can see files like README.md, requirements.txt

### ✅ Step 3: Create Virtual Environment (2 minutes)
```powershell
python -m venv venv
```
- [ ] Completed without errors
- [ ] New `venv` folder created
- [ ] (If venv already exists, that's fine - skip this)

### ✅ Step 4: Activate Virtual Environment (1 minute)
```powershell
.\venv\Scripts\Activate.ps1
```
- [ ] Prompt now shows `(venv)` at the beginning
- [ ] If error: Run this first, then retry:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### ✅ Step 5: Install Packages (3-5 minutes)
```powershell
pip install -r requirements.txt
```
- [ ] See many package names installing
- [ ] Ends with "Successfully installed [packages]"
- [ ] No error messages at the end

### ✅ Step 6: Run the App (30 seconds)
```powershell
python -m src.app
```
- [ ] A window appears (login window)
- [ ] Window is labeled "MediStock AI v0.1.0"

---

## First Run Checklist

### 📝 Login
- [ ] Username field visible
- [ ] Password field visible
- [ ] Login button visible
- [ ] Enter: `admin`
- [ ] Enter: `password123`
- [ ] Click: Login

### 🎯 Dashboard
- [ ] Dashboard loads successfully
- [ ] Welcome message shows your name
- [ ] Statistics displayed:
  - [ ] Total Items
  - [ ] Total Stock Value
  - [ ] Low Stock Items
  - [ ] Expired Items
- [ ] Navigation buttons visible:
  - [ ] Dashboard
  - [ ] Inventory
  - [ ] Stock Movements
  - [ ] Logout

### 🧪 Test Navigation
- [ ] Click "Inventory" - Lists items (should be empty)
- [ ] Click "Stock Movements" - Lists movements (should be empty)
- [ ] Click "Dashboard" - Returns to main view
- [ ] Click "Logout" - Returns to login

---

## ✅ Success Criteria

If ALL of these are true, the app is working:

- ✅ Python 3.11+ installed
- ✅ Virtual environment created and activated
- ✅ All packages installed successfully
- ✅ Login window appears when running app
- ✅ Can login with admin/password123
- ✅ Dashboard displays with data
- ✅ Can navigate between pages
- ✅ Logout button works
- ✅ No error messages in console

---

## 🎉 Congratulations!

**The app is working!** You now have:

1. ✅ Running application
2. ✅ Database initialized
3. ✅ User authentication working
4. ✅ Dashboard functional
5. ✅ Ready for next phase

---

## 📋 What's Next?

### Option A: Explore the Current Features (15 minutes)
1. Login and navigate around
2. Check all the views
3. Read what's displayed
4. Understand the current functionality

### Option B: Develop New Features (1-2 hours)
Read: `DEVELOPMENT.md`
Tasks:
1. Build Inventory CRUD UI (add/edit/delete items)
2. Add barcode scanner support
3. Create stock movement interface

### Option C: Customize the System (30 minutes)
1. Add your own user roles
2. Change item categories
3. Modify stock warning levels
4. See: `src/config.py`

### Option D: Learn the Code (1 hour)
1. Read: `DEVELOPMENT.md`
2. Review: `src/services/auth_service.py`
3. Review: `src/services/inventory_service.py`
4. Understand the architecture

---

## 🛑 Common Issues

### "python not found"
```powershell
# Install from https://www.python.org/downloads/
# Choose Python 3.11 or 3.12
# Check: "Add Python to PATH"
# Restart PowerShell
python --version
```

### "(venv) not in prompt"
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

### "No module named customtkinter"
```powershell
# Make sure venv is active (shows (venv) in prompt)
pip install -r requirements.txt
```

### "Application won't start"
```powershell
# Check logs
Get-Content .\logs\app.log -Tail 50
```

### "Port already in use" or "Connection refused"
```powershell
# Close other instances of the app
# This app runs locally - no network ports needed
# Just restart the command
```

---

## 📞 Help Resources

| Resource | What It Has |
|----------|------------|
| **RUN_APP.md** | Instructions to run the app |
| **QUICK_START.md** | Quick reference guide |
| **INSTALLATION.md** | Detailed setup help |
| **DEVELOPMENT.md** | How to develop features |
| **README.md** | Project overview |
| **logs/app.log** | Error messages |

---

## ✨ Timeline

| Step | Time |
|------|------|
| Verify Python | 2 min |
| Navigate to project | 1 min |
| Create venv | 2 min |
| Activate venv | 1 min |
| Install packages | 3-5 min |
| Run app | <1 min |
| **Total** | **~15 minutes** |

---

## 🎯 Final Checklist Before You Go

- [ ] Python 3.11+ installed and verified
- [ ] In project directory: `c:\Users\Home\Documents\project.inventory`
- [ ] Virtual environment created
- [ ] Virtual environment activated (see (venv) in prompt)
- [ ] Packages installed (pip install -r requirements.txt)
- [ ] App runs: `python -m src.app`
- [ ] Can login with admin/password123
- [ ] Dashboard displays correctly
- [ ] Can navigate between pages
- [ ] Understand what's working and what's next

---

**🎉 YOU'RE READY TO GO!**

Run the app and enjoy! 🚀
