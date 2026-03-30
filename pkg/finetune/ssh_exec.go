package finetune

// SSHClient dials a RunPod pod's exposed SSH port and executes commands.
// Uses golang.org/x/crypto/ssh — already in go.mod.
//
// An ephemeral ed25519 keypair is generated per FineTuneOrchestrator run.
// The public key is injected into the pod via the env field at pod creation
// (the Axolotl image's entrypoint writes AUTHORIZED_KEY to ~/.ssh/authorized_keys).

import (
	"bytes"
	"crypto/ed25519"
	"crypto/rand"
	"fmt"
	"io"
	"net"
	"os"
	"strings"
	"time"

	gossh "golang.org/x/crypto/ssh"
)

const (
	sshDialTimeout = 30 * time.Second
	sshExecTimeout = 4 * time.Hour
	sshUser        = "root"
)

// ─────────────────────────────────────────────────────────────────────────────
// Keypair
// ─────────────────────────────────────────────────────────────────────────────

// SSHKeypair is an ephemeral ed25519 keypair for one training run.
type SSHKeypair struct {
	PrivateKey ed25519.PrivateKey
	PublicKey  ed25519.PublicKey
	AuthorizedKeyLine string // "ssh-ed25519 AAAA... oricli-finetune"
}

// GenerateSSHKeypair generates a fresh ed25519 keypair.
func GenerateSSHKeypair() (*SSHKeypair, error) {
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return nil, fmt.Errorf("keygen: %w", err)
	}

	sshPub, err := gossh.NewPublicKey(pub)
	if err != nil {
		return nil, fmt.Errorf("ssh pubkey: %w", err)
	}

	authLine := string(gossh.MarshalAuthorizedKey(sshPub))
	authLine = strings.TrimSuffix(authLine, "\n")

	return &SSHKeypair{
		PrivateKey:        priv,
		PublicKey:         pub,
		AuthorizedKeyLine: string(authLine),
	}, nil
}

// ─────────────────────────────────────────────────────────────────────────────
// SSHClient
// ─────────────────────────────────────────────────────────────────────────────

// SSHClient manages an SSH connection to a RunPod pod.
type SSHClient struct {
	client *gossh.Client
	host   string
	port   int
}

// Dial connects to host:port using the provided private key.
func Dial(host string, port int, privKey ed25519.PrivateKey) (*SSHClient, error) {
	signer, err := gossh.NewSignerFromKey(privKey)
	if err != nil {
		return nil, fmt.Errorf("ssh signer: %w", err)
	}

	cfg := &gossh.ClientConfig{
		User:            sshUser,
		Auth:            []gossh.AuthMethod{gossh.PublicKeys(signer)},
		HostKeyCallback: gossh.InsecureIgnoreHostKey(), // pod hosts are ephemeral
		Timeout:         sshDialTimeout,
	}

	addr := fmt.Sprintf("%s:%d", host, port)
	conn, err := gossh.Dial("tcp", addr, cfg)
	if err != nil {
		return nil, fmt.Errorf("ssh dial %s: %w", addr, err)
	}

	return &SSHClient{client: conn, host: host, port: port}, nil
}

// DialWithRetry retries Dial up to maxAttempts with delay between tries.
// Useful immediately after pod becomes RUNNING — SSH daemon may not be ready yet.
func DialWithRetry(host string, port int, privKey ed25519.PrivateKey, maxAttempts int, delay time.Duration) (*SSHClient, error) {
	var lastErr error
	for i := 0; i < maxAttempts; i++ {
		if i > 0 {
			time.Sleep(delay)
		}
		client, err := Dial(host, port, privKey)
		if err == nil {
			return client, nil
		}
		lastErr = err
	}
	return nil, fmt.Errorf("ssh dial failed after %d attempts: %w", maxAttempts, lastErr)
}

// Exec runs a command on the remote host and returns combined stdout+stderr.
// The command runs in a new session — not interactive.
func (s *SSHClient) Exec(cmd string) (string, error) {
	sess, err := s.client.NewSession()
	if err != nil {
		return "", fmt.Errorf("new session: %w", err)
	}
	defer sess.Close()

	var out bytes.Buffer
	sess.Stdout = &out
	sess.Stderr = &out

	if err := sess.Run(cmd); err != nil {
		return out.String(), fmt.Errorf("exec %q: %w\noutput: %s", cmd, err, out.String())
	}
	return out.String(), nil
}

// ExecStream runs a command and writes output lines to the provided writer in real time.
func (s *SSHClient) ExecStream(cmd string, w io.Writer) error {
	sess, err := s.client.NewSession()
	if err != nil {
		return fmt.Errorf("new session: %w", err)
	}
	defer sess.Close()

	sess.Stdout = w
	sess.Stderr = w
	return sess.Run(cmd)
}

// UploadFile copies a local file to a remote path via SFTP-style SCP.
func (s *SSHClient) UploadFile(localPath, remotePath string) error {
	data, err := os.ReadFile(localPath)
	if err != nil {
		return fmt.Errorf("read local file %s: %w", localPath, err)
	}
	return s.UploadBytes(data, remotePath)
}

// UploadBytes writes bytes to a remote file via inline echo (no sftp dep needed).
func (s *SSHClient) UploadBytes(data []byte, remotePath string) error {
	sess, err := s.client.NewSession()
	if err != nil {
		return fmt.Errorf("new session: %w", err)
	}
	defer sess.Close()

	sess.Stdin = bytes.NewReader(data)
	cmd := fmt.Sprintf("cat > %s", remotePath)
	if err := sess.Run(cmd); err != nil {
		return fmt.Errorf("upload to %s: %w", remotePath, err)
	}
	return nil
}

// DownloadFile pulls a remote file to a local path.
func (s *SSHClient) DownloadFile(remotePath, localPath string) error {
	sess, err := s.client.NewSession()
	if err != nil {
		return fmt.Errorf("new session: %w", err)
	}
	defer sess.Close()

	var buf bytes.Buffer
	sess.Stdout = &buf
	if err := sess.Run("cat " + remotePath); err != nil {
		return fmt.Errorf("download %s: %w", remotePath, err)
	}

	return os.WriteFile(localPath, buf.Bytes(), 0644)
}

// Close closes the SSH connection.
func (s *SSHClient) Close() {
	if s.client != nil {
		s.client.Close()
	}
}

// WaitForFile polls until a remote file exists (training output file).
func (s *SSHClient) WaitForFile(remotePath string, interval, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	for {
		if time.Now().After(deadline) {
			return fmt.Errorf("timeout waiting for %s after %s", remotePath, timeout)
		}
		out, _ := s.Exec(fmt.Sprintf("test -f %s && echo yes || echo no", remotePath))
		if bytes.Contains([]byte(out), []byte("yes")) {
			return nil
		}
		// Check if connection is still alive
		if _, err := net.Dial("tcp", fmt.Sprintf("%s:%d", s.host, s.port)); err != nil {
			return fmt.Errorf("pod connection lost: %w", err)
		}
		time.Sleep(interval)
	}
}
