# Oricli-Alpha Core Installation Guide

## Quick Install

### macOS / Linux

```bash
# Run the setup script (installs CMake and all dependencies)
./scripts/setup.sh
```

### Windows

```powershell
# Run the setup script (installs CMake and all dependencies)
.\scripts\setup.ps1
```

## Manual Installation

### 1. Install System Dependencies

**macOS:**
```bash
brew install cmake
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y cmake build-essential
```

**Linux (Fedora/RHEL):**
```bash
sudo dnf install -y cmake gcc gcc-c++ make
```

**Windows:**
- Download CMake from: https://cmake.org/download/
- Or use winget: `winget install Kitware.CMake`
- Or use Chocolatey: `choco install cmake`

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## Verify Installation

```bash
python3 -c "import jax; import flax; print('JAX/Flax installed successfully')"
```

## Troubleshooting

### CMake Not Found
- Ensure CMake is installed and in your PATH
- Verify with: `cmake --version`

### JAX Installation

JAX v0.7.1+ supports Python 3.14.0 with pre-built wheels. If you encounter installation issues:

**Option 1: Use pre-built wheels (recommended):**
```bash
pip install --only-binary :all: jax jaxlib
pip install flax optax transformers huggingface-hub
```

**Option 2: Use the installation script:**
```bash
./scripts/install_jax.sh
```

**Option 3: Install from requirements:**
```bash
pip install -r requirements.txt
```

### Python Version
- Requires Python 3.8 or higher
- Check with: `python3 --version`
- JAX v0.7.1+ supports Python 3.14.0 with pre-built wheels

### CMake Version Compatibility
- CMake is required for some Python packages that need to build C extensions
- The setup script will automatically install CMake if needed
- CMake 3.15+ is recommended

## Requirements

- Python 3.8+
- CMake 3.15+
- pip, setuptools, wheel
- System build tools (gcc, make, etc.)
