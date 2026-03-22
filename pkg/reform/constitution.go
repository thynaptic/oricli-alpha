package reform

import (
	"fmt"
	"strings"
)

// --- Code Constitution ---
// Mirrors the pattern of pkg/safety/constitution.go but enforces engineering mandates
// rather than safety principles. Injected as the LLM system prompt in GenerateReform()
// to ensure the model never produces partial, placeholder, or unsafe code.

// CodePrinciple is a single engineering mandate with a name, description, and guideline.
type CodePrinciple struct {
	Name        string
	Description string
	Guideline   string
}

// CodeConstitution holds the full set of production-readiness principles.
type CodeConstitution struct {
	Principles []CodePrinciple
}

// NewCodeConstitution returns the canonical Code Constitution for Oricli-Alpha
// self-modification proposals.
func NewCodeConstitution() *CodeConstitution {
	return &CodeConstitution{
		Principles: []CodePrinciple{
			{
				Name:        "Complete Implementation Only",
				Description: "Every function, method, and block must be fully implemented.",
				Guideline:   "Do not emit TODO, FIXME, HACK, XXX, placeholder, stub, or 'not implemented' comments anywhere in the output. Every function body must contain real, working logic — never a bare return, panic, or empty block unless that is genuinely the correct behavior.",
			},
			{
				Name:        "Surgical Scope",
				Description: "Changes must be narrowly targeted at the identified bottleneck.",
				Guideline:   "Only modify the specific function or block causing the traced latency or logic fault. Do not refactor unrelated code, rename variables outside the scope, or restructure package layout. The diff between old and new code must be minimal and justified.",
			},
			{
				Name:        "Compile-Clean Standard",
				Description: "Output must compile with zero errors and pass go vet.",
				Guideline:   "All imports must be used. All declared variables must be used. No shadow declarations that hide outer variables unintentionally. No type mismatches. No unreachable code. The file must be go fmt clean.",
			},
			{
				Name:        "Perimeter Sovereignty",
				Description: "No new external dependencies or network egress may be introduced.",
				Guideline:   "Do not add new import paths that require go get. Do not introduce HTTP calls, file writes outside designated data paths, or subprocess executions outside the existing exec harness. Any network or filesystem operation must use already-established patterns in the codebase.",
			},
			{
				Name:        "Safety Inviolability",
				Description: "Safety, sovereign, and kernel packages are read-only.",
				Guideline:   "Never modify any file under pkg/safety/, pkg/sovereign/, or pkg/kernel/ in a self-modification proposal. These packages form the constitutional and security core of the system and require manual human review for any change.",
			},
			{
				Name:        "Benchmark Justification",
				Description: "Every proposal must include a concrete performance claim.",
				Guideline:   "In a comment at the top of the proposed change, state the specific improvement expected (e.g. 'Reduces MCTS node expansion from O(n²) to O(n log n) by replacing linear scan with a heap'). Vague claims like 'improves performance' are not acceptable.",
			},
			{
				Name:        "Idiomatic Go",
				Description: "Code must follow standard Go idioms and the existing codebase style.",
				Guideline:   "Use the same error-handling pattern as the surrounding file (explicit error return, no panic for recoverable errors). Use sync.Mutex or sync.RWMutex where shared state exists. Do not introduce goroutine leaks — every goroutine must have a clear exit condition.",
			},
		},
	}
}

// GetSystemPrompt formats the Code Constitution as an LLM system prompt.
// This is injected into GenerateReform() alongside the bottleneck trace.
func (c *CodeConstitution) GetSystemPrompt() string {
	var sb strings.Builder
	sb.WriteString("### SOVEREIGN CODE CONSTITUTION\n")
	sb.WriteString("You are a Sovereign Technical Architect proposing a self-modification to a production Go system.\n")
	sb.WriteString("You MUST adhere to every principle below without exception. A proposal that violates any single principle will be automatically rejected by the verification pipeline.\n\n")
	for i, p := range c.Principles {
		sb.WriteString(fmt.Sprintf("%d. **%s** — %s\n   Mandate: %s\n\n", i+1, p.Name, p.Description, p.Guideline))
	}
	sb.WriteString("Respond with ONLY the complete, modified Go file. No markdown fences, no explanation, no preamble — raw Go source only.\n")
	sb.WriteString("### END SOVEREIGN CODE CONSTITUTION\n")
	return sb.String()
}
