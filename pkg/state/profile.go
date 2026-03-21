package state

import (
	"math"
	"time"
)

// --- Pillar 34: User Communication Profile ---
// Ported from Aurora's UserCommunicationProfile.swift.
// Maintains long-term social learning and style adaptation.

type AdaptationSnapshot struct {
	Timestamp       time.Time `json:"timestamp"`
	Formality       float64   `json:"formality"`
	SlangUsage      float64   `json:"slang_usage"`
	CulturalComfort float64   `json:"cultural_comfort"`
	AverageEnergy   float64   `json:"average_energy"`
	Punctuation     float64   `json:"punctuation"`
	SentenceLength  float64   `json:"sentence_length"`
	EmojiFrequency  float64   `json:"emoji_frequency"`
	TurnCount       int       `json:"turn_count"`
}

type UserProfile struct {
	UserID           string               `json:"user_id"`
	Formality        float64              `json:"formality"` // EMA 0.0-1.0
	SlangUsage       float64              `json:"slang_usage"`
	CulturalComfort  float64              `json:"cultural_comfort"`
	AverageEnergy    float64              `json:"average_energy"`
	Punctuation      float64              `json:"punctuation"`
	SentenceLength   float64              `json:"sentence_length"`
	EmojiFrequency   float64              `json:"emoji_frequency"`
	Capitalization   string               `json:"capitalization"` // proper, lowercase, mixed
	History          []AdaptationSnapshot `json:"history"`
	LastUpdated      time.Time            `json:"last_updated"`
	ConversationCount int                 `json:"conversation_count"`
	UpdateCount      int                  `json:"update_count"`
	
	// Alpha (smoothing factor for EMA)
	Alpha float64 `json:"alpha"`
}

func NewUserProfile(userID string) *UserProfile {
	return &UserProfile{
		UserID:          userID,
		Formality:       0.5,
		SlangUsage:      0.2,
		CulturalComfort: 0.3,
		AverageEnergy:   0.5,
		Punctuation:     0.5,
		SentenceLength:  12.0,
		Capitalization:  "proper",
		Alpha:           0.2,
		LastUpdated:     time.Now(),
		History:         make([]AdaptationSnapshot, 0),
	}
}

// UpdateStyle applies a new observation to the long-term averages using EMA.
func (p *UserProfile) UpdateStyle(formality, slang, cultural, energy, punct, length, emoji float64, cap string) {
	p.Formality = (p.Alpha * formality) + ((1.0 - p.Alpha) * p.Formality)
	p.SlangUsage = (p.Alpha * slang) + ((1.0 - p.Alpha) * p.SlangUsage)
	p.CulturalComfort = (p.Alpha * cultural) + ((1.0 - p.Alpha) * p.CulturalComfort)
	p.AverageEnergy = (p.Alpha * energy) + ((1.0 - p.Alpha) * p.AverageEnergy)
	p.Punctuation = (p.Alpha * punct) + ((1.0 - p.Alpha) * p.Punctuation)
	p.SentenceLength = (p.Alpha * length) + ((1.0 - p.Alpha) * p.SentenceLength)
	p.EmojiFrequency = (p.Alpha * emoji) + ((1.0 - p.Alpha) * p.EmojiFrequency)
	p.Capitalization = cap
	
	p.UpdateCount++
	p.LastUpdated = time.Now()
}

// CreateSnapshot captures the current learned state.
func (p *UserProfile) CreateSnapshot() {
	snap := AdaptationSnapshot{
		Timestamp:       time.Now(),
		Formality:       p.Formality,
		SlangUsage:      p.SlangUsage,
		CulturalComfort: p.CulturalComfort,
		AverageEnergy:   p.AverageEnergy,
		TurnCount:       p.ConversationCount,
	}
	p.History = append(p.History, snap)
	
	// Keep last 50 snapshots
	if len(p.History) > 50 {
		p.History = p.History[1:]
	}
}

// BlendParameters calculates adapted personality weights (Ported from Swift getAdaptedParameters).
func (p *UserProfile) BlendParameters(baseFormality, baseSlang, baseCultural float64, strength float64) (float64, float64, float64) {
	f := (baseFormality * (1.0 - strength)) + (p.Formality * strength)
	s := (baseSlang * (1.0 - strength)) + (p.SlangUsage * strength)
	c := (baseCultural * (1.0 - strength)) + (p.CulturalComfort * strength)
	
	return clamp(f), clamp(s), clamp(c)
}

func clamp(v float64) float64 {
	return math.Max(0.0, math.Min(1.0, v))
}
