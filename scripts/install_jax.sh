#!/bin/bash
# JAX Installation Script
# Installs JAX/Flax ecosystem with pre-built wheels when available

set -e

echo "Installing JAX/Flax..."
echo ""

# Try installing with pre-built wheels first (fastest)
echo "Attempting to install JAX with pre-built wheels..."
if pip install --only-binary :all: jax>=0.7.1 jaxlib>=0.7.1 2>/dev/null; then
    echo "✓ JAX installed from pre-built wheels"
else
    echo "Pre-built wheels not available, building from source..."
    echo "This may take 10-20 minutes..."
    pip install jax>=0.7.1 jaxlib>=0.7.1
fi

# Install Flax ecosystem
echo "Installing Flax, optax..."
pip install flax>=0.7.0 optax>=0.1.7

echo ""
echo "Verifying JAX installation..."
python3 -c "import jax; import flax; print('✓ JAX/Flax installed successfully')" || {
    echo "✗ JAX installation verification failed"
    exit 1
}

echo ""
echo "✓ JAX/Flax installation complete!"
