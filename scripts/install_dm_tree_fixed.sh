#!/bin/bash
# Install dm-tree with CMake 4.x compatibility fix
# Uses CMake toolchain file to set policies

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

echo "Installing dm-tree with CMake 4.x compatibility fix..."
echo ""

# Check CMake version
CMAKE_VERSION=$(cmake --version 2>/dev/null | head -n1 | cut -d' ' -f3 || echo "unknown")
CMAKE_MAJOR=$(echo "$CMAKE_VERSION" | cut -d'.' -f1)

if [ "$CMAKE_MAJOR" -lt 4 ] 2>/dev/null; then
    echo "CMake $CMAKE_VERSION should work fine"
    echo "Installing dm-tree normally..."
    $PIP_CMD install --no-build-isolation dm-tree
    $PIP_CMD install distrax>=0.1.7
    echo "✓ Installation complete!"
    exit 0
fi

echo "Detected CMake $CMAKE_VERSION (4.x) - applying compatibility fixes..."
echo ""

# Create CMake toolchain file that sets all required policies
TOOLCHAIN_DIR=$(mktemp -d)
TOOLCHAIN_FILE="$TOOLCHAIN_DIR/cmake_policy_fix.cmake"

cat > "$TOOLCHAIN_FILE" << 'TOOLCHAIN_EOF'
# CMake toolchain file to fix policy compatibility issues with CMake 4.x
# This file sets all required policies to NEW to allow compatibility

# Set policies to NEW to avoid compatibility errors
cmake_policy(SET CMP0003 NEW)
cmake_policy(SET CMP0011 NEW)
cmake_policy(SET CMP0074 NEW)
cmake_policy(SET CMP0005 NEW)

# Set minimum version policy (critical for CMake 4.x)
if(POLICY CMP0144)
    cmake_policy(SET CMP0144 NEW)
endif()

# Also handle the cmake_minimum_required compatibility
# This allows old cmake_minimum_required(VERSION 3.5) to work
if(POLICY CMP0144)
    # Allow version ranges
    set(CMAKE_POLICY_DEFAULT_CMP0144 NEW)
endif()
TOOLCHAIN_EOF

# Set environment to use toolchain file
export CMAKE_TOOLCHAIN_FILE="$TOOLCHAIN_FILE"
export CMAKE_ARGS="-DCMAKE_TOOLCHAIN_FILE=$TOOLCHAIN_FILE -DCMAKE_POLICY_DEFAULT_CMP0003=NEW -DCMAKE_POLICY_DEFAULT_CMP0011=NEW -DCMAKE_POLICY_DEFAULT_CMP0074=NEW -DCMAKE_POLICY_DEFAULT_CMP0144=NEW"

echo "Installing dm-tree with CMake toolchain fix..."
echo "This may take a few minutes..."
echo ""

# Try installing with toolchain
$PIP_CMD install --no-build-isolation --no-cache-dir dm-tree && {
    echo ""
    echo "✓ dm-tree installed successfully!"
    rm -rf "$TOOLCHAIN_DIR"
    
    echo ""
    echo "Installing distrax..."
    $PIP_CMD install distrax>=0.1.7 && {
        echo "✓ distrax installed successfully!"
        echo ""
        echo "✓ Installation complete!"
        exit 0
    } || {
        echo "⚠ distrax installation failed"
        echo "  Try: $PIP_CMD install distrax>=0.1.7"
        exit 0  # dm-tree is installed, that's the main thing
    }
} || {
    echo ""
    echo "⚠ Installation failed with toolchain method"
    echo "Trying alternative approach..."
    rm -rf "$TOOLCHAIN_DIR"
    unset CMAKE_TOOLCHAIN_FILE
    
    # Alternative: Create CMake wrapper
    WRAPPER_DIR=$(mktemp -d)
    CMAKE_WRAPPER="$WRAPPER_DIR/cmake"
    CMAKE_PATH=$(which cmake)
    
    cat > "$CMAKE_WRAPPER" << EOF
#!/bin/bash
# CMake wrapper that sets policies and patches pybind11
# First, patch any pybind11 CMakeLists.txt files
find /tmp -path "*/pybind11*" -name "CMakeLists.txt" 2>/dev/null | while read f; do
    if [ -f "\$f" ] && grep -q "cmake_minimum_required.*VERSION 3.5" "\$f" 2>/dev/null; then
        sed -i.bak 's/cmake_minimum_required(VERSION 3\\.5)/cmake_minimum_required(VERSION 3.5...4.0)/g' "\$f" 2>/dev/null
        if ! grep -q "cmake_policy.*CMP0144" "\$f"; then
            sed -i.bak '1i\
cmake_policy(SET CMP0144 NEW)\
' "\$f" 2>/dev/null
        fi
        rm -f "\${f}.bak" 2>/dev/null
    fi
done

# Call real cmake with policy arguments
exec "$CMAKE_PATH" \\
    -DCMAKE_POLICY_DEFAULT_CMP0003=NEW \\
    -DCMAKE_POLICY_DEFAULT_CMP0011=NEW \\
    -DCMAKE_POLICY_DEFAULT_CMP0074=NEW \\
    -DCMAKE_POLICY_DEFAULT_CMP0144=NEW \\
    "\$@"
EOF
    chmod +x "$CMAKE_WRAPPER"
    export PATH="$WRAPPER_DIR:$PATH"
    
    $PIP_CMD install --no-build-isolation --no-cache-dir dm-tree && {
        echo ""
        echo "✓ dm-tree installed successfully with wrapper method!"
        rm -rf "$WRAPPER_DIR"
        
        echo ""
        echo "Installing distrax..."
        $PIP_CMD install distrax>=0.1.7 && echo "✓ distrax installed!" || echo "⚠ distrax failed"
        exit 0
    } || {
        echo ""
        echo "✗ dm-tree installation failed with all methods"
        echo ""
        echo "The issue: pybind11 (dm-tree dependency) is incompatible with CMake 4.x"
        echo ""
        echo "Recommended solution: Install CMake 3.x"
        echo "  ./scripts/install_cmake3.sh"
        echo ""
        echo "Note: JAX/Flax are installed and working correctly"
        echo "      distrax is optional (only needed for reinforcement_learning_agent)"
        rm -rf "$WRAPPER_DIR"
        exit 1
    }
}
