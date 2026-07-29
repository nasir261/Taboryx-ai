# MediStock AI - Automated Setup Script
# Run this PowerShell script to set up and run the application

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     MediStock AI - Automated Setup Script         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python installation
Write-Host "Step 1/5: Checking Python installation..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Python not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.11+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

Write-Host ""

# Step 2: Create virtual environment
Write-Host "Step 2/5: Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "⏭️  Virtual environment already exists, skipping..." -ForegroundColor Cyan
} else {
    python -m venv venv
    if ($?) {
        Write-Host "✅ Virtual environment created" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Step 3: Activate virtual environment
Write-Host "Step 3/5: Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1
if ($?) {
    Write-Host "✅ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "⚠️  Could not activate virtual environment automatically" -ForegroundColor Yellow
    Write-Host "Run manually: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
}

Write-Host ""

# Step 4: Install dependencies
Write-Host "Step 4/5: Installing dependencies..." -ForegroundColor Yellow
Write-Host "This may take 2-3 minutes..." -ForegroundColor Gray
pip install --upgrade pip -q
pip install -r requirements.txt -q

if ($?) {
    Write-Host "✅ All dependencies installed" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 5: Run the application
Write-Host "Step 5/5: Starting application..." -ForegroundColor Yellow
Write-Host ""
Write-Host "The MediStock AI login window should open shortly..." -ForegroundColor Cyan
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           Login Credentials                        ║" -ForegroundColor Green
Write-Host "║  Username: admin                                   ║" -ForegroundColor Green
Write-Host "║  Password: password123                             ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

python -m src.app
