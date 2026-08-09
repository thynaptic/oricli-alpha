package forge_test

import (
	"strings"
	"testing"
	"time"

	"github.com/thynaptic/ori-capsule/internal/forge"
)

func TestMemoryLibrary_PutGetEvict(t *testing.T) {
	lib := forge.NewMemoryLibrary(2, time.Hour)
	yaegiOK := `package main
import "strings"
func Hello(args []string) (string, string, error) {
  return strings.ToUpper(args[0]), "", nil
}
`
	a, err := lib.Put(forge.JITTool{Name: "hello", Kind: "yaegi", Source: yaegiOK, Description: "upper"})
	if err != nil {
		t.Fatal(err)
	}
	if a.Name != "hello" {
		t.Fatalf("%+v", a)
	}
	got, ok := lib.Get("hello")
	if !ok || got.Description != "upper" {
		t.Fatalf("%+v ok=%v", got, ok)
	}

	// Forbidden source rejected.
	_, err = lib.Put(forge.JITTool{Name: "bad", Kind: "yaegi", Source: `package main
import "os/exec"
func Bad(args []string) (string, string, error) { return "", "", nil }
`})
	if err == nil || !strings.Contains(err.Error(), "constitution") {
		t.Fatalf("err=%v", err)
	}

	scriptOK := "echo hi\n"
	if _, err := lib.Put(forge.JITTool{Name: "s1", Kind: "script", Source: scriptOK}); err != nil {
		t.Fatal(err)
	}
	if _, err := lib.Put(forge.JITTool{Name: "s2", Kind: "script", Source: scriptOK}); err != nil {
		t.Fatal(err)
	}
	// max=2 → hello should be evicted eventually after two more puts (LRU).
	if len(lib.List()) > 2 {
		t.Fatalf("list=%d", len(lib.List()))
	}
}
