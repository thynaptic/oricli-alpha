package cognition

import (
	"math"
	"strings"
	"sync"
)

// --- Pillar 32: Modern Slang & Rapport Engine ---
// Ported from Aurora's ModernSlangDetector.swift.
// Analyzes linguistic tics and generates rapport-building directives.

type SlangCategory string

const (
	SlangGenZ          SlangCategory = "genZ"
	SlangInternet      SlangCategory = "internet"
	SlangCasual        SlangCategory = "casual"
	SlangAbbreviations SlangCategory = "abbreviations"
	SlangExpressions   SlangCategory = "expressions"
)

type SlangResult struct {
	Intensity      float64
	Detected       []string
	Categories     []SlangCategory
	RecommendedLevel float64
}

type SlangEngine struct {
	Lexicon map[SlangCategory][]string
	History []float64
	mu      sync.RWMutex
}

func NewSlangEngine() *SlangEngine {
	e := &SlangEngine{
		Lexicon: make(map[SlangCategory][]string),
		History: make([]float64, 0),
	}
	e.loadLexicon()
	return e
}

func (e *SlangEngine) loadLexicon() {
	// Ported from Swift
	e.Lexicon[SlangGenZ] = []string{"no cap", "fr", "deadass", "bet", "lowkey", "highkey", "rizz", "gyatt", "skibidi", "sigma", "slay", "it's giving", "based", "cringe", "sus"}
	e.Lexicon[SlangInternet] = []string{"pog", "poggers", "monka", "omegalul", "copium", "hopium", "ratio", "skill issue", "git gud", "chronically online"}
	e.Lexicon[SlangCasual] = []string{"anyway", "literally", "actually", "honestly", "tbh", "ngl", "imo", "kinda", "sorta", "basically"}
	e.Lexicon[SlangAbbreviations] = []string{"rn", "asap", "tmr", "yday", "irl", "afk", "gg", "ttyl", "ty", "np"}
	e.Lexicon[SlangExpressions] = []string{"periodt", "go off", "valid", "wild", "crazy", "fire", "dope", "lit", "W", "L"}
}

// Analyze processes text and updates the user's slang momentum.
func (e *SlangEngine) Analyze(text string) SlangResult {
	e.mu.Lock()
	defer e.mu.Unlock()

	lower := strings.ToLower(text)
	var detected []string
	categories := make(map[SlangCategory]bool)

	for cat, patterns := range e.Lexicon {
		for _, p := range patterns {
			if strings.Contains(lower, p) {
				detected = append(detected, p)
				categories[cat] = true
			}
		}
	}

	// Intensity (Ported heuristic)
	words := strings.Fields(text)
	intensity := 0.0
	if len(words) > 0 {
		intensity = math.Min(1.0, (float64(len(detected))/float64(len(words)))*5.0)
	}

	// Update History (Rolling 10)
	e.History = append(e.History, intensity)
	if len(e.History) > 10 {
		e.History = e.History[1:]
	}

	// Recommended Level (Weighted blend of current and historical)
	avg := 0.0
	for _, h := range e.History { avg += h }
	if len(e.History) > 0 { avg /= float64(len(e.History)) }
	
	recommended := (intensity * 0.6) + (avg * 0.4)

	var cats []SlangCategory
	for c := range categories { cats = append(cats, c) }

	return SlangResult{
		Intensity:      intensity,
		Detected:       detected,
		Categories:     cats,
		RecommendedLevel: recommended,
	}
}

// GetDirectives returns rapport-building instructions based on slang analysis.
func (e *SlangEngine) GetDirectives(res SlangResult) string {
	directives := "### LINGUISTIC RAPPORT:\n"
	
	if res.RecommendedLevel > 0.7 {
		directives += "- User uses heavy slang. Match their energy naturally. Use contemporary terms like 'fr', 'no cap', 'slay'.\n"
	} else if res.RecommendedLevel > 0.3 {
		directives += "- User uses moderate casual language. Use 'tbh', 'ngl', 'imo' where it feels natural.\n"
	} else {
		directives += "- User uses minimal slang. Keep language formal, polished, and precise.\n"
	}

	for _, cat := range res.Categories {
		switch cat {
		case SlangGenZ: directives += "- Incorporate subtle Gen Z expressions to build rapport.\n"
		case SlangInternet: directives += "- User is familiar with internet culture. Use modern analogies.\n"
		case SlangCasual: directives += "- Use casual connectors ('anyway', 'plus') to keep the flow conversational.\n"
		}
	}

	return directives
}
