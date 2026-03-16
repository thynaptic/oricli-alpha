package service

import (
	"strings"
)

// IntentCategory represents the classified category of a user intent
type IntentCategory string

const (
	Greeting               IntentCategory = "greeting"
	SharingNews            IntentCategory = "sharingNews"
	AskingForHelp          IntentCategory = "askingForHelp"
	ExpressingEmotion      IntentCategory = "expressingEmotion"
	EmotionalDistress      IntentCategory = "emotionalDistress"
	MentalHealthSupport    IntentCategory = "mentalHealthSupport"
	RequestingInformation  IntentCategory = "requestingInformation"
	CasualConversation     IntentCategory = "casualConversation"
	Other                  IntentCategory = "other"
)

// IntentClassification represents the result of an intent categorization
type IntentClassification struct {
	Category    IntentCategory `json:"category"`
	Subcategory string         `json:"subcategory"`
	Confidence  float64        `json:"confidence"`
}

// IntentService handles keyword-based intent detection and categorization
type IntentService struct{}

// NewIntentService creates a new intent service
func NewIntentService() *IntentService {
	return &IntentService{}
}

// CategorizeIntent classifies an intent string and user message
func (s *IntentService) CategorizeIntent(intent string, userMessage string) IntentClassification {
	normalized := strings.ToLower(intent)
	message := strings.ToLower(userMessage)

	// Check for greeting
	if strings.Contains(normalized, "greeting") || strings.Contains(normalized, "greet") ||
		normalized == "greet" || strings.Contains(normalized, "social") ||
		s.containsAny(message, []string{"hello", "hi", "hey"}) {
		return IntentClassification{Category: Greeting, Confidence: 0.9}
	}

	// Check for sharing news
	if s.containsAny(normalized, []string{"sharing", "surprising", "excitement", "unexpected", "news", "guess what", "happened"}) ||
		strings.Contains(message, "you'll never guess") {
		return IntentClassification{Category: SharingNews, Confidence: 0.9}
	}

	// Check for asking for help
	if s.containsAny(normalized, []string{"help", "assist", "support", "need help", "can you help"}) ||
		s.containsAny(message, []string{"help", "can you", "assist"}) {
		return IntentClassification{Category: AskingForHelp, Confidence: 0.85}
	}

	// Check for emotional distress (high severity)
	if s.containsAny(normalized, []string{"overwhelmed", "hopeless", "can't go on", "no point", "nothing matters", "give up"}) ||
		s.containsAny(message, []string{"overwhelmed", "hopeless", "can't go on", "no point"}) {
		return IntentClassification{Category: EmotionalDistress, Subcategory: "high", Confidence: 0.9}
	}

	// Check for expressing emotion
	if s.containsAny(normalized, []string{"happy", "excited", "great", "amazing", "wonderful", "positive"}) {
		return IntentClassification{Category: ExpressingEmotion, Subcategory: "positive", Confidence: 0.8}
	}

	if s.containsAny(normalized, []string{"sad", "frustrated", "angry", "upset", "disappointed", "negative"}) {
		return IntentClassification{Category: ExpressingEmotion, Subcategory: "negative", Confidence: 0.8}
	}

	// Default to casual conversation
	return IntentClassification{Category: CasualConversation, Confidence: 0.5}
}

func (s *IntentService) containsAny(text string, keywords []string) bool {
	for _, kw := range keywords {
		if strings.Contains(text, kw) {
			return true
		}
	}
	return false
}
