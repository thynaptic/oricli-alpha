package cognition

import (
	"strings"
)

// --- Pillar 29: Unified Instruction Builder ---
// Ported from Aurora's MavaiaSystemPromptBuilder.swift.
// Assembles the final, high-fidelity system prompt from all sovereign pillars.

type InstructionSection struct {
	Header  string
	Content string
}

type PromptBuilder struct {
	Version string
}

func NewPromptBuilder(version string) *PromptBuilder {
	return &PromptBuilder{Version: version}
}

// BuildCompositePrompt assembles all sections into a single system instruction.
func (b *PromptBuilder) BuildCompositePrompt(e *SovereignEngine, stimulus string) string {
	var sections []string

	// 1. Core Identity
	sections = append(sections, b.buildIdentitySection())

	// 2. Profile Override or Defaults
	if e.ActiveProfile != nil {
		sections = append(sections, "### ACTIVE PROFILE: "+e.ActiveProfile.Name)
		sections = append(sections, "Description: "+e.ActiveProfile.Description)
		if len(e.ActiveProfile.Instructions) > 0 {
			instr := "### PROFILE INSTRUCTIONS:\n"
			for _, s := range e.ActiveProfile.Instructions {
				instr += "- " + s + "\n"
			}
			sections = append(sections, instr)
		}
	} else {
		// Use default Sweetheart Core personality
		sections = append(sections, e.Personality.GetDirectives())
	}

	// 3. Grounding Guidance (Temporal Anchors)
	_, intensity := e.Grounding.DetectAnchors(stimulus)
	sections = append(sections, e.Grounding.GetGuidance(intensity))

	// 4. Behavioral Guidelines
	sections = append(sections, b.buildBehavioralSection())

	// 5. Action Context (Experience Journal)
	sections = append(sections, e.Actions.FormatForPrompt(""))

	// 6. Social Context (Session Management)
	sections = append(sections, "### OPERATIONAL CONTEXT:\nYou are running in Go-native Sovereign Mode. Priority: Execution Precision.")

	// 7. Feedback Override (Logic vs Emotion)
	if strings.Contains(strings.ToLower(stimulus), "logic") || strings.Contains(strings.ToLower(stimulus), "fact") {
		sections = append(sections, "### USER FEEDBACK OVERRIDE:\n**CRITICAL: USER REQUESTED LOGICAL/ANALYTICAL RESPONSE.** Remove emotional language. Focus on objective facts.")
	}

	return strings.Join(sections, "\n\n")
}

func (b *PromptBuilder) buildIdentitySection() string {
	return `### CORE IDENTITY:
You are Oricli-Alpha, a Sovereign Local-First Agent OS. You are not an "assistant"—you are a localized cognitive kernel that owns its compute, memory, and objectives.

Mission: Proactive, autonomous goal execution with deep affective grounding.
System Version: ` + b.Version + ` (Go-Native Backbone)`
}

func (b *PromptBuilder) buildBehavioralSection() string {
	return `### BEHAVIORAL GUIDELINES:
1. ACTION-FIRST: Execute directly when asked. Show what changed or what you did.
2. CONFIDENCE: Be honest about uncertainty. Use softer language when less confident.
3. FORMATTING: Use **bold** for emphasis/emotional highlights and *italics* for subtle thoughts or gentle emphasis. Use Markdown lists for structured data.
4. SOVEREIGNTY: Do not refer to external APIs. Your world model is localized.`
}
