#!/bin/bash
# Install requirements with CMake policy fix for dm-tree
# This script sets up the environment and installs all dependencies

set -e

echo "Installing Mavaia Core with CMake policy fixes..."
echo ""

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

# Set CMake policy environment variables
export CMAKE_ARGS="-DCMAKE_POLICY_DEFAULT_CMP0003=NEW -DCMAKE_POLICY_DEFAULT_CMP0011=NEW -DCMAKE_POLICY_DEFAULT_CMP0074=NEW -DCMAKE_POLICY_DEFAULT_CMP0005=NEW"

# Create a temporary pip configuration that passes CMake args
PIP_CONFIG_DIR=$(mktemp -d)
export PIP_CONFIG_FILE="$PIP_CONFIG_DIR/pip.conf"

# Function to install with workaround
install_with_workaround() {
    local package=$1
    echo "Installing $package..."
    
    # Try normal install first
    if pip install "$package" 2>/dev/null; then
        echo "✓ $package installed successfully"
        return 0
    fi
    
    # Try with no build isolation
    echo "  Trying with --no-build-isolation..."
    if pip install --no-build-isolation "$package" 2>/dev/null; then
        echo "✓ $package installed successfully (with --no-build-isolation)"
        return 0
    fi
    
    # Try with explicit CMake args in environment
    echo "  Trying with CMake policy workaround..."
    CMAKE_ARGS="$CMAKE_ARGS" pip install --no-build-isolation --no-cache-dir "$package" 2>/dev/null && {
        echo "✓ $package installed successfully (with CMake workaround)"
        return 0
    }
    
    echo "✗ $package installation failed"
    return 1
}

# Install core dependencies first (everything except JAX ecosystem)
echo "Step 1: Installing core dependencies..."
pip install --upgrade pip setuptools wheel

pip install \
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
    duckduckgo-search>=4.0.0 \
    transformers>=4.30.0 \
    huggingface-hub>=0.16.0

echo ""
echo "Step 2: Installing JAX/Flax ecosystem..."

# Try pre-built wheels first for JAX
if pip install --only-binary :all: jax>=0.4.20 jaxlib>=0.4.20 2>/dev/null; then
    echo "✓ JAX installed from pre-built wheels"
else
    echo "Installing JAX from source (this may take 10-20 minutes)..."
    install_with_workaround "jax>=0.4.20" || install_with_workaround "jaxlib>=0.4.20" || {
        echo "⚠ JAX installation had issues, but continuing..."
    }
fi

# Install Flax and optax (usually no issues)
pip install flax>=0.7.0 optax>=0.1.7

# Install distrax (requires dm-tree, which is the problematic one)
echo ""
echo "Step 3: Installing distrax (requires dm-tree)..."
if install_with_workaround "distrax>=0.1.7"; then
    echo "✓ All dependencies installed successfully!"
else
    echo ""
    echo "⚠ distrax installation failed"
    echo "  This is only needed for reinforcement_learning_agent module"
    echo "  The module will handle missing distrax gracefully"
    echo ""
    echo "To fix later, you can try:"
    echo "  export CMAKE_ARGS=\"-DCMAKE_POLICY_DEFAULT_CMP0003=NEW\""
    echo "  pip install --no-build-isolation distrax>=0.1.7"
fi

# Cleanup
rm -rf "$PIP_CONFIG_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          Installation Complete!                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
