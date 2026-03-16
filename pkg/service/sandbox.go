package service

import (
	"bytes"
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

type ExecutionResult struct {
	Success       bool    `json:"success"`
	Stdout        string  `json:"stdout"`
	Stderr        string  `json:"stderr"`
	ExitCode      int     `json:"exit_code"`
	ExecutionTime float64 `json:"execution_time"`
}

type SandboxService struct {
	SandboxRoot string
	Timeout     time.Duration
}

func NewSandboxService(root string) *SandboxService {
	if root == "" {
		root = "/tmp/oricli_sandbox"
	}
	os.MkdirAll(root, 0755)
	return &SandboxService{
		SandboxRoot: root,
		Timeout:     30 * time.Second,
	}
}

func (s *SandboxService) ExecuteCommand(command string, args []string, timeout time.Duration) ExecutionResult {
	if timeout == 0 {
		timeout = s.Timeout
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	start := time.Now()
	cmd := exec.CommandContext(ctx, command, args...)
	
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	duration := time.Since(start).Seconds()

	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = -1
		}
	}

	return ExecutionResult{
		Success:       err == nil,
		Stdout:        stdout.String(),
		Stderr:        stderr.String(),
		ExitCode:      exitCode,
		ExecutionTime: duration,
	}
}

func (s *SandboxService) WriteFile(name, content string) (string, error) {
	path := filepath.Join(s.SandboxRoot, name)
	err := os.WriteFile(path, []byte(content), 0644)
	return path, err
}

func (s *SandboxService) DeleteFile(name string) error {
	path := filepath.Join(s.SandboxRoot, name)
	return os.Remove(path)
}
