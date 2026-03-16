package service

import (
	"math/rand"
	"strings"
)

// ConversationalService handles simple greetings and proactive engagement
type ConversationalService struct {
	greetings        []string
	triggerKeywords []string
	followUpPatterns map[string][]string
	curiosityExprs   map[string][]string
	backChanneling   map[string][]string
}

// NewConversationalService creates a new conversational service
func NewConversationalService() *ConversationalService {
	s := &ConversationalService{
		greetings: []string{
			"Hello! How can the Hive assist you today?",
			"Greetings. I am Oricli-Alpha. What's on your mind?",
			"Hi there! Ready for some sovereign orchestration?",
			"Hello! The micro-agents are standing by. How can I help?",
			"Greetings, boss. What are we building today?",
		},
		triggerKeywords: []string{"hi", "hello", "hey", "greetings", "yo", "morning", "afternoon", "evening"},
	}
	s.initPatterns()
	return s
}

func (s *ConversationalService) initPatterns() {
	s.followUpPatterns = map[string][]string{
		"clarification": {
			"What do you mean by that?",
			"Could you elaborate?",
			"Can you tell me more?",
		},
		"deeper": {
			"What made you think of that?",
			"How did that come about?",
			"What's the story behind that?",
		},
	}
	s.curiosityExprs = map[string][]string{
		"mild":     {"That's interesting.", "I see.", "Hmm."},
		"moderate": {"That's really interesting!", "I'd love to hear more.", "Tell me more about that."},
		"high":     {"Wow, that's fascinating!", "I'm really curious about that.", "That sounds intriguing!"},
	}
	s.backChanneling = map[string][]string{
		"acknowledgment": {"I see", "Right", "Okay", "Got it", "Makes sense"},
		"encouragement":  {"That's interesting", "I hear you", "Go on", "Tell me more"},
		"validation":     {"That makes sense", "I understand", "That's reasonable", "I can see that"},
	}
}

// GenerateDefaultResponse returns a greeting if the input matches trigger keywords
func (s *ConversationalService) GenerateDefaultResponse(lastMessage string) (string, float64) {
	msg := strings.ToLower(strings.TrimSpace(lastMessage))
	msg = strings.Trim(msg, "?!.")

	for _, kw := range s.triggerKeywords {
		if msg == kw {
			return s.getRandom(s.greetings), 1.0
		}
	}

	if len(msg) < 3 {
		return s.getRandom(s.greetings), 0.9
	}

	return "I hear you, but I might need a bit more detail to dispatch the right micro-agents. What's the goal?", 0.1
}

// AddBackChanneling adds a small prefix to a response based on user input
func (s *ConversationalService) AddBackChanneling(response string, userInput string) (string, bool) {
	if response == "" {
		return response, false
	}

	userLower := strings.ToLower(userInput)
	
	// Emotional check
	emotions := []string{"sad", "happy", "excited", "worried", "frustrated", "angry"}
	hasEmotion := false
	for _, e := range emotions {
		if strings.Contains(userLower, e) {
			hasEmotion = true
			break
		}
	}

	prefix := ""
	if hasEmotion {
		prefix = s.getRandom(s.backChanneling["validation"])
	} else if len(strings.Fields(userInput)) > 15 {
		prefix = s.getRandom(s.backChanneling["acknowledgment"])
	}

	if prefix != "" && rand.Float64() < 0.6 {
		if !strings.HasPrefix(strings.ToLower(response), strings.ToLower(prefix)) {
			return prefix + ", " + strings.ToLower(response[:1]) + response[1:], true
		}
	}

	return response, false
}

func (s *ConversationalService) getRandom(list []string) string {
	if len(list) == 0 {
		return ""
	}
	return list[rand.Intn(len(list))]
}
