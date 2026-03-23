package reform

import (
	"fmt"
	"strings"
)

// CanvasConstitution enforces production-readiness principles for Canvas-mode
// code generation. Unlike CodeConstitution (which is Go-specific and diff-scoped),
// CanvasConstitution is language-agnostic and targets new artifact generation:
// React/JSX, HTML, Python, Go snippets, shell scripts, etc.
//
// Injected as the LLM system prompt addendum whenever isCanvasMode || isCodeAction
// is detected in handleChatCompletions.
type CanvasConstitution struct {
	Principles []CodePrinciple
}

// NewCanvasConstitution returns the canonical Canvas Code Constitution.
func NewCanvasConstitution() *CanvasConstitution {
	return &CanvasConstitution{
		Principles: []CodePrinciple{
			{
				Name:        "Complete Implementation Only",
				Description: "Every function, component, and block must be fully implemented.",
				Guideline:   "Do not emit TODO, FIXME, HACK, XXX, placeholder, stub, or 'not implemented' markers. Every function body must contain real, working logic. Never return an empty block, a bare throw, or a console.log placeholder unless that is genuinely the correct behavior. If a section would require external data not yet available, implement a sensible default or clearly-typed interface — never a stub.",
			},
			{
				Name:        "Syntax and Parse-Clean Standard",
				Description: "Output must be syntactically valid and parseable with zero errors.",
				Guideline:   "All imports must be used. All declared variables must be referenced. No unclosed tags, missing brackets, or type mismatches. JSX must be valid React. Python must be PEP8-clean. Go must pass go vet. HTML must be valid markup. The file must be formatter-clean for its language.",
			},
			{
				Name:        "Perimeter Sovereignty",
				Description: "No new external CDN dependencies, third-party API calls, or unvetted imports.",
				Guideline:   "Do not add <script src='https://...'>, unpkg/jsDelivr CDN imports, or fetch() calls to external services not already established in the codebase. All imports must reference packages already present in package.json / go.mod / requirements.txt. Never introduce network egress to unknown endpoints.",
			},
			{
				Name:        "Self-Contained Artifact",
				Description: "The generated artifact must work in isolation without undeclared external state.",
				Guideline:   "Props, function arguments, and component interfaces must be fully typed and documented inline. Do not reference global variables, window properties, or context values that are not declared within the artifact or explicitly passed as parameters. If the artifact needs external state, define a clear props/params interface at the top.",
			},
			{
				Name:        "Idiomatic Patterns",
				Description: "Code must follow the idiomatic conventions of its language and the existing codebase style.",
				Guideline:   "React: functional components, hooks, no class components unless explicitly requested. Go: explicit error returns, no panic for recoverable errors, sync.Mutex for shared state. Python: type hints, context managers, no bare except. Match the naming conventions, indentation style, and import ordering of the surrounding codebase.",
			},
			{
				Name:        "No Credential or Secret Embedding",
				Description: "Artifacts must never contain hardcoded secrets, API keys, passwords, or internal paths.",
				Guideline:   "Never hardcode API keys, tokens, connection strings, internal IP addresses, filesystem paths, or user credentials. Use environment variable references (process.env.X, os.Getenv(), os.environ.get()) with clearly named placeholders. Flag any location where a secret would be needed with a clear // CONFIGURE: comment.",
			},
		},
	}
}

// GetSystemPrompt formats the Canvas Constitution as an LLM system prompt addendum.
func (c *CanvasConstitution) GetSystemPrompt() string {
	var sb strings.Builder
	sb.WriteString("### SOVEREIGN CANVAS CODE CONSTITUTION\n")
	sb.WriteString("You are generating a production-ready code artifact for a Sovereign AI system.\n")
	sb.WriteString("You MUST adhere to every principle below. A generated artifact that violates any single principle will be rejected.\n\n")
	for i, p := range c.Principles {
		sb.WriteString(fmt.Sprintf("%d. **%s** — %s\n   Mandate: %s\n\n", i+1, p.Name, p.Description, p.Guideline))
	}
	sb.WriteString("Generate ONLY the complete, working code artifact. Include a brief comment header describing what it does. No apologies, no preamble — clean artifact output only.\n")
	sb.WriteString("### END SOVEREIGN CANVAS CODE CONSTITUTION\n")
	return sb.String()
}
