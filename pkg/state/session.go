package state

import (
	"math"
	"math/rand"
	"sync"
	"time"
)

// --- Pillar 20: Stateful Session Management ---
// Ported from Aurora's ConversationalOrchestrator.swift.
// Tracks relationship evolution and social context across a session.

type RelationshipLevel string

const (
	RelFirstInteraction RelationshipLevel = "first_interaction"
	RelRapportBuilt      RelationshipLevel = "rapport_built"
	RelDeepConnection    RelationshipLevel = "deep_connection"
	RelConflict          RelationshipLevel = "conflict"
)

type SessionTurn struct {
	Input     string    `json:"input"`
	Output    string    `json:"output"`
	Timestamp time.Time `json:"timestamp"`
	Emotion   string    `json:"emotion"`
}

type ConversationalSession struct {
	ID                string            `json:"id"`
	Relationship      RelationshipLevel `json:"relationship"`
	Formality         float64           `json:"formality"`
	Turns             []SessionTurn     `json:"turns"`
	LastTopic         string            `json:"last_topic"`
	EngagementScore   float64           `json:"engagement_score"`
	mu                sync.RWMutex
}

func NewConversationalSession(id string) *ConversationalSession {
	return &ConversationalSession{
		ID:           id,
		Relationship: RelFirstInteraction,
		Formality:    0.5,
		Turns:        make([]SessionTurn, 0),
	}
}

// UpdateState processes a new turn and evolves the session's social context.
func (s *ConversationalSession) UpdateState(input, output, emotion string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	turn := SessionTurn{
		Input:     input,
		Output:    output,
		Timestamp: time.Now(),
		Emotion:   emotion,
	}
	s.Turns = append(s.Turns, turn)

	// Keep rolling window of 20 turns
	if len(s.Turns) > 20 {
		s.Turns = s.Turns[1:]
	}

	// 1. Relationship Evolution (Ported heuristic)
	if len(s.Turns) > 10 && s.Relationship == RelFirstInteraction {
		s.Relationship = RelRapportBuilt
	}
	if emotion == "conflict" {
		s.Relationship = RelConflict
	}

	// 2. Engagement Calculation
	// High engagement if turns are frequent and recent
	s.EngagementScore = math.Min(1.0, float64(len(s.Turns))/15.0)
}

// GetSocialDirectives returns instructions for the LLM based on relationship state.
func (s *ConversationalSession) GetSocialDirectives() string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	directives := "### SOCIAL CONTEXT & RELATIONSHIP:\n"
	
	switch s.Relationship {
	case RelFirstInteraction:
		directives += "- Relationship: Establishing rapport. Be helpful, clear, and welcoming.\n"
	case RelRapportBuilt:
		directives += "- Relationship: Established. You can be more informal and intuitive. Recall past turns.\n"
	case RelDeepConnection:
		directives += "- Relationship: Deep. High trust. Use personalized grounding and shared context.\n"
	case RelConflict:
		directives += "- Relationship: Dissonant. Prioritize de-escalation, empathy, and clarity.\n"
	}

	// Engagement Directive
	if s.EngagementScore > 0.8 {
		directives += "- User is highly engaged. You can use follow-up questions to deepen the exploration.\n"
	}

	return directives
}

// ShouldAskFollowUp implements the random engagement spark (Ported from Swift).
func (s *ConversationalSession) ShouldAskFollowUp() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()

	// 30% chance if engagement is moderate and history is long enough
	if len(s.Turns) >= 2 && s.EngagementScore > 0.4 {
		return rand.Float64() < 0.3
	}
	return false
}
