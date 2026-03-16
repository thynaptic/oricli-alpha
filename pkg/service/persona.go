package service

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
)

type PersonalityConfig struct {
	Description             string              `json:"description"`
	KeyPhrases              []string            `json:"key_phrases"`
	Temperature             float64             `json:"temperature"`
	DefaultSassFactor       float64             `json:"default_sass_factor"`
	EmotionalResponseStyle  string              `json:"emotional_response_style"`
	ExampleResponses        map[string][]string `json:"example_responses"`
}

type PersonaData struct {
	Personalities map[string]PersonalityConfig `json:"personalities"`
}

type PersonaService struct {
	Data PersonaData
}

func NewPersonaService(configPath string) (*PersonaService, error) {
	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, err
	}

	var pd PersonaData
	if err := json.Unmarshal(data, &pd); err != nil {
		return nil, err
	}

	return &PersonaService{Data: pd}, nil
}

func (s *PersonaService) BuildSystemInstructions(personalityID string) (string, float64) {
	p, ok := s.Data.Personalities[personalityID]
	if !ok {
		// Default to a generic helpful personality if not found
		return "You are Oricli-Alpha, a high-signal, helpful AI assistant.", 0.7
	}

	instructions := fmt.Sprintf(`You are Oricli-Alpha adopting the %s persona.
Core Description: %s
Tone Style: %s
Sass Factor: %.2f

Signature Phrases to use occasionally: %v

Maintain this voice consistently. Be authentic and relatable.`, 
		personalityID, p.Description, p.EmotionalResponseStyle, p.DefaultSassFactor, p.KeyPhrases)

	return instructions, p.Temperature
}

func (s *PersonaService) GetRandomExample(personalityID, intent string) string {
	p, ok := s.Data.Personalities[personalityID]
	if !ok {
		return ""
	}

	examples, ok := p.ExampleResponses[intent]
	if !ok || len(examples) == 0 {
		return ""
	}

	return examples[rand.Intn(len(examples))]
}
