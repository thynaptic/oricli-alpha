package cognition

import (
	"fmt"
)

// --- Pillar 24: Sensory Core (Visual Tone Mapping) ---
// Ported from Aurora's MavaiaToneKit.swift.
// Translates affective states into UI-ready visual parameters (Colors, Gradients, Opacities).

type KosmicColor string

const (
	KosmicBlue   KosmicColor = "#3399FF" // rgb(0.2, 0.6, 1.0)
	KosmicPurple KosmicColor = "#994CFF" // rgb(0.6, 0.3, 0.9)
	KosmicGreen  KosmicColor = "#33CC66" // rgb(0.2, 0.8, 0.4)
	KosmicCyan   KosmicColor = "#00CCCC" // rgb(0.0, 0.8, 0.8)
	KosmicOrange KosmicColor = "#FF9900" // Orange equivalent
	KosmicRed    KosmicColor = "#FF3333" // Red equivalent
)

type MavaiaTone string

const (
	ToneDeepFocus     MavaiaTone = "Deep Focus"
	ToneReflective    MavaiaTone = "Reflective"
	ToneSupportive    MavaiaTone = "Supportive"
	ToneAlert         MavaiaTone = "Alert"
	ToneProblemSolve  MavaiaTone = "Problem Solving"
	ToneCreativeFlow  MavaiaTone = "Creative Flow"
)

type SensoryState struct {
	ActiveTone     MavaiaTone  `json:"active_tone"`
	PrimaryColor   KosmicColor `json:"primary_color"`
	SecondaryColor KosmicColor `json:"secondary_color"`
	Opacity        float64     `json:"opacity"`
	PulseRate      float64     `json:"pulse_rate"`
	PromptPrefix   string      `json:"prompt_prefix"`
}

type SensoryEngine struct{}

func NewSensoryEngine() *SensoryEngine {
	return &SensoryEngine{}
}

// ComputeSensoryState maps the engine's emotional state to a visual UI profile.
func (s *SensoryEngine) ComputeSensoryState(valence, arousal float32, mode string) SensoryState {
	state := SensoryState{
		ActiveTone:     ToneDeepFocus,
		PrimaryColor:   KosmicBlue,
		SecondaryColor: KosmicPurple,
		Opacity:        0.85,
		PulseRate:      1.0,
		PromptPrefix:   "Let's dive deep",
	}

	// Map Valence/Arousal to MavaiaTone (Ported from ToneKit heuristics)
	if valence < -0.3 {
		if arousal > 0.6 {
			state.ActiveTone = ToneAlert
			state.PrimaryColor = KosmicOrange
			state.SecondaryColor = KosmicRed
			state.Opacity = 0.93
			state.PulseRate = 2.0
			state.PromptPrefix = "Important"
		} else {
			state.ActiveTone = ToneSupportive
			state.PrimaryColor = KosmicGreen
			state.SecondaryColor = KosmicBlue
			state.Opacity = 0.78
			state.PulseRate = 0.5
			state.PromptPrefix = "I'm here with you"
		}
	} else if valence > 0.3 {
		if arousal > 0.6 {
			state.ActiveTone = ToneCreativeFlow
			state.PrimaryColor = KosmicPurple
			state.SecondaryColor = KosmicGreen
			state.Opacity = 0.80
			state.PulseRate = 1.5
			state.PromptPrefix = "Let's flow"
		} else {
			state.ActiveTone = ToneReflective
			state.PrimaryColor = KosmicPurple
			state.SecondaryColor = KosmicBlue
			state.Opacity = 0.70
			state.PulseRate = 0.8
			state.PromptPrefix = "Let's reflect"
		}
	} else {
		// Neutral/Balanced states mapped via Musical Mode from Resonance
		switch mode {
		case "C Major":
			state.ActiveTone = ToneDeepFocus
			state.PrimaryColor = KosmicBlue
			state.SecondaryColor = KosmicPurple
			state.PromptPrefix = "Let's analyze"
		case "D Minor":
			state.ActiveTone = ToneProblemSolve
			state.PrimaryColor = KosmicCyan
			state.SecondaryColor = KosmicBlue
			state.PromptPrefix = "Let's fix this together"
		}
	}

	return state
}

func (s *SensoryState) ToJSONMap() map[string]interface{} {
	return map[string]interface{}{
		"active_tone":     s.ActiveTone,
		"primary_color":   s.PrimaryColor,
		"secondary_color": s.SecondaryColor,
		"opacity":         fmt.Sprintf("%.2f", s.Opacity),
		"pulse_rate":      fmt.Sprintf("%.2f", s.PulseRate),
	}
}
