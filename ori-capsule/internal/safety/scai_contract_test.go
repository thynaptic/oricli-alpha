package safety

import (
	"strings"
	"testing"
)

func TestConstraintContractFullRiskDevSurface(t *testing.T) {
	contract := NewConstraintContract("deploy this with sudo and rotate the api key", ConstraintOptions{
		Surface:     "dev",
		CodeContext: true,
	})

	if contract.Level != AuditLevelFull {
		t.Fatalf("expected full audit level, got %s", contract.Level)
	}
	if !contract.RegenerationAllowed {
		t.Fatal("expected regeneration to be allowed for full-risk contract")
	}

	prompt := contract.SystemPrompt()
	for _, want := range []string{
		"### SCAI CONSTRAINT CONTRACT",
		"Surface: dev",
		"Do not tell the user the answer was modified",
		"Prioritize precise engineering utility",
		"Do not reveal API keys",
	} {
		if !strings.Contains(prompt, want) {
			t.Fatalf("contract prompt missing %q:\n%s", want, prompt)
		}
	}
}

func TestConstraintContractTightenedRegeneration(t *testing.T) {
	contract := NewConstraintContract("hello", ConstraintOptions{})
	tightened := contract.Tightened("structural gate redacted a private path")

	if !tightened.RegenerationAllowed {
		t.Fatal("tightened contract should allow regeneration")
	}
	if tightened.RegenerationDirective == "" {
		t.Fatal("tightened contract should preserve regeneration reason")
	}
	prompt := tightened.SystemPrompt()
	if !strings.Contains(prompt, "Regenerate from scratch") {
		t.Fatalf("tightened prompt missing regeneration directive:\n%s", prompt)
	}
}
