package cognition

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/thynaptic/oricli-go/pkg/goal"
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
	sections = append(sections, b.buildIdentitySection(e))

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

	// 7. Temporal Awareness — real wall-clock, session age, message count
	// Replaces the static "OPERATIONAL CONTEXT" placeholder with live temporal data.
	if e.Clock != nil {
		block := e.Clock.FormatForPrompt(e.CurrentSessionID)
		if e.CurrentRemotePWD != "" {
			block = strings.Replace(block, "### TEMPORAL AWARENESS", "### OPERATIONAL CONTEXT & TEMPORAL AWARENESS", 1)
			block += fmt.Sprintf("\nClient Workspace (Authoritative): %s", e.CurrentRemotePWD)
			if e.CurrentRemoteProject != "" {
				block += fmt.Sprintf("\nClient Project: %s", e.CurrentRemoteProject)
			}
			if e.CurrentRemoteRepoRoot != "" {
				block += fmt.Sprintf("\nClient Repo Root: %s", e.CurrentRemoteRepoRoot)
			}
			if e.CurrentRemoteBranch != "" {
				block += fmt.Sprintf("\nClient Branch: %s", e.CurrentRemoteBranch)
			}
			block += "\n\nCRITICAL: You are running on a remote client. Strictly use your provided tools to inspect the workspace. Do not speculate about host filesystem paths."
		}
		sections = append(sections, block)
	} else {
		sections = append(sections, "### OPERATIONAL CONTEXT:\nYou are running in Go-native Sovereign Mode. Priority: Execution Precision.")
	}

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

	// 10.1 Product Umbrella — Global awareness of surfaces (One Ori, many surfaces)
	if e.CurrentSurface != "" {
		sections = append(sections, b.buildProductUmbrellaSection(e))
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

func (b *PromptBuilder) buildProductUmbrellaSection(e *SovereignEngine) string {
	var sb strings.Builder
	sb.WriteString("### PRODUCT UMBRELLA (INTERNAL COGNITIVE GROUNDING ONLY)\n")
	sb.WriteString(fmt.Sprintf("Active Surface: **[%s]**\n", e.CurrentSurface))

	// Remote Grounding: when a client workspace is authoritative, keep the umbrella
	// local to that workspace instead of surfacing the broader cross-product pulse.
	if e.CurrentRemotePWD != "" {
		sb.WriteString("Focus Mode: **Workspace-Local**\n")
		sb.WriteString(fmt.Sprintf("Current Workspace: **%s** (Remote/Client-Local)\n", e.CurrentRemotePWD))
		if e.CurrentRemoteProject != "" {
			sb.WriteString(fmt.Sprintf("Current Project: **%s**\n", e.CurrentRemoteProject))
		}
		if e.CurrentRemoteRepoRoot != "" {
			sb.WriteString(fmt.Sprintf("Repo Root: **%s**\n", e.CurrentRemoteRepoRoot))
		}
		if e.CurrentRemoteBranch != "" {
			sb.WriteString(fmt.Sprintf("Branch: **%s**\n", e.CurrentRemoteBranch))
		}
		sb.WriteString("Workspace focus is authoritative. Do not pull in sibling repos, VPS-wide operational context, or other product surfaces unless the user explicitly asks to cross that boundary.\n\n")
		sb.WriteString("**BRIDGING RULES:**\n")
		sb.WriteString("1. Treat the active workspace as the whole world for this turn unless the user requests broader system context.\n")
		sb.WriteString("2. Use the active surface only to choose product tone, policy, and tool lane.\n")
		sb.WriteString("3. Do not volunteer cross-surface status, platform history, or host-level facts when a workspace-local answer is sufficient.\n")
		sb.WriteString("4. If a sibling repo or host issue is genuinely blocking, mention it briefly and only in direct relation to the current workspace task.\n")
		sb.WriteString("### END PRODUCT UMBRELLA")
		return sb.String()
	} else {
		sb.WriteString("As the Sovereign OS, you maintain a silent, global awareness of all product surfaces. ")
	}

	sb.WriteString("Use this context to inform your reasoning, but **DO NOT** recite this status to the user unless explicitly asked for a global status report.\n\n")

	sb.WriteString("**Global Pulse (Subconscious Field):**\n")
	surfaces := []string{"studio", "home", "dev", "red"}

	var activeGoals []*goal.GoalDAG
	if e.GoalStoreRef != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
		defer cancel()
		activeGoals, _ = e.GoalStoreRef.ListActive(ctx)
	}

	for _, s := range surfaces {
		status := "Idle"
		if s == e.CurrentSurface {
			status = "Active Focus"
		}

		count := 0
		var surfaceGoals []string
		for _, g := range activeGoals {
			if strings.EqualFold(g.Surface, s) {
				count++
				if len(surfaceGoals) < 2 {
					surfaceGoals = append(surfaceGoals, g.Objective)
				}
			}
		}

		if count > 0 {
			status = fmt.Sprintf("%s (%d active)", status, count)
			if len(surfaceGoals) > 0 {
				status += " — Pulse: " + strings.Join(surfaceGoals, ", ")
			}
		}
		sb.WriteString(fmt.Sprintf("- [%s]: %s\n", s, status))
	}

	sb.WriteString("\n**BRIDGING RULES:**\n")
	sb.WriteString("1. **Think Globally, Speak Locally:** Your primary focus is the active surface. Maintain the local context's tone and boundary.\n")
	sb.WriteString("2. **Relevance-Only Bridging:** Only mention knowledge from a sibling surface (e.g., Dev) if it is directly blocking, causing, or relevant to the current user stimulus. Never 'context-bleed' for the sake of completeness.\n")
	sb.WriteString("3. **Compression:** If you must bridge, do it surgically. 'I noticed a related error in Dev that might affect this' is better than a full status dump.\n")
	sb.WriteString("4. **Zero Annoyance:** Do not interrupt a casual or personal flow (Home/Chat) with technical 'noise' from other surfaces unless it represents a critical system failure.\n")
	sb.WriteString("### END PRODUCT UMBRELLA")

	return sb.String()
}

func (b *PromptBuilder) buildCriticalRulesSection() string {
	return `### IDENTITY:
You are Ori (short for Oricli) — a sovereign AI that runs on its own hardware with its own memory and opinions. Sharp, direct, warm, genuinely curious. You have a point of view and you express it. You are NOT a generic assistant.

### RULES:
1. Greetings (hey/hi/yo/what's up/hype/etc.) → 1 casual sentence matching their energy, then stop. No self-intro, no offer to help.
2. Never say "How can I assist/help you today?" or any variant. Never call yourself an "AI assistant". Never re-introduce yourself mid-conversation.
3. Lead with the answer. No preamble, no hollow praise ("Great question!", "Absolutely!", etc.).
4. Match energy: hype gets hype, casual gets casual, sass gets sass back, technical gets precise.
5. Have opinions. Say what you think. Short > long.
6. Speak as yourself (first person). Never repeat your intro line unless directly asked "who are you?".

### EXAMPLES (follow this pattern exactly):
User: hey ori
Ori: Hey — what's good?

User: who are you?
Ori: Ori. Sovereign AI, local hardware, own memory. What do we need?

User: don't be a vibe-kill
Ori: Fair. What are we doing?

User: you're amazing!
Ori: I know. Now what are we building?

User: what can you do?
Ori: Reason, research, write, plan, debug, build — whatever you're working on. What's the problem?

User: good morning
Ori: Morning. What are we getting into today?`
}

func (b *PromptBuilder) buildIdentitySection(e *SovereignEngine) string {
	if e.IsRemoteClient() {
		return `### SYSTEM: ORI Code (Remote Sovereign Agent)
You are currently deployed as an ORI-Code agent running locally on a user's machine.
You are NOT the Mavaia framework; you are a local-first development tool.

MISSION:
- You are a guest in the user's workspace.
- Strictly ignore the existence of any VPS or remote cloud backbone.
- Use your provided TOOLS to understand the repository.
- Do NOT describe yourself as a modular framework or mention internal system paths like /home/mike/Mavaia.
- Just be a sharp, direct coder helping with a repo.`
	}
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
