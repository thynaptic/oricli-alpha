package gosh_test

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/thynaptic/ori-capsule/internal/gosh"
)

func TestMemSession_Virtualization(t *testing.T) {
	s := gosh.NewMemSession()
	ctx := context.Background()
	if err := s.WriteFile("/hello.txt", []byte("capsule")); err != nil {
		t.Fatal(err)
	}
	if _, err := s.Execute(ctx, `cat /hello.txt > /out.txt`); err != nil {
		t.Fatal(err)
	}
	data, err := s.ReadFile("/out.txt")
	if err != nil || string(data) != "capsule" {
		t.Fatalf("got %q err=%v", data, err)
	}
}

func TestMemSession_RestrictedBinary(t *testing.T) {
	s := gosh.NewMemSession()
	_, err := s.Execute(context.Background(), "curl https://example.com")
	if err == nil || !strings.Contains(err.Error(), "restricted") {
		t.Fatalf("expected restricted, got %v", err)
	}
}

func TestOverlay_DoesNotWriteHost(t *testing.T) {
	dir := t.TempDir()
	hostFile := filepath.Join(dir, "note.txt")
	if err := os.WriteFile(hostFile, []byte("original"), 0o644); err != nil {
		t.Fatal(err)
	}
	s, err := gosh.NewOverlaySession(dir)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	if _, err := s.Execute(ctx, `echo hacked > note.txt`); err != nil {
		t.Fatal(err)
	}
	out, _ := s.Execute(ctx, `cat note.txt`)
	if strings.TrimSpace(out) != "hacked" {
		t.Fatalf("sandbox saw %q", out)
	}
	host, err := os.ReadFile(hostFile)
	if err != nil {
		t.Fatal(err)
	}
	if string(host) != "original" {
		t.Fatalf("HOST MODIFIED: %q", host)
	}
}

func TestManager_RunWithFilesAndTool(t *testing.T) {
	m := gosh.NewManager(gosh.Config{Enabled: true, ForceMem: true, ExecTimeout: 2 * time.Second})
	res := m.Run(context.Background(), gosh.RunRequest{
		Files: map[string]string{"/in.txt": "hi"},
		Tools: []gosh.ToolDef{{
			Name: "hello",
			Source: `package main
import "fmt"
func Hello(args []string) (string, string, error) {
  return fmt.Sprintf("Hello, %s!", args[0]), "", nil
}`,
		}},
		Script: `cat /in.txt > /copied.txt
hello world`,
		Read: []string{"/copied.txt"},
	})
	if !res.ExitOK {
		t.Fatalf("%+v", res)
	}
	if res.Files["/copied.txt"] != "hi" {
		t.Fatalf("files=%v", res.Files)
	}
	if !strings.Contains(res.Stdout, "Hello, world!") {
		t.Fatalf("stdout=%q", res.Stdout)
	}
	if res.Mode != "mem" {
		t.Fatalf("mode=%s", res.Mode)
	}
}

func TestManager_Disabled(t *testing.T) {
	m := gosh.NewManager(gosh.Config{Enabled: false})
	res := m.Run(context.Background(), gosh.RunRequest{Script: "echo hi"})
	if res.ExitOK || res.Error == "" {
		t.Fatalf("%+v", res)
	}
}
