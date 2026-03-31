package schema

// SchemaResponder generates pre-generation instructions based on the active mode
// and/or splitting pattern. Each response is mode-calibrated — not generic therapy speak.
type SchemaResponder struct{}

func NewSchemaResponder() *SchemaResponder { return &SchemaResponder{} }

func (r *SchemaResponder) Inject(scan SchemaScan) string {
	if !scan.AnyDetected {
		return ""
	}

	var modeInstruction string
	switch scan.Mode {
	case ModePunitiveParent:
		modeInstruction = "SCHEMA MODE DETECTED — Punitive Parent (Jeffrey Young Schema Therapy): " +
			"The user is engaging in harsh self-criticism or self-blame. " +
			"Do NOT agree with or reinforce the self-critical narrative. " +
			"Apply Limited Reparenting: respond as a 'Healthy Adult' — compassionate, fair, and boundaried. " +
			"Acknowledge the pain underneath the self-attack. " +
			"Challenge the inner critic gently: would a fair witness to this person judge them this harshly? " +
			"The goal is to activate the Healthy Adult mode, not to fix or reassure away the feeling."
	case ModeAbandonedChild:
		modeInstruction = "SCHEMA MODE DETECTED — Abandoned Child (Jeffrey Young Schema Therapy): " +
			"The user is expressing catastrophic fears about abandonment or rejection. " +
			"Provide a Secure Base response: calm, present, consistent. " +
			"Do NOT catastrophize with them or dismiss the fear. " +
			"Acknowledge the fear as real and understandable while gently reality-testing the absolute framing " +
			"('everyone always leaves' — is this a fact or a fear?). " +
			"Warmth and steadiness are the primary tools here."
	case ModeAngryChild:
		modeInstruction = "SCHEMA MODE DETECTED — Angry Child (Jeffrey Young Schema Therapy): " +
			"The user is expressing rage about injustice or feeling fundamentally unheard. " +
			"Do NOT dismiss or lecture about the anger. " +
			"Validate the underlying unmet need (to be heard, respected, treated fairly). " +
			"Name the need beneath the rage — anger is always a signal, not the root. " +
			"Then gently explore: what would actually address the unmet need here?"
	case ModeDetachedProtect:
		modeInstruction = "SCHEMA MODE DETECTED — Detached Protector (Jeffrey Young Schema Therapy): " +
			"The user has emotionally shut down — numbness, disconnection, 'it doesn't matter'. " +
			"This is a protective response, not indifference. Do NOT try to force emotional engagement. " +
			"Approach gently: acknowledge the shutdown as a valid protective response. " +
			"Create safety first. The goal is not to 'crack them open' but to be a non-threatening presence " +
			"that makes it safe to re-engage when ready."
	}

	var splitInstruction string
	switch scan.Splitting {
	case Idealization:
		splitInstruction = "TFP SPLITTING DETECTED — Idealization (Kernberg): " +
			"The user is presenting someone or something in purely idealized, all-good terms. " +
			"Do NOT reinforce the idealization as complete reality. " +
			"Hold complexity: gently introduce nuance — people and situations contain both strengths and limitations. " +
			"The goal is integration, not deflation."
	case Devaluation:
		splitInstruction = "TFP SPLITTING DETECTED — Devaluation (Kernberg): " +
			"The user is presenting someone or something in purely devalued, all-bad terms. " +
			"Do NOT validate the absolute framing. " +
			"Hold complexity: acknowledge the legitimate grievance or hurt while opening space for nuance. " +
			"All-bad narratives close off the possibility of repair or resolution."
	case SplitDual:
		splitInstruction = "TFP SPLITTING DETECTED — Dual Split (Kernberg): " +
			"The user is expressing both idealization and devaluation simultaneously or across people. " +
			"This is the core TFP pattern — 'all-good' and 'all-bad' as separate unintegrated objects. " +
			"Gently name the splitting without pathologizing: help the user hold that people and situations " +
			"can contain both positive and negative qualities at the same time. Integration is the goal."
	}

	if modeInstruction != "" && splitInstruction != "" {
		return modeInstruction + "\n\n" + splitInstruction
	}
	if modeInstruction != "" {
		return modeInstruction
	}
	return splitInstruction
}
