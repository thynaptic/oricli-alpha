# Mavaia Core Setup Script (PowerShell for Windows)
# Installs system dependencies (CMake) and Python packages

Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          Mavaia Core Setup Script (Windows)            ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check for CMake
Write-Host "Checking for CMake..."
$cmakeExists = Get-Command cmake -ErrorAction SilentlyContinue

if ($cmakeExists) {
    $cmakeVersion = (cmake --version | Select-Object -First 1).ToString()
    Write-Host "✓ CMake found: $cmakeVersion" -ForegroundColor Green
} else {
    Write-Host "✗ CMake not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "CMake is required for JAX installation." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options to install CMake:" -ForegroundColor Yellow
    Write-Host "1. Using Chocolatey (if installed):" -ForegroundColor Yellow
    Write-Host "   choco install cmake" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Using winget (Windows 10/11):" -ForegroundColor Yellow
    Write-Host "   winget install Kitware.CMake" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Download installer from:" -ForegroundColor Yellow
    Write-Host "   https://cmake.org/download/" -ForegroundColor White
    Write-Host ""
    
    $installChoice = Read-Host "Would you like to try installing with winget? (Y/n)"
    if ($installChoice -eq "" -or $installChoice -eq "Y" -or $installChoice -eq "y") {
        $wingetExists = Get-Command winget -ErrorAction SilentlyContinue
        if ($wingetExists) {
            Write-Host "Installing CMake with winget..."
            winget install --id Kitware.CMake --accept-package-agreements --accept-source-agreements
        } else {
            Write-Host "winget not found. Please install CMake manually." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Please install CMake manually and run this script again." -ForegroundColor Red
        exit 1
    }
    
    # Verify installation
    $cmakeExists = Get-Command cmake -ErrorAction SilentlyContinue
    if ($cmakeExists) {
        $cmakeVersion = (cmake --version | Select-Object -First 1).ToString()
        Write-Host "✓ CMake installed successfully: $cmakeVersion" -ForegroundColor Green
    } else {
        Write-Host "ERROR: CMake installation failed. Please install manually." -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# Check for Python
Write-Host "Checking for Python..."
$pythonExists = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonExists) {
    $pythonExists = Get-Command python3 -ErrorAction SilentlyContinue
    if ($pythonExists) {
        $pythonCmd = "python3"
    } else {
        Write-Host "ERROR: Python not found. Please install Python 3.8 or higher." -ForegroundColor Red
        exit 1
    }
} else {
    $pythonCmd = "python"
}

$pythonVersion = & $pythonCmd --version
Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
Write-Host ""

# Check for pip
Write-Host "Checking for pip..."
$pipExists = Get-Command pip -ErrorAction SilentlyContinue
if (-not $pipExists) {
    $pipExists = & $pythonCmd -m pip --version 2>$null
    if ($pipExists) {
        $pipCmd = "$pythonCmd -m pip"
    } else {
        Write-Host "ERROR: pip not found. Installing pip..." -ForegroundColor Red
        & $pythonCmd -m ensurepip --upgrade
        $pipCmd = "$pythonCmd -m pip"
    }
} else {
    $pipCmd = "pip"
}

$pipVersion = & $pipCmd --version | Select-Object -First 1
Write-Host "✓ pip found: $pipVersion" -ForegroundColor Green
Write-Host ""

# Check if we're in a virtual environment
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠ WARNING: Not in a virtual environment." -ForegroundColor Yellow
    Write-Host "  It's recommended to use a virtual environment:" -ForegroundColor Yellow
    Write-Host "    $pythonCmd -m venv .venv" -ForegroundColor White
    Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        Write-Host "Setup cancelled." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ Virtual environment detected: $env:VIRTUAL_ENV" -ForegroundColor Green
}
Write-Host ""

# Upgrade pip
Write-Host "Upgrading pip..."
& $pipCmd install --upgrade pip setuptools wheel
Write-Host ""

# Get the project root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$requirementsFile = Join-Path $projectRoot "requirements.txt"

if (-not (Test-Path $requirementsFile)) {
    Write-Host "ERROR: requirements.txt not found at: $requirementsFile" -ForegroundColor Red
    exit 1
}

# Install Python dependencies
Write-Host "Installing Python dependencies from requirements.txt..."
Write-Host "This may take several minutes, especially for JAX/Flax..."
Write-Host ""

& $pipCmd install -r $requirementsFile

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          Setup Complete!                                ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ CMake installed" -ForegroundColor Green
Write-Host "✓ Python dependencies installed" -ForegroundColor Green
Write-Host ""
Write-Host "You can now use Mavaia Core. To verify installation:" -ForegroundColor Yellow
Write-Host "  $pythonCmd -c 'import jax; import flax; print(\"JAX/Flax installed successfully\")'" -ForegroundColor White
Write-Host ""
