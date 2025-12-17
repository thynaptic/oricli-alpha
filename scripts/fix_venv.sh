#!/bin/bash
# Fix Virtual Environment Script
# Recreates the virtual environment if it's broken

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║          Fix Virtual Environment                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

cd "$PROJECT_ROOT"

# Check if venv exists
if [ -d "$VENV_DIR" ]; then
    echo "Found existing .venv directory"
    echo "The virtual environment appears to be broken (pip hangs)."
    echo ""
    read -p "Remove and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing .venv..."
        rm -rf "$VENV_DIR"
    else
        echo "Keeping existing .venv, attempting to fix pip..."
        echo ""
        echo "Attempting to reinstall pip in existing venv..."
        # Use python -m ensurepip instead of pip directly
        if "$VENV_DIR/bin/python3" -m ensurepip --upgrade 2>&1 | head -20; then
            echo "✓ pip reinstalled"
            echo ""
            echo "Testing pip..."
            if "$VENV_DIR/bin/python3" -m pip --version >/dev/null 2>&1; then
                echo "✓ pip is now working"
                exit 0
            else
                echo "✗ pip still not working. Recreating venv recommended."
                exit 1
            fi
        else
            echo "Failed to fix pip. Recreating venv recommended."
            exit 1
        fi
    fi
fi

echo "Creating new virtual environment..."
python3 -m venv "$VENV_DIR"

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Upgrading pip, setuptools, and wheel..."
# Use python -m pip instead of pip directly to avoid hanging
python3 -m pip install --upgrade pip setuptools wheel --no-warn-script-location

echo ""
echo "Testing pip installation..."
if python3 -m pip --version >/dev/null 2>&1; then
    echo "✓ pip is working correctly"
else
    echo "✗ pip installation may have issues"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          Virtual Environment Fixed!                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To install dependencies:"
echo "  python3 -m pip install -r requirements.txt"
echo ""
echo "Note: If pip still hangs, use 'python3 -m pip' instead of 'pip'"
echo ""
