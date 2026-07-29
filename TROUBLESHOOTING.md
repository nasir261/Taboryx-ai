# ⚡ QUICK TROUBLESHOOTING GUIDE

## Problem: "python not found" or "python: The term 'python' is not recognized"

**Solution:**
1. Install Python 3.11+ from https://www.python.org/downloads/
2. **IMPORTANT:** During installation, check the box that says "Add Python to PATH"
3. Click "Install Now"
4. Wait for installation to complete
5. Close and restart PowerShell completely
6. Try `python --version` again

---

## Problem: "cannot load .\venv\Scripts\Activate.ps1"

**Error looks like:**
```
cannot be loaded because running scripts is disabled on this system
```

**Solution:**
1. Run this command:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
2. Type `Y` and press Enter
3. Then run: `.\venv\Scripts\Activate.ps1`

---

## Problem: "No module named 'customtkinter'" or similar

**Solution:**
1. Make sure `(venv)` appears at the beginning of your prompt
2. If not, run: `.\venv\Scripts\Activate.ps1`
3. Re-run: `pip install -r requirements.txt`
4. Wait for all packages to install

---

## Problem: "pip: The term 'pip' is not recognized"

**Solution:**
1. Check Python is installed: `python --version`
2. Try: `python -m pip install -r requirements.txt`
3. If still doesn't work, reinstall Python

---

## Problem: "The system cannot find the path specified"

**Error when running:** `cd c:\Users\Home\Documents\project.inventory`

**Solution:**
1. Make sure the path exists
2. Try typing it manually instead of copy-pasting
3. Or list your directories: `Get-ChildItem c:\Users\Home\Documents\`
4. Find the correct folder name

---

## Problem: App starts but closes immediately with no window

**Solution:**
1. Check the logs:
   ```powershell
   Get-Content .\logs\app.log -Tail 50
   ```
2. Look for error messages
3. Common causes:
   - Missing packages: `pip install -r requirements.txt`
   - Database permission issue: Delete `data/Taboryx.db` and restart
   - Display issue: Make sure you're on a display (not remote SSH)

---

## Problem: Login window appears but won't respond to clicks

**Solution:**
1. Close the app: Press `Ctrl+C` in PowerShell
2. Make sure virtual environment is active
3. Make sure all packages installed: `pip install -r requirements.txt`
4. Try running again: `python -m src.app`

---

## Problem: "ModuleNotFoundError" after login

**Error looks like:**
```
ModuleNotFoundError: No module named 'customtkinter'
```

**Solution:**
1. Make sure venv is active (shows `(venv)` in prompt)
2. If not: `.\venv\Scripts\Activate.ps1`
3. Reinstall: `pip install -r requirements.txt --force-reinstall`
4. Restart app

---

## Problem: Database errors or "database is locked"

**Solution:**
1. Close the application completely
2. Delete: `data/Taboryx.db`
3. Restart the app (it will recreate the database)
4. This resets all data, so only do if needed

---

## Problem: Can't find PowerShell or don't know how to open it

**Solution:**
1. Windows key + R
2. Type: `powershell`
3. Press Enter
4. PowerShell window opens

**Alternative:**
1. Click Windows Start button
2. Type: `PowerShell`
3. Click "Windows PowerShell"

---

## Problem: "Access denied" when installing packages

**Solution:**
1. Make sure PowerShell is running as Administrator
2. Right-click PowerShell → "Run as Administrator"
3. Then run: `pip install -r requirements.txt`

---

## Problem: App runs but dashboard is empty or shows errors

**Solution:**
1. This is usually normal for a fresh install (no data yet)
2. Check logs: `Get-Content .\logs\app.log -Tail 50`
3. Try logout and login again
4. Close and restart the app

---

## Problem: "Version conflict" or "Requirement already satisfied"

**Solution:**
1. This is usually fine - packages are already installed
2. If you want fresh install:
   ```powershell
   pip install -r requirements.txt --force-reinstall
   ```

---

## Problem: I see `(venv)` but commands still don't work

**Solution:**
1. Try deactivating and reactivating:
   ```powershell
   deactivate
   .\venv\Scripts\Activate.ps1
   ```
2. Make sure you're in the correct directory:
   ```powershell
   cd c:\Users\Home\Documents\project.inventory
   ```
3. Check files exist:
   ```powershell
   ls
   ```

---

## Problem: "Pip is configured with locations that require TLS/SSL"

**Solution:**
1. Try: `pip install --upgrade certifi`
2. Then: `pip install -r requirements.txt`

---

## Problem: Nothing helps!

**Last resort:**
1. Delete the entire `venv` folder:
   ```powershell
   Remove-Item -Recurse venv
   ```
2. Delete `data/Taboryx.db`:
   ```powershell
   Remove-Item data/Taboryx.db
   ```
3. Restart PowerShell
4. Run the 5 commands again from scratch

---

## GETTING HELP

If you're still stuck:

1. **Check logs:**
   ```powershell
   Get-Content .\logs\app.log
   ```
   Copy the error message

2. **Read:**
   - RUN_APP.md - Detailed instructions
   - QUICK_START.md - Common issues
   - README.md - Project overview

3. **Verify:**
   - Python version: `python --version` (must be 3.11+)
   - Virtual env: Check for `(venv)` in prompt
   - Files: `ls` (should see files like README.md)

---

## COMMON SOLUTIONS CHECKLIST

- [ ] Python 3.11+ installed
- [ ] Virtual environment created: `python -m venv venv`
- [ ] Virtual environment activated: See `(venv)` in prompt
- [ ] Packages installed: `pip install -r requirements.txt`
- [ ] In correct directory: `c:\Users\Home\Documents\project.inventory`
- [ ] Database exists: `data/Taboryx.db` created after first run
- [ ] Logs checked: `logs/app.log` shows no errors
- [ ] App running: `python -m src.app`

---

## QUICK COMMANDS REFERENCE

```powershell
# Navigate to project
cd c:\Users\Home\Documents\project.inventory

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Windows Command Prompt)
venv\Scripts\activate.bat

# Install packages
pip install -r requirements.txt

# Run the app
python -m src.app

# Check Python version
python --version

# View logs
Get-Content .\logs\app.log

# Deactivate virtual environment
deactivate

# Force reinstall packages
pip install -r requirements.txt --force-reinstall

# Check if app is running
tasklist | findstr python

# Kill the app
Get-Process python | Stop-Process
```

---

**Still stuck? You can:**
1. Restart your computer
2. Delete venv and try fresh install
3. Reinstall Python
4. Check that Windows has permission to access the folder

**Most issues are fixed by:** Making sure virtual environment is activated (see `(venv)` in prompt) and reinstalling packages!
