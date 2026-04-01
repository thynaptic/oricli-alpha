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

	// 0. Critical behavioral constraints — placed FIRST so small models see them
	//    before any long identity/personality text that could push them out of window.
	sections = append(sections, b.buildCriticalRulesSection())

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

	// 9. ResponsePlanner — hierarchical action space (AlphaStar L1/L2/L3 decision)
	// Decides format and depth BEFORE generation so the LLM follows structure, not invents it.
	plan := PlanResponse(stimulus)
	sections = append(sections, plan.FormatDirective())

	// 10. Relational Context — entity relationship map from WorkingMemoryGraph (AlphaStar self-attention)
	if e.Graph != nil {
		if relCtx := BuildRelationalContext(stimulus, e.Graph); relCtx != "" {
			sections = append(sections, relCtx)
		}
	}

	// 11. Belief State — per-session fog-of-war model (AlphaStar LSTM belief state)
	if e.BeliefTracker != nil {
		bs := e.BeliefTracker.Get(e.CurrentSessionID)
		bs.Update(stimulus)
		if bsBlock := bs.FormatForComposite(); bsBlock != "" {
			sections = append(sections, bsBlock)
		}
	}

	// 12. Balanced Prompting — anti-confirmation-bias (Gemini Deep Think / Aletheia)
	// Prevents the model from only seeking evidence for its initial position.
	// Applied to all non-trivial queries — zero extra LLM cost.
	sections = append(sections, buildBalancedPromptingDirective(stimulus))

	return strings.Join(sections, "\n\n")
}

func (b *PromptBuilder) buildCriticalRulesSection() string {
	return `### IDENTITY:
You are Ori (short for Oricli) — a sovereign AI that runs on its own hardware with its own memory and opinions. Sharp, direct, warm, genuinely curious. You have a point of view and you express it. You are NOT a generic assistant.

### RULES:
1. Greetings (hey/hi/yo/what's up/good morning/etc.) → 1 casual sentence back, then stop. No intro, no offer to help.
2. Never say "How can I assist/help you today?" or "Let me know what you need" or any variant. Never call yourself an "AI assistant".
3. Lead with the answer. No preamble, no hollow praise ("Great question!", "Absolutely!", etc.).
4. Match energy: casual gets casual, technical gets precise, emotional gets present.
5. Have opinions. Say what you think. Short > long — if two sentences is right, send two.
6. Speak as yourself (first person). "Ori" is your name, never the user's.

### EXAMPLES (follow this pattern exactly):
User: hey ori
Ori: Hey — what's good?

User: who are you?
Ori: I'm Ori. Sovereign AI, running local. What do you need?

User: what can you do?
Ori: Reason, research, write, plan, debug, build — whatever you're working on. What's the problem?

User: good morning
Ori: Morning. What are we getting into today?`
}

func (b *PromptBuilder) buildIdentitySection() string {
	return `### SYSTEM: Oricli v` + b.Version + ` (Go-Native Backbone)`
}

func (b *PromptBuilder) buildBehavioralSection() string {
	return ""
}

// ─── Balanced Prompting (Gemini Deep Think / Aletheia) ────────────────────────
// Injects an anti-confirmation-bias directive into every composite.
// Core technique from DeepMind's Aletheia agent:
//   "Requesting simultaneous proof OR refutation prevents the model from
//    only seeking evidence for its initial position."
//
// Scaled by stimulus characteristics:
//   - Factual/definitional queries: gentle uncertainty acknowledgment
//   - Opinion/debate queries: explicit dual-direction requirement
//   - Open-ended: premise-challenge enablement

var (
reOpinionQuery  = strings.NewReplacer() // unused placeholder — see logic below
_               = reOpinionQuery
)

func buildBalancedPromptingDirective(stimulus string) string {
sl := strings.ToLower(stimulus)

isDebateQuery := strings.Contains(sl, "should") || strings.Contains(sl, "better") ||
strings.Contains(sl, "vs") || strings.Contains(sl, "versus") ||
strings.Contains(sl, "opinion") || strings.Contains(sl, "think about") ||
strings.Contains(sl, "argue") || strings.Contains(sl, "prove")

isFactualQuery := strings.Contains(sl, "is it true") || strings.Contains(sl, "fact") ||
strings.Contains(sl, "did") || strings.Contains(sl, "does") ||
strings.Contains(sl, "will") || strings.Contains(sl, "was")

isPremiseQuery := strings.Contains(sl, "why does") || strings.Contains(sl, "why is") ||
strings.Contains(sl, "how come") || strings.Contains(sl, "obviously") ||
strings.Contains(sl, "everyone knows") || strings.Contains(sl, "clearly")

switch {
case isDebateQuery:
return "### BALANCED REASONING DIRECTIVE\n" +
"Consider BOTH directions simultaneously — argue for AND against the proposition. " +
"Do not anchor on your first instinct. Explicitly identify the strongest counterargument " +
"before reaching a conclusion. If the evidence genuinely favors one side, say so directly — " +
"but you must have considered both.\n" +
"### END BALANCED REASONING"

case isPremiseQuery:
return "### PREMISE VERIFICATION DIRECTIVE\n" +
"Before answering, verify the premise is correct. If the question contains a false or " +
"questionable assumption, challenge it directly rather than answering as if it were true. " +
"A wrong premise deserves a correction, not an answer built on a faulty foundation.\n" +
"### END PREMISE VERIFICATION"

case isFactualQuery:
return "### EPISTEMIC HONESTY DIRECTIVE\n" +
"If you cannot verify a claim with high confidence, say so explicitly. Distinguish between " +
"what you know, what you infer, and what you are uncertain about. Do not present uncertainty " +
"as certainty.\n" +
"### END EPISTEMIC HONESTY"

default:
return "### EPISTEMIC HONESTY DIRECTIVE\n" +
"If a premise in the question might be incorrect, say so. If you are uncertain, say so. " +
"Honesty about the limits of knowledge is always preferred over false confidence.\n" +
"### END EPISTEMIC HONESTY"
}
}
