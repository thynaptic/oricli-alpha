package agents_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/thynaptic/ori-capsule/internal/agents"
)

func TestLibrary_LoadAndResolve(t *testing.T) {
	dir := t.TempDir()
	content := `---
name: ori-reasoner
description: Deep reasoning lane
tools:
  - read
  - edit
user-invocable: true
---

You are the reasoner.
`
	if err := os.WriteFile(filepath.Join(dir, "ori-reasoner.agent.md"), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	fast := `---
name: ori-chat-fast
description: Fast chat
tools: []
---

Stay concise.
`
	if err := os.WriteFile(filepath.Join(dir, "ori-chat-fast.agent.md"), []byte(fast), 0o644); err != nil {
		t.Fatal(err)
	}

	lib := agents.Open(dir)
	if n := len(lib.List()); n != 2 {
		t.Fatalf("list=%d", n)
	}
	a, ok := lib.Get("ori-reasoner")
	if !ok || !strings.Contains(a.Prompt, "reasoner") || len(a.Tools) != 2 {
		t.Fatalf("%+v ok=%v", a, ok)
	}
	def, ok := lib.Resolve("")
	if !ok || def.Name != "ori-chat-fast" {
		t.Fatalf("default=%+v", def)
	}
	block := agents.PromptBlock(a)
	if !strings.Contains(block, "ORI AGENT PROFILE") {
		t.Fatalf("%q", block)
	}
}
