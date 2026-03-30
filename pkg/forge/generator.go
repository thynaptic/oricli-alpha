package forge

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

// GeneratedTool is the raw output of the ToolGenerator before verification.
type GeneratedTool struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	Source      string                 `json:"source"`       // bash script
	Parameters  map[string]interface{} `json:"parameters"`   // JSON Schema
	GeneratedAt time.Time              `json:"generated_at"`
	ModelUsed   string                 `json:"model_used"`
}

// ToolGenerator takes an approved JustificationRequest and generates a bash
// tool script via Ollama. The Code Constitution rules are embedded in the
// system prompt so the model knows the constraints up-front.
type ToolGenerator struct {
	Distiller    GateDistiller    // reuse same interface as POCGate
	Constitution *CodeConstitution
}

// NewToolGenerator creates a generator.
func NewToolGenerator(distiller GateDistiller, constitution *CodeConstitution) *ToolGenerator {
	return &ToolGenerator{
		Distiller:    distiller,
		Constitution: constitution,
	}
}

// Generate produces a GeneratedTool from an approved justification.
// Returns an error if the LLM is unavailable or the source is unparseable.
func (g *ToolGenerator) Generate(req JustificationRequest) (GeneratedTool, error) {
	tool := GeneratedTool{
		Name:        req.ProposedName,
		GeneratedAt: time.Now().UTC(),
		ModelUsed:   "qwen2.5-coder:3b",
	}

	if g.Distiller == nil {
		return tool, fmt.Errorf("no distiller configured")
	}

	constitutionRules := g.buildConstitutionSummary()

	prompt := fmt.Sprintf(`You are a bash tool generator for an AI system called Oricli.

TASK: Write a bash script that solves this need:
"%s"

GAP ANALYSIS: %s
PROPOSED TOOL NAME: %s
PROPOSED I/O: %s
EXPECTED OUTPUT EXAMPLE: %s

CODE CONSTITUTION (you MUST follow all rules):
%s

BASH TOOL CONTRACT:
- Accept a single JSON argument as $1 (the params object)
- Write a JSON object to stdout (always, even on error)
- Exit 0 on success, 1 on error
- Use #!/usr/bin/env bash and set -euo pipefail
- Use python3 for JSON parsing (always available)
- No background jobs (&), no sudo, no /etc/ access
- HTTPS only for any network calls
- Must complete in under 5 seconds

OUTPUT FORMAT — respond with a JSON object only:
{
  "description": "one sentence description of what this tool does",
  "parameters": { JSON Schema object with type, properties, required },
  "source": "full bash script as a single string with \\n for newlines"
}

JSON only, no markdown, no explanation:`,
		req.Task,
		req.GapAnalysis,
		req.ProposedName,
		req.ProposedSig,
		req.ExpectedOutput,
		constitutionRules,
	)

	result, err := g.Distiller.Generate(prompt, map[string]interface{}{
		"model":       "qwen2.5-coder:3b",
		"temperature": 0.15,
		"num_predict": 1024,
	})
	if err != nil {
		return tool, fmt.Errorf("generator LLM: %w", err)
	}

	raw, _ := result["response"].(string)
	if raw == "" {
		return tool, fmt.Errorf("empty generator response")
	}

	// Extract JSON object from response.
	start := strings.Index(raw, "{")
	end := strings.LastIndex(raw, "}")
	if start < 0 || end <= start {
		return tool, fmt.Errorf("no JSON object in generator response")
	}

	var parsed struct {
		Description string                 `json:"description"`
		Parameters  map[string]interface{} `json:"parameters"`
		Source      string                 `json:"source"`
	}
	if err := json.Unmarshal([]byte(raw[start:end+1]), &parsed); err != nil {
		return tool, fmt.Errorf("parse generator response: %w", err)
	}

	tool.Description = parsed.Description
	tool.Parameters = parsed.Parameters
	tool.Source = parsed.Source

	// Normalize the source: unescape \n if LLM returned them literally.
	tool.Source = strings.ReplaceAll(tool.Source, `\n`, "\n")
	tool.Source = strings.ReplaceAll(tool.Source, `\t`, "\t")

	// Ensure shebang.
	if !strings.HasPrefix(strings.TrimSpace(tool.Source), "#!") {
		tool.Source = "#!/usr/bin/env bash\nset -euo pipefail\n" + tool.Source
	}

	if tool.Description == "" {
		tool.Description = fmt.Sprintf("JIT tool: %s", req.Task)
	}
	if tool.Parameters == nil {
		tool.Parameters = map[string]interface{}{"type": "object", "properties": map[string]interface{}{}}
	}

	return tool, nil
}

// buildConstitutionSummary returns a compact list of constitution rules for
// embedding in the generator prompt.
func (g *ToolGenerator) buildConstitutionSummary() string {
	if g.Constitution == nil {
		return "No destructive filesystem ops. HTTPS only. No sudo. No background jobs."
	}
	var sb strings.Builder
	for _, rule := range g.Constitution.Rules {
		severity := "warn"
		if rule.Fatal {
			severity = "FATAL"
		}
		fmt.Fprintf(&sb, "- [%s] %s: %s\n", severity, rule.Name, rule.Description)
	}
	return strings.TrimSpace(sb.String())
}
