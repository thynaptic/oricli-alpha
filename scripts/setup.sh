#!/bin/bash
# Oricli-Alpha Core Setup Script
# Installs system dependencies (CMake) and Python packages

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════════╗"
echo "║          Oricli-Alpha Core Setup Script                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

echo "Detected OS: $OS"
echo "Detected Architecture: $ARCH"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install CMake on macOS
install_cmake_macos() {
    if command_exists brew; then
        echo "Installing CMake using Homebrew..."
        brew install cmake
    else
        echo "ERROR: Homebrew not found. Please install Homebrew first:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo ""
        echo "Or install CMake manually from: https://cmake.org/download/"
        exit 1
    fi
}

# Function to install CMake on Linux
install_cmake_linux() {
    if command_exists apt-get; then
        echo "Installing CMake using apt-get..."
        sudo apt-get update
        sudo apt-get install -y cmake build-essential
    elif command_exists yum; then
        echo "Installing CMake using yum..."
        sudo yum install -y cmake gcc gcc-c++ make
    elif command_exists dnf; then
        echo "Installing CMake using dnf..."
        sudo dnf install -y cmake gcc gcc-c++ make
    elif command_exists pacman; then
        echo "Installing CMake using pacman..."
        sudo pacman -S --noconfirm cmake base-devel
    else
        echo "ERROR: Could not detect package manager. Please install CMake manually:"
        echo "  https://cmake.org/download/"
        exit 1
    fi
}

# Check and install CMake
echo "Checking for CMake..."
if command_exists cmake; then
    CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
    CMAKE_MAJOR=$(echo "$CMAKE_VERSION" | cut -d'.' -f1)
    echo "✓ CMake found: version $CMAKE_VERSION"
    
    # Check for CMake 4.x compatibility issue
    if [ "$CMAKE_MAJOR" -ge 4 ] 2>/dev/null; then
        echo ""
        echo "⚠ WARNING: CMake 4.x detected"
        echo "  CMake 4.x has known compatibility issues with dm-tree (required for distrax)"
        echo "  Installing CMake 3.x for compatibility..."
        echo ""
        
        if command_exists brew; then
            # Check if cmake@3 is available (it's not in newer Homebrew)
            if brew info cmake@3 >/dev/null 2>&1; then
                echo "Installing CMake 3.x..."
                brew install cmake@3 2>/dev/null || brew upgrade cmake@3 2>/dev/null || true
                brew link cmake@3 --force 2>/dev/null || {
                    echo "⚠ Could not link CMake 3.x automatically"
                    echo "  You may need to run: brew link cmake@3 --force"
                }
                
                # Verify CMake 3.x is now active
                CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
                CMAKE_MAJOR=$(echo "$CMAKE_VERSION" | cut -d'.' -f1)
                if [ "$CMAKE_MAJOR" -eq 3 ] 2>/dev/null; then
                    echo "✓ CMake 3.x is now active: version $CMAKE_VERSION"
                else
                    echo "⚠ CMake 3.x installed but not active. Current version: $CMAKE_VERSION"
                    echo "  Run: brew link cmake@3 --force"
                fi
            else
                echo "⚠ CMake 3.x formula not available in Homebrew"
                echo "  Homebrew only provides CMake 4.x now"
                echo ""
                echo "  Continuing with CMake 4.x..."
                echo "  The setup will attempt to work around dm-tree build issues"
                echo "  JAX/Flax will install and work correctly"
                echo "  distrax may require additional workarounds"
            fi
        else
            echo "⚠ CMake 4.x detected but Homebrew not available"
            echo "  Please install CMake 3.x manually for full compatibility"
            echo "  JAX/Flax will work, but distrax may fail to install"
        fi
        echo ""
    fi
else
    echo "✗ CMake not found. Installing..."
    case "$OS" in
        Darwin*)
            install_cmake_macos
            ;;
        Linux*)
            install_cmake_linux
            ;;
        *)
            echo "ERROR: Unsupported OS: $OS"
            echo "Please install CMake manually from: https://cmake.org/download/"
            exit 1
            ;;
    esac
    
    # Verify installation
    if command_exists cmake; then
        CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
        echo "✓ CMake installed successfully: version $CMAKE_VERSION"
    else
        echo "ERROR: CMake installation failed. Please install manually."
        exit 1
    fi
fi
echo ""

# Check for Python
echo "Checking for Python..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)
    echo "✓ Python found: version $PYTHON_VERSION"
    
    # Check for minimum version
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]) 2>/dev/null; then
        echo "ERROR: Python 3.8 or higher required. Found: $PYTHON_VERSION"
        exit 1
    fi
else
    echo "ERROR: Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi
echo ""

# Check for pip
echo "Checking for pip..."
if command_exists pip3; then
    PIP_VERSION=$(pip3 --version | cut -d' ' -f2)
    echo "✓ pip found: version $PIP_VERSION"
    PIP_CMD="pip3"
elif python3 -m pip --version >/dev/null 2>&1; then
    echo "✓ pip found (via python3 -m pip)"
    PIP_CMD="python3 -m pip"
else
    echo "ERROR: pip not found. Installing pip..."
    python3 -m ensurepip --upgrade
    PIP_CMD="python3 -m pip"
fi
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠ WARNING: Not in a virtual environment."
    echo "  It's recommended to use a virtual environment:"
    echo "    python3 -m venv .venv"
    echo "    source .venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
else
    echo "✓ Virtual environment detected: $VIRTUAL_ENV"
fi
echo ""

# Upgrade pip
echo "Upgrading pip..."
$PIP_CMD install --upgrade pip setuptools wheel
echo ""

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if requirements.txt exists
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "ERROR: requirements.txt not found at: $REQUIREMENTS_FILE"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies from requirements.txt..."
echo "This may take several minutes, especially for JAX/Flax..."
echo ""

# Set CMake policy environment variables to handle dm-tree build issues
export CMAKE_ARGS="-DCMAKE_POLICY_DEFAULT_CMP0003=NEW -DCMAKE_POLICY_DEFAULT_CMP0011=NEW -DCMAKE_POLICY_DEFAULT_CMP0074=NEW"

# Install dependencies in stages to handle dm-tree build issues
echo "Step 1: Installing core dependencies (excluding JAX/Flax)..."
$PIP_CMD install --upgrade pip setuptools wheel

# Install everything except JAX ecosystem first
$PIP_CMD install \
    fastapi>=0.104.0 \
    "uvicorn[standard]>=0.24.0" \
    pydantic>=2.0.0 \
    flask>=3.0.0 \
    httpx>=0.24.0 \
    requests>=2.31.0 \
    pandas>=1.5.0 \
    numpy>=1.23.0 \
    scikit-learn>=1.2.0 \
    docker>=6.0.0 \
    psutil>=5.9.0 \
    beautifulsoup4>=4.12.0 \
    PyPDF2>=3.0.0 \
    transformers>=4.30.0 \
    huggingface-hub>=0.16.0

echo ""
echo "Step 2: Installing JAX/Flax ecosystem..."
echo "Attempting to install with pre-built wheels first..."

# Try to install JAX with pre-built wheels (JAX v0.7.1+ has wheels for Python 3.14)
if $PIP_CMD install --only-binary :all: jax>=0.7.1 jaxlib>=0.7.1 2>/dev/null; then
    echo "✓ JAX installed from pre-built wheels"
else
    echo "Pre-built wheels not available, installing from source..."
    echo "This may take 10-20 minutes..."
    $PIP_CMD install jax>=0.7.1 jaxlib>=0.7.1
fi

# Install Flax and optax
echo "Installing Flax and optax..."
$PIP_CMD install flax>=0.7.0 optax>=0.1.7

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          Setup Complete!                                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "✓ CMake installed"
echo "✓ Python dependencies installed"
echo ""
echo "You can now use Oricli-Alpha Core. To verify installation:"
echo "  python3 -c 'import jax; import flax; print(\"JAX/Flax installed successfully\")'"
echo ""
