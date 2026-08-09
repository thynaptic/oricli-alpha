package reform_test

import (
	"strings"
	"testing"

	"github.com/thynaptic/ori-capsule/internal/reform"
)

func TestCanvasConstitution_Prompt(t *testing.T) {
	p := reform.NewCanvasConstitution().GetSystemPrompt()
	if !strings.Contains(p, "SOVEREIGN CANVAS CODE CONSTITUTION") {
		t.Fatalf("missing header: %s", p[:80])
	}
	if !strings.Contains(p, "No Credential or Secret Embedding") {
		t.Fatal("missing secret principle")
	}
}

func TestCodeConstitution_Prompt(t *testing.T) {
	p := reform.NewCodeConstitution().GetSystemPrompt()
	if !strings.Contains(p, "SOVEREIGN CODE CONSTITUTION") {
		t.Fatal("missing header")
	}
	if !strings.Contains(p, "Complete Implementation Only") {
		t.Fatal("missing principle")
	}
}

func TestPromptForSurface(t *testing.T) {
	if reform.PromptForSurface(false, false) != "" {
		t.Fatal("default surface should be empty")
	}
	canvas := reform.PromptForSurface(true, true)
	if !strings.Contains(canvas, "CANVAS") {
		t.Fatalf("canvas should win over code: %q", canvas[:60])
	}
	code := reform.PromptForSurface(false, true)
	if !strings.Contains(code, "CODE CONSTITUTION") || strings.Contains(code, "CANVAS") {
		t.Fatalf("code prompt unexpected: %q", code[:80])
	}
}
