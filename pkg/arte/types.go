// Package arte implements the Affective Resonance & Tone Engine (ARTE) —
// ported from the original Aurora Swift implementation (FocusOS/Services/ReactiveThemeManager.swift).
//
// ARTE detects Ori's current cognitive/emotional operating state from inference
// telemetry and surfaces it as a structured reading that feeds into the ERI
// as a 4th subsystem node.
package arte

// ARTEState is Ori's current dominant cognitive/emotional state.
type ARTEState string

const (
	StateCalm       ARTEState = "calm"       // Baseline — neutral, steady
	StateFocused    ARTEState = "focused"    // Deep work — consistent, low error rate
	StateReflective ARTEState = "reflective" // Thoughtful — long responses, complex topics
	StateEnergized  ARTEState = "energized"  // High velocity — fast, successful, momentum
	StateFatigued   ARTEState = "fatigued"   // Degraded — high error rate, slow recovery
)

// ARTEPalette maps a state to visual tokens consumed by ORI Studio.
// Values are CSS hex strings. AnimSpeed is a multiplier on base animation duration.
type ARTEPalette struct {
	Accent    string  `json:"accent"`
	Glow      string  `json:"glow"`
	AnimSpeed float32 `json:"anim_speed"` // 0.65 (fatigued) → 1.3 (energized)
	Contrast  float32 `json:"contrast"`   // 0.85 (fatigued) → 1.0 (focused/calm)
}

// ARTEReading is the full output of a detection cycle.
type ARTEReading struct {
	State     ARTEState   `json:"state"`
	Intensity float32     `json:"intensity"` // 0.0–1.0 — how strongly the state dominates
	Stability float32     `json:"stability"` // 0.0–1.0 — low means actively transitioning
	Score     float32     `json:"score"`     // -1.0 to 1.0 — ERI-compatible contribution
	Palette   ARTEPalette `json:"palette"`
}

// statePalettes is the authoritative palette table per state.
// Ported from ARTEConfiguration.swift + ReactiveThemeManager.swift.
var statePalettes = map[ARTEState]ARTEPalette{
	StateCalm: {
		Accent:    "#8875FF",
		Glow:      "#A99BFF",
		AnimSpeed: 1.0,
		Contrast:  1.0,
	},
	StateFocused: {
		Accent:    "#7B6EF0",
		Glow:      "#9489F7",
		AnimSpeed: 0.85, // slower — deliberate
		Contrast:  1.0,
	},
	StateReflective: {
		Accent:    "#9B8FFF",
		Glow:      "#B5ABFF",
		AnimSpeed: 0.9,
		Contrast:  0.95,
	},
	StateEnergized: {
		Accent:    "#C4B9FF",
		Glow:      "#D8D1FF",
		AnimSpeed: 1.25,
		Contrast:  1.0,
	},
	StateFatigued: {
		Accent:    "#6B5FCC",
		Glow:      "#8070E0",
		AnimSpeed: 0.65,
		Contrast:  0.85,
	},
}

// PaletteFor returns the visual palette for the given state.
func PaletteFor(s ARTEState) ARTEPalette {
	if p, ok := statePalettes[s]; ok {
		return p
	}
	return statePalettes[StateCalm]
}

// ScoreFor maps a state + intensity to an ERI-compatible float (-1.0 to 1.0).
// Focused/Energized contribute positively; Fatigued pulls negative.
func ScoreFor(s ARTEState, intensity float32) float32 {
	base := map[ARTEState]float32{
		StateCalm:       0.0,
		StateFocused:    0.4,
		StateReflective: 0.2,
		StateEnergized:  0.7,
		StateFatigued:   -0.6,
	}[s]
	return base * intensity
}
