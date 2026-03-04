#!/bin/bash
set -e

# 1. Create a custom, minimal sshd_config to ensure settings are correct
mkdir -p /var/run/sshd /etc/ssh
cat > /etc/ssh/sshd_config <<EOF
Port 22
Protocol 2
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_dsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key

PermitRootLogin yes
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys

PasswordAuthentication no
ChallengeResponseAuthentication no

UsePAM yes
PrintMotd no
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/openssh/sftp-server
EOF

# 2. Generate SSH host keys if they don't exist
ssh-keygen -A

# 3. Inject the user-provided public key
USER_HOME="/root"
if [ -n "$PUBLIC_KEY$SSH_PUBLIC_KEY$RUNPOD_PUBLIC_KEY$SSH_KEY" ]; then
    SSH_KEY_CONTENT="${PUBLIC_KEY:-$SSH_PUBLIC_KEY:-$RUNPOD_PUBLIC_KEY:-$SSH_KEY}"
    echo "[INFO] Injecting SSH public key..."
    mkdir -p "$USER_HOME/.ssh"
    echo "$SSH_KEY_CONTENT" > "$USER_HOME/.ssh/authorized_keys"
    chmod 700 "$USER_HOME/.ssh"
    chmod 600 "$USER_HOME/.ssh/authorized_keys"
    chown -R root:root "$USER_HOME/.ssh"
    echo "[INFO] SSH key injection complete."
else
    echo "[WARN] No public key found in environment. SSH access will likely fail."
fi

# 4. Start SSHD as the main foreground process
echo "[INFO] Starting SSH daemon as the main container process..."
exec /usr/sbin/sshd -D -e -f /etc/ssh/sshd_config
