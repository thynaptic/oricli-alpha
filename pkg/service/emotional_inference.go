package service

import (
	"log"
	"math/rand"
	"regexp"
	"strings"
	"sync"
	"time"
)

type EmotionalScore struct {
	PrimaryEmotion string  `json:"primary_emotion"`
	Score          float64 `json:"score"`
	Valence        float64 `json:"valence"`
	Arousal        float64 `json:"arousal"`
	Urgency        float64 `json:"urgency"`
}

type WarmthLevel struct {
	Level      string   `json:"level"`
	Modulators []string `json:"modulators"`
}

type EmpathyTuning struct {
	Level   string   `json:"level"`
	Phrases []string `json:"phrases"`
}

type EmotionalInferenceService struct {
	mu               sync.RWMutex
	emotionPatterns  map[string]*regexp.Regexp
	warmthModulators map[string][]string
	empathyTuners    map[string][]string
	affectiveStates  map[string]map[string]interface{}
}

func NewEmotionalInferenceService() *EmotionalInferenceService {
	s := &EmotionalInferenceService{
		affectiveStates: make(map[string]map[string]interface{}),
	}
	s.loadConfig()
	return s
}

func (s *EmotionalInferenceService) loadConfig() {
	// Hardcoded defaults to replace JSON for speed
	s.emotionPatterns = map[string]*regexp.Regexp{
		"positive":     regexp.MustCompile(`(?i)\b(happy|excited|great|awesome|wonderful|amazing|love|enjoy)\b`),
		"negative":     regexp.MustCompile(`(?i)\b(sad|angry|frustrated|worried|stressed|tired|upset|disappointed)\b`),
		"neutral":      regexp.MustCompile(`(?i)\b(okay|fine|alright|normal|regular)\b`),
		"seeking_help": regexp.MustCompile(`(?i)\b(help|need|problem|issue|stuck|confused|don't understand)\b`),
	}

	s.warmthModulators = map[string][]string{
		"high_warmth":   {"I'm here for you", "I understand", "That sounds", "I hear you"},
		"medium_warmth": {"I see", "Got it", "That makes sense", "I get that"},
		"low_warmth":    {"Understood", "Noted", "Acknowledged"},
	}

	s.empathyTuners = map[string][]string{
		"high_empathy":   {"That must be", "I can imagine", "That sounds really", "I'm sorry you're"},
		"medium_empathy": {"That's", "I understand", "That can be"},
		"low_empathy":    {"I see", "Okay", "Right"},
	}
}

func (s *EmotionalInferenceService) ScoreEmotionalIntent(text string, context string) *EmotionalScore {
	s.mu.RLock()
	defer s.mu.RUnlock()

	log.Printf("[EmotionalInference] Scoring intent for text length: %d", len(text))

	scores := make(map[string]int)
	totalMatches := 0

	for emotion, re := range s.emotionPatterns {
		matches := len(re.FindAllStringIndex(text, -1))
		scores[emotion] = matches
		totalMatches += matches
	}

	primaryEmotion := "neutral"
	maxScore := 0
	for e, c := range scores {
		if c > maxScore {
			maxScore = c
			primaryEmotion = e
		}
	}

	valence := 0.5
	if primaryEmotion == "positive" {
		valence = 0.8
	} else if primaryEmotion == "negative" || primaryEmotion == "seeking_help" {
		valence = 0.2
	}

	arousal := 0.5
	if strings.Contains(text, "!") || strings.ToUpper(text) == text && len(text) > 5 {
		arousal = 0.8
	}

	urgency := 0.2
	if primaryEmotion == "seeking_help" || strings.Contains(strings.ToLower(text), "asap") || strings.Contains(strings.ToLower(text), "urgent") {
		urgency = 0.9
	}

	confidence := 0.5
	if totalMatches > 0 {
		confidence = float64(maxScore) / float64(totalMatches)
	}

	return &EmotionalScore{
		PrimaryEmotion: primaryEmotion,
		Score:          confidence,
		Valence:        valence,
		Arousal:        arousal,
		Urgency:        urgency,
	}
}

func (s *EmotionalInferenceService) CalculateWarmthLevel(score *EmotionalScore) *WarmthLevel {
	s.mu.RLock()
	defer s.mu.RUnlock()

	level := "medium_warmth"
	if score.Valence < 0.4 || score.Urgency > 0.7 {
		level = "high_warmth"
	} else if score.Valence > 0.7 {
		level = "medium_warmth"
	} else if score.Arousal < 0.3 {
		level = "low_warmth"
	}

	return &WarmthLevel{
		Level:      level,
		Modulators: s.warmthModulators[level],
	}
}

func (s *EmotionalInferenceService) TuneEmpathy(text string, score *EmotionalScore) *EmpathyTuning {
	s.mu.RLock()
	defer s.mu.RUnlock()

	level := "medium_empathy"
	if score.PrimaryEmotion == "negative" || score.PrimaryEmotion == "seeking_help" {
		level = "high_empathy"
	} else if score.PrimaryEmotion == "neutral" {
		level = "low_empathy"
	}

	return &EmpathyTuning{
		Level:   level,
		Phrases: s.empathyTuners[level],
	}
}

func (s *EmotionalInferenceService) ModulateResponseWarmth(response string, score *EmotionalScore) string {
	warmth := s.CalculateWarmthLevel(score)
	empathy := s.TuneEmpathy(response, score)

	if len(warmth.Modulators) == 0 && len(empathy.Phrases) == 0 {
		return response
	}

	rand.Seed(time.Now().UnixNano())
	prefix := ""

	if score.Valence < 0.4 && len(empathy.Phrases) > 0 {
		prefix = empathy.Phrases[rand.Intn(len(empathy.Phrases))] + "... "
	} else if len(warmth.Modulators) > 0 {
		prefix = warmth.Modulators[rand.Intn(len(warmth.Modulators))] + ". "
	}

	return prefix + response
}
