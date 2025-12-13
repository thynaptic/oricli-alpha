#!/bin/bash
# Fix dm-tree build issue with CMake policy compatibility
# This script sets the necessary CMake policies and installs dm-tree

set -e

echo "Fixing dm-tree build issue..."
echo ""

# The issue is that dm-tree's dependencies (pybind11, absl) have outdated CMake requirements
# We need to set CMake policies to allow compatibility

# Set CMake policy environment variables
export CMAKE_ARGS="-DCMAKE_POLICY_DEFAULT_CMP0003=NEW -DCMAKE_POLICY_DEFAULT_CMP0011=NEW -DCMAKE_POLICY_DEFAULT_CMP0074=NEW"

# Also try setting it via pip's build environment
export PIP_BUILD_ISOLATION=0

echo "Attempting to install dm-tree with CMake policy workaround..."
echo ""

# Try installing with the workaround
pip install --no-build-isolation --no-cache-dir dm-tree || {
    echo ""
    echo "⚠ dm-tree installation failed with standard method"
    echo "Trying alternative approach..."
    echo ""
    
    # Alternative: Install from source with explicit CMake flags
    pip install --no-build-isolation --no-cache-dir \
        --global-option="build_ext" \
        --global-option="-DCMAKE_POLICY_DEFAULT_CMP0003=NEW" \
        --global-option="-DCMAKE_POLICY_DEFAULT_CMP0011=NEW" \
        dm-tree || {
        echo ""
        echo "⚠ dm-tree installation still failed"
        echo ""
        echo "Workaround: Install JAX without dm-tree dependency"
        echo "  JAX will work, but some features may be limited"
        echo ""
        echo "To install JAX without dm-tree:"
        echo "  pip install --no-deps jax jaxlib"
        echo "  pip install flax optax"
        exit 1
    }
}

echo ""
echo "✓ dm-tree installed successfully!"
echo "You can now install distrax:"
echo "  pip install distrax>=0.1.7"
