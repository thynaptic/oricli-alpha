package vdi

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// --- Pillar 46: Sovereign System Orchestrator ---
// Secure wrappers for host-level file and command execution.

// ReadFile safely reads a file from the host system.
func (m *Manager) ReadFile(path string) (string, error) {
	// Security: Prevent reading sensitive keys
	if strings.Contains(path, "api_key") || strings.Contains(path, ".env") {
		return "", fmt.Errorf("security violation: access to sensitive environment files is blocked")
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("failed to read file %s: %v", path, err)
	}

	content := string(data)
	if len(content) > 10000 {
		content = content[:10000] + "... (truncated)"
	}
	return content, nil
}

// WriteFile safely writes content to the host system.
func (m *Manager) WriteFile(path string, content string) (string, error) {
	// Security: Prevent overwriting core binaries
	if strings.HasSuffix(path, ".so") || strings.HasSuffix(path, ".bin") {
		return "", fmt.Errorf("security violation: writing to binary files is blocked")
	}

	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return "", fmt.Errorf("failed to create directory %s: %v", dir, err)
	}

	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		return "", fmt.Errorf("failed to write file %s: %v", path, err)
	}

	return fmt.Sprintf("Successfully wrote %d bytes to %s", len(content), path), nil
}

// ExecCommand runs a bash command on the host.
// Disabled by default — set ORICLI_VDI_EXEC=true to enable. Free-form shell
// from LLM-planned workspace steps is otherwise host RCE.
func (m *Manager) ExecCommand(command string) (string, error) {
	if os.Getenv("ORICLI_VDI_EXEC") != "true" {
		return "", fmt.Errorf("security violation: host command execution disabled (set ORICLI_VDI_EXEC=true to enable)")
	}

	lower := strings.ToLower(command)
	blocked := []string{
		"rm -rf /", "mkfs", "dd if=", ":(){", "shutdown", "reboot",
		"curl ", "wget ", "nc ", "ncat ", "python -c", "perl -e",
		"/etc/passwd", "/etc/shadow", ".oricli/api_key", ".env",
	}
	for _, b := range blocked {
		if strings.Contains(lower, b) {
			return "", fmt.Errorf("security violation: command blocked by VDI safeguard")
		}
	}

	cmd := exec.Command("bash", "-c", command)
	out, err := cmd.CombinedOutput()

	result := string(out)
	if len(result) > 5000 {
		result = result[:5000] + "... (truncated output)"
	}

	if err != nil {
		return result, fmt.Errorf("command failed: %v", err)
	}

	if result == "" {
		result = "Command executed successfully with no output."
	}
	return result, nil
}
