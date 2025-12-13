# Mavaia Core Installation

## Quick Start

**IMPORTANT: Python Version Requirements**
- ✅ **Python 3.11 or 3.12** (Recommended - best compatibility)
- ✅ Python 3.8 to 3.13 (Supported)
- ❌ **Python 3.14** (NOT supported - Flax compatibility issues)

### Step 1: Install Python 3.11 or 3.12

**macOS:**
```bash
brew install python@3.11
# Or
brew install python@3.12
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install python3.11 python3.11-venv
# Or
sudo apt-get install python3.12 python3.12-venv
```

### Step 2: Create Virtual Environment

```bash
# Using Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate

# Or using Python 3.12
python3.12 -m venv .venv
source .venv/bin/activate
```

### Step 3: Run Setup Script

```bash
./scripts/setup.sh
```

The setup script will:
- ✅ Install CMake (or CMake 3.x if CMake 4.x is detected)
- ✅ Install all Python dependencies including JAX/Flax
- ✅ Handle dm-tree/distrax installation with workarounds

## Manual Installation

See [INSTALL.md](INSTALL.md) for detailed manual installation instructions.

## Troubleshooting

### Python 3.14 Error
If you see Flax compatibility errors, you're using Python 3.14. Switch to Python 3.11 or 3.12.

### CMake 4.x / dm-tree Build Error
If distrax installation fails due to dm-tree:
1. Install CMake 3.x: `./scripts/install_cmake3.sh`
2. Or install JAX without distrax (JAX works fine, distrax is optional)

### Verify Installation

```bash
python3 -c "import jax; import flax; print('✓ JAX/Flax installed successfully')"
```
