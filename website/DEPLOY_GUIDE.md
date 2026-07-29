# Website Deployment Guide

## What was created

```
website/
├── index.html            ← Main landing page
├── updates.html          ← Release history + manifest viewer
├── Taboryx_version.json ← Version manifest (read by the desktop app)
├── config.js             ← Single file for renaming the app / changing settings
└── assets/
    └── style.css         ← All styles

.github/workflows/
└── deploy-website.yml    ← Auto-deploys to GitHub Pages on every push
```

---

## Step 1 — Create a GitHub repository

1. Go to https://github.com/new
2. Create a new repository (can be private or public — Pages works on both with the right plan)
3. Name it anything, e.g. `Taboryx-site` or your final app name

---

## Step 2 — Push this project to GitHub

Open a terminal in `C:\Users\Home\Documents\project.inventory` and run:

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

---

## Step 3 — Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages** (left sidebar)
3. Under **Source**, select **GitHub Actions**
4. Click **Save**

Your site will be live at:
```
https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/
```

---

## Step 4 — Update the manifest URL in the desktop app

Open `src/services/update_service.py` and change:

```python
UPDATE_MANIFEST_URL = "https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/Taboryx_version.json"
```

---

## How to post a new update

### 1. Edit `website/Taboryx_version.json`

```json
{
  "version": "1.0.0",
  "title": "Version 1.0.0 — Your update title",
  "release_date": "01 August 2026",
  "download_url": "https://github.com/YOUR_USERNAME/YOUR_REPO/releases/download/v1.0.0/TaboryxSetup_1.0.0.exe",
  "filename": "TaboryxSetup_1.0.0.exe",
  "release_notes": "- What changed\n- Another change\n- Bug fix"
}
```

### 2. Edit `website/updates.html`

Copy the latest update block and add a new one at the top inside `<div id="update-list">`.

### 3. Edit `website/config.js`

Update `currentVersion` to match.

### 4. Push to GitHub

```bash
git add website/
git commit -m "Release v1.0.0"
git push
```

GitHub Actions will automatically redeploy the site within ~60 seconds.

---

## Renaming the app

Edit **`website/config.js`** — change `appName`, `appTagline`, `appDescription`.
Every page reads from this single file. No other files need to change.
