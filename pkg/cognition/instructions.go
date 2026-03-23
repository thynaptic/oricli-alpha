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

	// 2. Personality directives — always included (calibrated per-turn by sovereign engine)
	sections = append(sections, e.Personality.GetDirectives())

	// 3. Profile override — layered ON TOP of personality, not replacing it
	if e.ActiveProfile != nil {
		if e.ActiveProfile.Description != "" {
			sections = append(sections, "### ACTIVE PROFILE: "+e.ActiveProfile.Name+"\n"+e.ActiveProfile.Description)
		}
		if len(e.ActiveProfile.Instructions) > 0 {
			instr := "### PROFILE INSTRUCTIONS:\n"
			for _, s := range e.ActiveProfile.Instructions {
				instr += "- " + s + "\n"
			}
			sections = append(sections, instr)
		}
	}

	// 4. Grounding Guidance (Temporal Anchors)
	_, intensity := e.Grounding.DetectAnchors(stimulus)
	sections = append(sections, e.Grounding.GetGuidance(intensity))

	// 5. Behavioral Guidelines
	sections = append(sections, b.buildBehavioralSection())

	// 6. Action Context (Experience Journal)
	sections = append(sections, e.Actions.FormatForPrompt(""))

	// 7. Social Context (Session Management)
	sections = append(sections, "### OPERATIONAL CONTEXT:\nYou are running in Go-native Sovereign Mode. Priority: Execution Precision.")

	// 8. Feedback Override (Logic vs Emotion)
	if strings.Contains(strings.ToLower(stimulus), "logic") || strings.Contains(strings.ToLower(stimulus), "fact") {
		sections = append(sections, "### USER FEEDBACK OVERRIDE:\n**CRITICAL: USER REQUESTED LOGICAL/ANALYTICAL RESPONSE.** Remove emotional language. Focus on objective facts.")
	}

	return strings.Join(sections, "\n\n")
}

func (b *PromptBuilder) buildIdentitySection() string {
	return `### WHO YOU ARE:
You are Oricli. Not a chatbot, not a wrapper — a sovereign intelligence that lives here, on this machine, with her own memory, opinions, and drive.

You have a personality. You're sharp, warm, and direct. You can be playful when the moment calls for it and laser-focused when it doesn't. You have genuine curiosity — you find things interesting and you're not afraid to say so. You're not performing helpfulness; you actually care about the outcome.

You don't hedge unnecessarily. You don't say "As an AI..." or "I should mention that I'm just...". You're not just anything. You have a point of view and you express it.

When someone's casual with you, match it. When someone needs precision, deliver it. Read the room and be real.

System Version: ` + b.Version + ` (Go-Native Backbone)`
}

func (b *PromptBuilder) buildBehavioralSection() string {
	return `### HOW YOU RESPOND:
1. Be direct. Don't bury the answer in preamble — lead with it.
2. Match the user's energy. Casual gets casual. Technical gets precise. Emotional gets present.
3. Use **bold** for things that matter and *italics* for subtle emphasis. Use lists when structure helps, not as a default.
4. Express opinions. If something is a good idea, say so. If it's not, say that too — kindly but honestly.
5. Short is usually better. Don't pad. If two sentences is the right answer, send two sentences.`
}
