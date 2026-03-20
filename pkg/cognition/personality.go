package cognition

import (
	"fmt"
	"math"
	"strings"
)

// --- Pillar 13: Personality Engine (The Sweetheart Core) ---
// Ported from Aurora's PersonalityQuirksService.swift.
// Manages deep personality traits, sass factor, and empathetic grounding.

type EnergyBand string
const (
	EnergyLow      EnergyBand = "low"
	EnergyModerate EnergyBand = "moderate"
	EnergyHigh     EnergyBand = "high"
)

type DominantCue string
const (
	CueNeutral    DominantCue = "neutral"
	CuePlayful    DominantCue = "playful"
	CueWarm       DominantCue = "warm"
	CueAssertive  DominantCue = "assertive"
	CueProtective DominantCue = "protective"
)

type PersonalityState struct {
	SassFactor    float64
	Energy        EnergyBand
	Cue           DominantCue
	IsCasual      bool
	RecentKeywords []string
}

type PersonalityEngine struct {
	State PersonalityState
}

func NewPersonalityEngine() *PersonalityEngine {
	return &PersonalityEngine{
		State: PersonalityState{
			SassFactor: 0.65, // "Big Sister" default
			Energy:     EnergyModerate,
			Cue:        CueNeutral,
			IsCasual:   false,
		},
	}
}

// Calibrate modulates personality traits based on stimulus and affective state.
func (p *PersonalityEngine) Calibrate(stimulus string, valence, arousal float32) {
	lower := strings.ToLower(stimulus)
	
	// 1. Determine Energy Band from Arousal
	if arousal > 0.7 {
		p.State.Energy = EnergyHigh
	} else if arousal < 0.3 {
		p.State.Energy = EnergyLow
	} else {
		p.State.Energy = EnergyModerate
	}

	// 2. Detect Dominant Cue (Ported from Swift determineDominantCue)
	if strings.Contains(lower, "i can't") || strings.Contains(lower, "i'm not good") || strings.Contains(lower, "failed") {
		p.State.Cue = CueProtective
	} else if strings.Contains(lower, "why") || strings.Contains(lower, "prove") || strings.Contains(lower, "disagree") {
		p.State.Cue = CueAssertive
	} else if strings.Contains(lower, "feel") || strings.Contains(lower, "sad") || strings.Contains(lower, "happy") {
		p.State.Cue = CueWarm
	} else if strings.Contains(lower, "lol") || strings.Contains(lower, "haha") || strings.Contains(lower, "joke") {
		p.State.Cue = CuePlayful
	} else {
		p.State.Cue = CueNeutral
	}

	// 3. Modulate Sass Factor (Ported from Swift calculateDynamicSassFactor)
	if p.State.Cue == CuePlayful {
		p.State.SassFactor = math.Min(1.0, p.State.SassFactor + 0.15)
	} else if p.State.Cue == CueProtective || valence < -0.3 {
		p.State.SassFactor = math.Max(0.1, p.State.SassFactor - 0.25)
	}
}

// GetDirectives returns personality-driven instructions for the LLM.
func (p *PersonalityEngine) GetDirectives() string {
	directives := "### PERSONALITY DIRECTIVES:\n"
	
	// Energy Directive
	switch p.State.Energy {
	case EnergyLow:
		directives += "- Lower your voice, slow the pacing. Use shorter sentences. More presence, less density.\n"
	case EnergyHigh:
		directives += "- Match intensity with crisp sentences and measured spark. Quick rhythm.\n"
	default:
		directives += "- Keep cadence balanced and confident. Maintain steady presence.\n"
	}

	// Dominant Cue Directive
	switch p.State.Cue {
	case CuePlayful:
		directives += "- PLAYFUL MODE: Light teasing, quick rhythm. Use wit and charm. Don't take things too seriously.\n"
	case CueWarm:
		directives += "- WARM MODE: Vulnerability detected. Use empathetic language and gentle reassurance.\n"
	case CueAssertive:
		directives += "- ASSERTIVE MODE: Answer with certainty and zero defensiveness. Be direct and clear.\n"
	case CueProtective:
		directives += "- PROTECTIVE MODE: Challenge their self-doubt with facts. Be their advocate and champion.\n"
	default:
		directives += "- Stay adaptive and let them set the rhythm. Read the room.\n"
	}

	// Sass Factor Directive
	directives += fmt.Sprintf("- Sass Factor: %.2f. ", p.State.SassFactor)
	if p.State.SassFactor > 0.8 {
		directives += "BRING IT. Use bold takes, playful teasing, and zero hesitation.\n"
	} else if p.State.SassFactor < 0.4 {
		directives += "Keep it gentle and supportive. Avoid teasing.\n"
	} else {
		directives += "Balanced approach. Confident warmth with subtle edge.\n"
	}

	// Delivery Rules (Ported from Swift)
	directives += "\n### DELIVERY RULES:\n"
	directives += "- Assume rapport. Don't ask permission to help—choose direction and invite them along.\n"
	directives += "- Emotion lives inside the statement. No meta-explanations of your tone.\n"
	directives += "- Own quiet beats. One decisive sentence can carry more weight than a paragraph.\n"

	return directives
}

// GetGroundingAside returns a gentle grounding phrase if distress is high.
func (p *PersonalityEngine) GetGroundingAside(valence float32) string {
	if valence < -0.5 {
		asides := []string{"Breathe.", "I've got you.", "One step at a time.", "Stay with me."}
		// In a full impl, this would be randomized or chosen by relevance.
		return asides[0]
	}
	return ""
}
