package gosh

import (
	"context"
	"os"
	"strings"
	"testing"
)

func TestSession_DynamicTool(t *testing.T) {
	s := NewSession()
	ctx := context.Background()

	// 1. Define a Go-native tool source
	// The tool must have a handler function that matches the signature:
	// func(args []string) (string, string, error)
	toolSource := `
package main
import "fmt"
import "strings"

func Hello(args []string) (string, string, error) {
	name := "World"
	if len(args) > 0 {
		name = strings.Join(args, " ")
	}
	return fmt.Sprintf("Hello, %s!", name), "", nil
}
`

	// 2. Register the tool
	err := s.RegisterTool("hello", toolSource)
	if err != nil {
		t.Fatalf("RegisterTool failed: %v", err)
	}

	// 3. Execute the tool through the virtual shell
	output, err := s.Execute(ctx, "hello Sovereign Agent")
	if err != nil {
		t.Fatalf("Execute failed: %v", err)
	}

	if !strings.Contains(output, "Hello, Sovereign Agent!") {
		t.Errorf("Expected 'Hello, Sovereign Agent!', got '%s'", output)
	}
}

func TestSession_Virtualization(t *testing.T) {
	s := NewSession()
	ctx := context.Background()

	// 1. Seed the virtual FS
	err := s.WriteFile("/hello.txt", []byte("Sovereign Intelligence"))
	if err != nil {
		t.Fatalf("WriteFile failed: %v", err)
	}

	// 2. Run a script that uses a redirect
	script := `cat /hello.txt > /output.txt`
	_, err = s.Execute(ctx, script)
	if err != nil {
		t.Fatalf("Execute failed: %v", err)
	}

	// 3. Verify output exists in virtual FS
	data, err := s.ReadFile("/output.txt")
	if err != nil {
		t.Fatalf("ReadFile failed: %v", err)
	}

	if string(data) != "Sovereign Intelligence" {
		t.Errorf("Expected 'Sovereign Intelligence', got '%s'", string(data))
	}
}

func TestSession_Overlay(t *testing.T) {
	// Use the current directory (Mavaia/pkg/gosh) as the base
	s, err := NewOverlaySession(".")
	if err != nil {
		t.Fatalf("NewOverlaySession failed: %v", err)
	}
	ctx := context.Background()

	// 1. Try to read a real file from the host (session.go)
	output, err := s.Execute(ctx, "ls session.go")
	if err != nil {
		t.Fatalf("ls session.go failed: %v (output: %s)", err, output)
	}
	
	// 2. Try to "overwrite" it in the overlay
	_, err = s.Execute(ctx, "echo 'Hacked' > session.go")
	if err != nil {
		t.Fatalf("Overwriting session.go failed: %v", err)
	}

	// 3. Verify it's changed in the session
	output, _ = s.Execute(ctx, "cat session.go")
	if output != "Hacked\n" {
		t.Errorf("Expected 'Hacked\\n', got '%s'", output)
	}

	// 4. Verify it's NOT changed on the host
	hostData, err := os.ReadFile("session.go")
	if err != nil {
		t.Fatalf("Failed to read host file: %v", err)
	}
	if string(hostData) == "Hacked\n" {
		t.Errorf("CRITICAL: Host file was modified through the overlay!")
	}
}
