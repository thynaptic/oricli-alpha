#!/bin/bash
# Install only distrax (assumes dm-tree is already installed or will be installed)
# This is a simpler script that just tries to install distrax with workarounds

set -e

# Detect pip command
if command -v pip3 >/dev/null 2>&1; then
    PIP_CMD="pip3"
elif python3 -m pip --version >/dev/null 2>&1; then
    PIP_CMD="python3 -m pip"
else
    echo "ERROR: pip not found"
    exit 1
fi

echo "Installing distrax..."
echo ""

# Check if dm-tree is installed
if python3 -c "import tree" 2>/dev/null; then
    echo "✓ dm-tree is already installed"
else
    echo "⚠ dm-tree not found. Installing dm-tree first..."
    ./scripts/install_dm_tree_fixed.sh || {
        echo ""
        echo "⚠ dm-tree installation failed"
        echo "  distrax requires dm-tree"
        echo "  Try: ./scripts/install_cmake3.sh first"
        exit 1
    }
fi

echo ""
echo "Installing distrax..."
$PIP_CMD install distrax>=0.1.7 && {
    echo ""
    echo "✓ distrax installed successfully!"
} || {
    echo ""
    echo "⚠ distrax installation failed"
    echo "  This is only needed for reinforcement_learning_agent module"
    echo "  The module will handle missing distrax gracefully"
    exit 1
}
