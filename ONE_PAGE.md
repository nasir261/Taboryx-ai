# MediStock AI - ONE PAGE QUICK REFERENCE

## 5 COMMANDS TO RUN THE APP

```powershell
cd c:\Users\Home\Documents\project.inventory
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.app
```

**Login:** admin / password123

---

## WHAT YOU GET

| Feature | Status |
|---------|--------|
| User Authentication | ✅ Works |
| Database | ✅ 13 tables ready |
| Dashboard | ✅ Shows metrics |
| Inventory View | ✅ Ready for items |
| Stock Movements | ✅ Ready to log |
| Barcode Support | 🔄 Next phase |
| Reporting | 🔄 Next phase |

---

## COMMON ERRORS & FIXES

| Error | Fix |
|-------|-----|
| "python not found" | Install Python 3.11+ |
| "Cannot load Activate.ps1" | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| "No module customtkinter" | `pip install -r requirements.txt` |
| "App won't start" | Check `logs/app.log` |

---

## FILE LOCATIONS

| File | Purpose |
|------|---------|
| `c:\Users\Home\Documents\project.inventory` | Project folder |
| `data/medistock.db` | Database |
| `logs/app.log` | Error logs |
| `src/config.py` | Settings |
| `src/app.py` | Start here |

---

## NEXT STEPS AFTER APP RUNS

### Option 1: Explore (15 min)
- Click through Dashboard
- Check Inventory view
- See Stock Movements

### Option 2: Develop (2-3 hours)
- Read: `DEVELOPMENT.md`
- Build: Inventory CRUD UI
- Add: Barcode scanner

### Option 3: Customize (30 min)
- Edit: `src/config.py`
- Add: New roles
- Change: Categories

---

## DOCUMENTATION

- **RUN_APP.md** - How to run the app
- **CHECKLIST.md** - Step-by-step checklist
- **QUICK_START.md** - Getting started guide
- **DEVELOPMENT.md** - How to code features
- **README.md** - Project overview

---

## PROJECT STATS

| Metric | Value |
|--------|-------|
| Lines of Code | 1,985 |
| Database Tables | 13 |
| Service Methods | 30+ |
| Modules | 18 |
| Documentation | 40KB |

---

## KEYBOARD SHORTCUTS

| Action | Key |
|--------|-----|
| Activate venv | `. .\venv\Scripts\Activate.ps1` |
| Stop app | `Ctrl+C` |
| Deactivate venv | `deactivate` |
| Check logs | `Get-Content logs/app.log` |

---

## REQUIREMENTS

- Python 3.11+
- Windows 10+
- 500MB disk space
- 2GB RAM

---

**That's it! Follow the 5 commands at the top and you're done.** 🚀
