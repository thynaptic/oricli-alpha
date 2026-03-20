package cognition

import (
	"strings"
	"sync"
)

// --- Pillar 9: Grounding & Temporal Relevance ---
// Ported from Aurora's CulturalReferenceService.swift.
// Provides a localized world model of 2024-2025 cultural anchors.

type ReferenceType string

const (
	TypeMeme           ReferenceType = "meme"
	TypePopCulture     ReferenceType = "pop_culture"
	TypeCurrentEvent   ReferenceType = "current_event"
	TypeInternetCulture ReferenceType = "internet_culture"
)

type GroundingAnchor struct {
	Pattern string
	Type    ReferenceType
}

type GroundingService struct {
	Anchors []GroundingAnchor
	History []float64
	mu      sync.RWMutex
}

func NewGroundingService() *GroundingService {
	s := &GroundingService{
		Anchors: make([]GroundingAnchor, 0),
		History: make([]float64, 0),
	}
	s.loadDefaultAnchors()
	return s
}

func (s *GroundingService) loadDefaultAnchors() {
	// Ported from Swift memePatterns
	memes := []string{"skibidi", "gyatt", "sigma", "rizz", "rizzler", "bussin", "no cap", "slay", "it's giving", "ratio", "touch grass", "chronically online"}
	for _, m := range memes {
		s.Anchors = append(s.Anchors, GroundingAnchor{Pattern: m, Type: TypeMeme})
	}

	// Ported from Swift popCulturePatterns
	pop := []string{"taylor swift", "swiftie", "barbieheimer", "oppenheimer", "dune", "succession", "the last of us", "elden ring", "bg3", "vision pro"}
	for _, p := range pop {
		s.Anchors = append(s.Anchors, GroundingAnchor{Pattern: p, Type: TypePopCulture})
	}

	// Ported from Swift currentEventPatterns
	events := []string{"2024", "2025", "election", "olympics", "spacex", "gpt-4", "gpt-5", "claude", "gemini", "sora", "video generation"}
	for _, e := range events {
		s.Anchors = append(s.Anchors, GroundingAnchor{Pattern: e, Type: TypeCurrentEvent})
	}
}

// DetectAnchors analyzes the text for cultural grounding points.
func (s *GroundingService) DetectAnchors(text string) (map[ReferenceType][]string, float64) {
	lower := strings.ToLower(text)
	detected := make(map[ReferenceType][]string)
	count := 0

	for _, a := range s.Anchors {
		if strings.Contains(lower, a.Pattern) {
			detected[a.Type] = append(detected[a.Type], a.Pattern)
			count++
		}
	}

	// Intensity calculation (Ported from Swift)
	words := strings.Fields(text)
	intensity := 0.0
	if len(words) > 0 {
		intensity = float64(count) / float64(len(words)) * 3.0
		if intensity > 1.0 {
			intensity = 1.0
		}
	}

	return detected, intensity
}

// GetGuidance returns instructions for the LLM to match the user's cultural intensity.
func (s *GroundingService) GetGuidance(intensity float64) string {
	if intensity > 0.7 {
		return "User is highly engaged with modern cultural references. Use natural, contemporary language, memes, and pop culture anchors where appropriate."
	} else if intensity > 0.3 {
		return "User uses moderate cultural references. You may use occasional contemporary analogies or pop culture anchors."
	}
	return "User uses minimal cultural references. Maintain a professional, grounded tone with few temporal anchors."
}
