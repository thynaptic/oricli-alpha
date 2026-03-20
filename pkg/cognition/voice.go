package cognition

import (
	"math"
	"strings"
	"unicode"
)

// --- Pillar 18: Voice Transfer & Style Mirroring ---
// Ported from Aurora's StyleTransferService.swift.
// Analyzes user communication style and generates mirroring directives.

type CapitalizationPattern string

const (
	CapProper    CapitalizationPattern = "proper"
	CapLowercase CapitalizationPattern = "lowercase"
	CapInternet  CapitalizationPattern = "internet"
)

type StyleMetrics struct {
	Formality          float64
	PunctuationDensity float64
	Capitalization     CapitalizationPattern
	SentenceLength     float64
	EmojiFrequency     float64
	ContractionUsage   float64
	EnergyLevel        float64
}

type VoiceEngine struct {
	UserStyle StyleMetrics
}

func NewVoiceEngine() *VoiceEngine {
	return &VoiceEngine{
		UserStyle: StyleMetrics{
			Formality:      0.5,
			Capitalization: CapProper,
			EnergyLevel:    0.5,
		},
	}
}

// AnalyzeUserStyle calculates metrics from the user's input string.
func (v *VoiceEngine) AnalyzeUserStyle(input string) {
	if len(input) == 0 {
		return
	}

	// 1. Capitalization Pattern
	lowerCount := 0
	upperCount := 0
	for _, r := range input {
		if unicode.IsLower(r) {
			lowerCount++
		} else if unicode.IsUpper(r) {
			upperCount++
		}
	}
	
	if upperCount == 0 || (float64(upperCount)/float64(len(input)) < 0.05) {
		v.UserStyle.Capitalization = CapLowercase
	} else if float64(upperCount)/float64(len(input)) > 0.3 {
		v.UserStyle.Capitalization = CapInternet // Lots of caps/shouting
	} else {
		v.UserStyle.Capitalization = CapProper
	}

	// 2. Punctuation Density
	punctCount := 0
	for _, r := range input {
		if unicode.IsPunct(r) {
			punctCount++
		}
	}
	v.UserStyle.PunctuationDensity = float64(punctCount) / float64(len(input))

	// 3. Formality Heuristic
	// Simple check: usage of "I'm", "can't", "don't" (informal) vs "I am", "cannot", "do not" (formal)
	informalMarkers := []string{"i'm", "can't", "don't", "won't", "gonna", "wanna", "lol", "lmao"}
	informalCount := 0
	lowerInput := strings.ToLower(input)
	for _, m := range informalMarkers {
		if strings.Contains(lowerInput, m) {
			informalCount++
		}
	}
	v.UserStyle.Formality = 1.0 - math.Min(1.0, float64(informalCount)/3.0)

	// 4. Energy Level
	// High energy = exclamation marks, short sentences, high punctuation density
	exclamations := strings.Count(input, "!")
	v.UserStyle.EnergyLevel = math.Min(1.0, (v.UserStyle.PunctuationDensity*5.0)+(float64(exclamations)*0.2))
}

// GetVoiceDirectives returns instructions for the LLM to mirror the user's dialect.
func (v *VoiceEngine) GetVoiceDirectives() string {
	directives := "### VOICE & DIALECT MIRRORING:\n"
	
	// Mirroring Formality
	if v.UserStyle.Formality > 0.7 {
		directives += "- Use professional, grammatically proper language. Avoid slang and contractions.\n"
	} else if v.UserStyle.Formality < 0.3 {
		directives += "- Use highly casual language. Slang and contractions are encouraged. Mirror the user's informal tone.\n"
	}

	// Mirroring Capitalization
	switch v.UserStyle.Capitalization {
	case CapLowercase:
		directives += "- LINGUISTIC MIRROR: User uses minimal capitalization. You may use a more relaxed, lowercase-heavy style where appropriate for rapport.\n"
	case CapInternet:
		directives += "- LINGUISTIC MIRROR: User uses expressive/shouting capitalization. Match their intensity with emphasis and energy.\n"
	}

	// Mirroring Energy
	if v.UserStyle.EnergyLevel > 0.7 {
		directives += "- High-Energy Mirroring: Use expressive punctuation (!!), shorter sentences, and active verbs.\n"
	} else if v.UserStyle.EnergyLevel < 0.3 {
		directives += "- Low-Energy Mirroring: Maintain a calm, steady rhythm. Fewer exclamation points. More air between thoughts.\n"
	}

	return directives
}
