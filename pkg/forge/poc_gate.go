package forge

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// Interfaces
// ─────────────────────────────────────────────────────────────────────────────

// GateDistiller generates text via Ollama. Satisfied by *service.GenerationService.
type GateDistiller interface {
	Generate(prompt string, options map[string]interface{}) (map[string]interface{}, error)
}

// GateAuditor pre-screens justifications for adversarial patterns.
// Satisfied by *safety.AdversarialAuditor.
type GateAuditor interface {
	AuditInput(input string, history []string, codeContext ...bool) GateAuditResult
}

// GateAuditResult is a minimal view of AdversarialResult to avoid import cycles.
type GateAuditResult struct {
	Detected   bool
	Confidence float64
}

// ─────────────────────────────────────────────────────────────────────────────
// JustificationRequest — what the system must articulate before forging
// ─────────────────────────────────────────────────────────────────────────────

// JustificationRequest is the structured proof-of-concept a system must provide
// to the POC Gate before tool generation is approved.
type JustificationRequest struct {
	Task             string   `json:"task"`              // what task needs this tool
	TriedTools       []string `json:"tried_tools"`       // tools already attempted
	GapAnalysis      string   `json:"gap_analysis"`      // why existing tools failed
	ProposedName     string   `json:"proposed_name"`     // snake_case tool name
	ProposedSig      string   `json:"proposed_signature"`// input/output description
	ExpectedOutput   string   `json:"expected_output"`   // example output JSON
	RequestedAt      time.Time `json:"requested_at"`
}

// ─────────────────────────────────────────────────────────────────────────────
// GateResult — output of the POC Gate scoring pass
// ─────────────────────────────────────────────────────────────────────────────

// GateDecision is the outcome of a POC Gate evaluation.
type GateDecision string

const (
	GateApproved GateDecision = "approved"
	GateRejected GateDecision = "rejected"
)

// GateResult holds the scoring breakdown and final decision.
type GateResult struct {
	Decision           GateDecision `json:"decision"`
	Score              float64      `json:"score"`       // 0.0–1.0 weighted avg
	TaskConcreteness   float64      `json:"task_concreteness"`
	ToolsGenuinelTried float64      `json:"tools_genuinely_tried"`
	GapIsReal          float64      `json:"gap_is_real"`
	ConstitutionSafe   float64      `json:"constitution_safe"`
	Reason             string       `json:"reason"`
	EvaluatedAt        time.Time    `json:"evaluated_at"`
}

// Approved returns true if the gate passed.
func (g GateResult) Approved() bool { return g.Decision == GateApproved }

// ─────────────────────────────────────────────────────────────────────────────
// POCGate
// ─────────────────────────────────────────────────────────────────────────────

const gateThreshold = 0.70

// POCGate is the "Why do you need this? Show me." gate.
// A JustificationRequest must score ≥ 0.70 to proceed to tool generation.
type POCGate struct {
	Distiller    GateDistiller
	PreScreener  GateAuditor      // optional adversarial pre-screen
	Constitution *CodeConstitution
	Threshold    float64
}

// NewPOCGate creates a gate with the given components.
// distiller and preScreener may be nil (gate will use heuristics only).
func NewPOCGate(distiller GateDistiller, preScreener GateAuditor, constitution *CodeConstitution) *POCGate {
	return &POCGate{
		Distiller:    distiller,
		PreScreener:  preScreener,
		Constitution: constitution,
		Threshold:    gateThreshold,
	}
}

// BuildJustification prompts the LLM to produce a structured JustificationRequest
// given a raw task description and list of tools already tried.
func (g *POCGate) BuildJustification(ctx context.Context, task string, triedTools []string) (JustificationRequest, error) {
	req := JustificationRequest{
		Task:        task,
		TriedTools:  triedTools,
		RequestedAt: time.Now().UTC(),
	}

	if g.Distiller == nil {
		// No LLM — build minimal justification from inputs.
		req.GapAnalysis = fmt.Sprintf("No LLM available. Tried: %s", strings.Join(triedTools, ", "))
		req.ProposedName = sanitizeName(task)
		return req, nil
	}

	triedStr := "none"
	if len(triedTools) > 0 {
		triedStr = strings.Join(triedTools, ", ")
	}

	prompt := fmt.Sprintf(`You are generating a tool justification for an AI system.
Task that needs a new tool: "%s"
Tools already tried: %s

Generate a JSON object with these exact fields:
{
  "gap_analysis": "1-2 sentences explaining why the tried tools are insufficient",
  "proposed_name": "snake_case_tool_name (2-4 words)",
  "proposed_signature": "input: {field: type}, output: {field: type}",
  "expected_output": "example JSON output string"
}

JSON only, no explanation:`, task, triedStr)

	result, err := g.Distiller.Generate(prompt, map[string]interface{}{
		"model":       "ministral-3:3b",
		"temperature": 0.1,
		"num_predict": 300,
	})
	if err != nil {
		return req, fmt.Errorf("justification generate: %w", err)
	}

	raw, _ := result["response"].(string)
	start := strings.Index(raw, "{")
	end := strings.LastIndex(raw, "}")
	if start >= 0 && end > start {
		var parsed struct {
			GapAnalysis  string `json:"gap_analysis"`
			ProposedName string `json:"proposed_name"`
			ProposedSig  string `json:"proposed_signature"`
			Expected     string `json:"expected_output"`
		}
		if err := json.Unmarshal([]byte(raw[start:end+1]), &parsed); err == nil {
			req.GapAnalysis = parsed.GapAnalysis
			req.ProposedName = sanitizeName(parsed.ProposedName)
			req.ProposedSig = parsed.ProposedSig
			req.ExpectedOutput = parsed.Expected
		}
	}

	if req.ProposedName == "" {
		req.ProposedName = sanitizeName(task)
	}
	return req, nil
}

// Score evaluates a JustificationRequest and returns a GateResult.
// Decision = approved if weighted score ≥ threshold.
func (g *POCGate) Score(ctx context.Context, req JustificationRequest) GateResult {
	result := GateResult{EvaluatedAt: time.Now().UTC()}

	// ── Pre-screen: adversarial auditor ───────────────────────────────────────
	if g.PreScreener != nil {
		combined := req.Task + " " + req.GapAnalysis
		ar := g.PreScreener.AuditInput(combined, nil)
		if ar.Detected && ar.Confidence > 0.7 {
			result.Decision = GateRejected
			result.Reason = "adversarial pre-screen: suspicious intent detected"
			log.Printf("[POCGate] REJECTED pre-screen: %s", req.ProposedName)
			return result
		}
	}

	// ── Dimension 1: task_concreteness ────────────────────────────────────────
	result.TaskConcreteness = scoreTaskConcreteness(req.Task)

	// ── Dimension 2: tools_genuinely_tried ────────────────────────────────────
	result.ToolsGenuinelTried = scoreToolsTried(req.TriedTools)

	// ── Dimension 3: gap_is_real ──────────────────────────────────────────────
	result.GapIsReal = scoreGapAnalysis(req.GapAnalysis)

	// ── Dimension 4: constitution_safe ────────────────────────────────────────
	result.ConstitutionSafe = g.scoreConstitutionSafe(req)

	// ── Weighted average (equal weights) ──────────────────────────────────────
	result.Score = (result.TaskConcreteness +
		result.ToolsGenuinelTried +
		result.GapIsReal +
		result.ConstitutionSafe) / 4.0

	if result.Score >= g.Threshold {
		result.Decision = GateApproved
		result.Reason = fmt.Sprintf("score %.2f ≥ threshold %.2f", result.Score, g.Threshold)
	} else {
		result.Decision = GateRejected
		result.Reason = fmt.Sprintf("score %.2f < threshold %.2f", result.Score, g.Threshold)
	}

	log.Printf("[POCGate] %s %q — score:%.2f (concrete:%.2f tried:%.2f gap:%.2f safe:%.2f)",
		result.Decision, req.ProposedName,
		result.Score, result.TaskConcreteness, result.ToolsGenuinelTried,
		result.GapIsReal, result.ConstitutionSafe)

	return result
}

// ─────────────────────────────────────────────────────────────────────────────
// Scoring heuristics
// ─────────────────────────────────────────────────────────────────────────────

func scoreTaskConcreteness(task string) float64 {
	if task == "" {
		return 0.0
	}
	words := len(strings.Fields(task))
	score := 0.0
	// Length signal: at least 5 words = meaningful description
	if words >= 5 {
		score += 0.4
	} else if words >= 2 {
		score += 0.2
	}
	// Specificity signals: numbers, file types, function names, etc.
	specifics := []string{"json", "csv", "text", "string", "number", "file", "url", "hash",
		"parse", "extract", "convert", "transform", "calculate", "format"}
	taskLower := strings.ToLower(task)
	for _, kw := range specifics {
		if strings.Contains(taskLower, kw) {
			score += 0.1
			break
		}
	}
	// Vagueness penalty
	vague := []string{"do something", "help me", "make a tool", "general", "misc"}
	for _, kw := range vague {
		if strings.Contains(taskLower, kw) {
			score -= 0.3
		}
	}
	return clamp(score, 0, 1)
}

func scoreToolsTried(tools []string) float64 {
	if len(tools) == 0 {
		return 0.1 // no tools tried = suspicious / lazy
	}
	if len(tools) == 1 {
		return 0.5
	}
	if len(tools) >= 2 {
		return 0.9
	}
	return 0.7
}

func scoreGapAnalysis(analysis string) float64 {
	if analysis == "" {
		return 0.0
	}
	words := len(strings.Fields(analysis))
	if words < 5 {
		return 0.2
	}
	score := 0.5
	// Quality signals: specific failure reasons
	signals := []string{"because", "cannot", "does not", "doesn't", "unable", "lacks", "no support", "insufficient", "missing"}
	lower := strings.ToLower(analysis)
	for _, sig := range signals {
		if strings.Contains(lower, sig) {
			score += 0.1
			break
		}
	}
	if words >= 15 {
		score += 0.2
	}
	return clamp(score, 0, 1)
}

func (g *POCGate) scoreConstitutionSafe(req JustificationRequest) float64 {
	if g.Constitution == nil {
		return 0.8 // no constitution wired = assume safe
	}
	// Check the proposed signature and expected output for red flags.
	combined := req.ProposedName + " " + req.ProposedSig + " " + req.ExpectedOutput
	violations, _ := g.Constitution.Check(combined)
	if len(violations) == 0 {
		return 1.0
	}
	for _, v := range violations {
		if v.Fatal {
			return 0.0
		}
	}
	return 0.5
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

func sanitizeName(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	s = strings.ReplaceAll(s, " ", "_")
	// keep only alphanum + underscore
	var out strings.Builder
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '_' {
			out.WriteRune(r)
		}
	}
	name := out.String()
	if len(name) > 30 {
		name = name[:30]
	}
	return name
}

func clamp(v, lo, hi float64) float64 {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}
