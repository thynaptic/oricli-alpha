#!/bin/bash
# Install CMake 3.x manually (when Homebrew doesn't have cmake@3)

set -e

echo "Installing CMake 3.x for dm-tree compatibility..."
echo ""

# Check if we're on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "This script is for macOS. For Linux, install CMake 3.x via your package manager."
    exit 1
fi

CMAKE3_VERSION="3.29.3"  # Latest CMake 3.x version
CMAKE3_URL="https://github.com/Kitware/CMake/releases/download/v${CMAKE3_VERSION}/cmake-${CMAKE3_VERSION}-macos-universal.tar.gz"
INSTALL_DIR="/usr/local/cmake-3"

echo "Downloading CMake ${CMAKE3_VERSION}..."
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

curl -L -o cmake.tar.gz "$CMAKE3_URL" || {
    echo "ERROR: Failed to download CMake"
    exit 1
}

echo "Extracting..."
tar -xzf cmake.tar.gz
CMAKE_DIR=$(ls -d cmake-* | head -1)

echo "Installing to $INSTALL_DIR..."
sudo mkdir -p "$INSTALL_DIR"
sudo cp -r "$CMAKE_DIR"/* "$INSTALL_DIR"/

# Create symlink
echo "Creating symlink..."
sudo ln -sf "$INSTALL_DIR/CMake.app/Contents/bin/cmake" /usr/local/bin/cmake3
sudo ln -sf "$INSTALL_DIR/CMake.app/Contents/bin/ctest" /usr/local/bin/ctest3

# Also make cmake point to cmake3 if cmake is 4.x
CURRENT_CMAKE=$(which cmake)
CURRENT_VERSION=$(cmake --version 2>/dev/null | head -n1 | cut -d' ' -f3 | cut -d'.' -f1 || echo "0")
if [ "$CURRENT_VERSION" -ge 4 ] 2>/dev/null; then
    echo "Linking cmake to cmake3..."
    sudo ln -sf "$INSTALL_DIR/CMake.app/Contents/bin/cmake" /usr/local/bin/cmake
fi

cd /
rm -rf "$TEMP_DIR"

echo ""
echo "✓ CMake 3.x installed successfully!"
echo "  Version: $($INSTALL_DIR/CMake.app/Contents/bin/cmake --version | head -n1)"
echo ""
echo "You can now install distrax:"
echo "  pip install distrax>=0.1.7"
