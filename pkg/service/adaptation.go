package service

import (
	"math"
	"regexp"
	"strings"
)

type AdaptationFactors struct {
	FormalityLevel           float64 `json:"formality_level"`
	SlangUsage               float64 `json:"slang_usage"`
	CulturalReferenceComfort float64 `json:"cultural_reference_comfort"`
	AverageEnergy            float64 `json:"average_energy"`
	PreferredEmotionalTone   string  `json:"preferred_emotional_tone"`
	ResponseLengthPreference float64 `json:"response_length_preference"`
}

type AdaptationService struct {
	FormalWords   map[string]bool
	CasualWords   map[string]bool
	SlangWords    map[string]bool
	ToneKeywords  map[string][]string
	CulturalRe    *regexp.Regexp
}

func NewAdaptationService() *AdaptationService {
	s := &AdaptationService{
		FormalWords: map[string]bool{
			"please": true, "thank": true, "appreciate": true, "would": true,
			"could": true, "should": true, "respectfully": true, "sincerely": true,
		},
		CasualWords: map[string]bool{
			"yeah": true, "yep": true, "nah": true, "dude": true, "bro": true,
			"sup": true, "yo": true, "hey": true, "cool": true, "awesome": true,
		},
		SlangWords: map[string]bool{
			"yeet": true, "fr": true, "no cap": true, "cap": true, "bet": true,
			"lowkey": true, "highkey": true, "deadass": true, "tea": true, "sis": true,
		},
		ToneKeywords: map[string][]string{
			"playful":   {"lol", "haha", "funny", "joke", "lmao", "lmfao"},
			"warm":      {"love", "care", "warm", "comfort", "support"},
			"assertive": {"need", "must", "should", "definitely", "absolutely"},
		},
		CulturalRe: regexp.MustCompile(`(?i)(meme|viral|trend|tiktok|instagram|twitter|youtube)`),
	}
	return s
}

func (s *AdaptationService) Analyze(history []string) AdaptationFactors {
	if len(history) == 0 {
		return AdaptationFactors{FormalityLevel: 0.5, AverageEnergy: 0.5, ResponseLengthPreference: 20.0}
	}

	var totalFormality, totalSlang, totalEnergy, totalLength float64
	toneCounts := make(map[string]int)
	culturalCount := 0

	for _, msg := range history {
		words := strings.Fields(strings.ToLower(msg))
		if len(words) == 0 { continue }

		// 1. Formality
		formal, casual := 0, 0
		for _, w := range words {
			if s.FormalWords[w] { formal++ }
			if s.CasualWords[w] { casual++ }
		}
		if formal+casual > 0 {
			totalFormality += float64(formal) / float64(formal+casual)
		} else {
			totalFormality += 0.5
		}

		// 2. Slang
		slang := 0
		for _, w := range words {
			if s.SlangWords[w] { slang++ }
		}
		totalSlang += math.Min(1.0, float64(slang)/math.Max(1.0, float64(len(words))*0.3))

		// 3. Energy
		excl := float64(strings.Count(msg, "!"))
		ques := float64(strings.Count(msg, "?"))
		caps := 0.0
		for _, c := range msg {
			if c >= 'A' && c <= 'Z' { caps++ }
		}
		totalEnergy += math.Min(1.0, (excl*0.3 + ques*0.2 + caps*0.1 + float64(len(words))*0.01))

		// 4. Tone & Cultural
		lowerMsg := strings.ToLower(msg)
		for tone, keywords := range s.ToneKeywords {
			for _, kw := range keywords {
				if strings.Contains(lowerMsg, kw) {
					toneCounts[tone]++
				}
			}
		}
		if s.CulturalRe.MatchString(msg) {
			culturalCount++
		}
		totalLength += float64(len(words))
	}

	count := float64(len(history))
	bestTone := ""
	maxTone := 0
	for t, c := range toneCounts {
		if c > maxTone {
			maxTone = c
			bestTone = t
		}
	}

	return AdaptationFactors{
		FormalityLevel:           totalFormality / count,
		SlangUsage:               totalSlang / count,
		CulturalReferenceComfort: math.Min(1.0, float64(culturalCount)/math.Max(1.0, count*0.3)),
		AverageEnergy:            totalEnergy / count,
		PreferredEmotionalTone:   bestTone,
		ResponseLengthPreference: totalLength / count,
	}
}
