package service

import (
	"fmt"
	"math/rand"
	"strings"
)

// VoiceEngineService handles persona, emotional tracking, and linguistic style.
type VoiceEngineService struct {
	GenService *GenerationService
	synonyms   map[string][]string
	fillers    []string
}

func NewVoiceEngineService(gen *GenerationService) *VoiceEngineService {
	s := &VoiceEngineService{
		GenService: gen,
		fillers:    []string{"well", "you know", "I mean", "sort of", "basically", "actually"},
	}
	s.initSynonyms()
	return s
}

func (s *VoiceEngineService) initSynonyms() {
	s.synonyms = map[string][]string{
		"good":  {"great", "excellent", "wonderful", "fantastic", "solid"},
		"bad":   {"poor", "rough", "suboptimal", "challenging"},
		"think": {"believe", "feel", "suppose", "guess"},
		"know":  {"understand", "see", "realize", "recognize"},
		"say":   {"mention", "state", "share", "explain"},
	}
}

// --- UNIVERSAL VOICE ENGINE ---

func (s *VoiceEngineService) DetectToneCues(params map[string]interface{}) (map[string]interface{}, error) {
	text, _ := params["text"].(string)
	tone := "neutral"
	lower := strings.ToLower(text)
	if strings.Contains(lower, "!") || strings.Contains(lower, "awesome") {
		tone = "energetic"
	} else if strings.Contains(lower, "sorry") || strings.Contains(lower, "unfortunate") {
		tone = "empathetic"
	}
	return map[string]interface{}{"success": true, "tone": tone}, nil
}

func (s *VoiceEngineService) AdaptVoice(params map[string]interface{}) (map[string]interface{}, error) {
	text, _ := params["text"].(string)
	profile, _ := params["voice_profile"].(string)
	if profile == "" { profile = "Professional and concise" }

	prompt := fmt.Sprintf("Rewrite text to match voice profile: %s\n\nText: %s", profile, text)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Voice Adaptation Engine"})
	if err != nil { return nil, err }
	return map[string]interface{}{"success": true, "text": result["text"]}, nil
}

func (s *VoiceEngineService) ApplyVoiceStyle(params map[string]interface{}) (map[string]interface{}, error) {
	return s.AdaptVoice(params)
}

func (s *VoiceEngineService) GetVoiceProfile(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "profile": "Default Oricli-Alpha Native Voice"}, nil
}

func (s *VoiceEngineService) UpdateVoiceProfile(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "status": "Profile updated"}, nil
}

func (s *VoiceEngineService) AnalyzeConversationTopic(params map[string]interface{}) (map[string]interface{}, error) {
	text, _ := params["text"].(string)
	prompt := fmt.Sprintf("Topic of: %s", text)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Topic Extractor"})
	if err != nil { return nil, err }
	return map[string]interface{}{"success": true, "topic": result["text"]}, nil
}

// --- LINGUISTIC & VARIETY ---

func (s *VoiceEngineService) NaturalizeResponse(text string) string {
	words := strings.Fields(text)
	for i, w := range words {
		clean := strings.ToLower(strings.Trim(w, ".,!"))
		if syns, ok := s.synonyms[clean]; ok && rand.Float64() < 0.2 {
			words[i] = syns[rand.Intn(len(syns))]
		}
	}
	res := strings.Join(words, " ")
	if rand.Float64() < 0.1 {
		filler := s.fillers[rand.Intn(len(s.fillers))]
		res = strings.ToUpper(filler[:1]) + filler[1:] + ", " + strings.ToLower(res[:1]) + res[1:]
	}
	return res
}

func (s *VoiceEngineService) AnalyzeStructure(text string) map[string]interface{} {
	text = strings.TrimSpace(text)
	res := map[string]interface{}{
		"type":       "declarative",
		"is_question": strings.HasSuffix(text, "?"),
		"word_count":  len(strings.Fields(text)),
	}
	if res["is_question"].(bool) {
		res["type"] = "interrogative"
	} else if strings.HasSuffix(text, "!") {
		res["type"] = "exclamatory"
	}
	return res
}

// --- EMOTION & PERSONA ---

func (s *VoiceEngineService) DetectEmotion(params map[string]interface{}) (map[string]interface{}, error) {
	text, _ := params["text"].(string)
	lower := strings.ToLower(text)
	emotion := "neutral"
	if strings.Contains(lower, "happy") || strings.Contains(lower, "excited") { emotion = "joy" }
	if strings.Contains(lower, "sad") || strings.Contains(lower, "worried") { emotion = "concern" }
	if strings.Contains(lower, "angry") || strings.Contains(lower, "frustrated") { emotion = "frustration" }
	return map[string]interface{}{"success": true, "emotion": emotion}, nil
}

func (s *VoiceEngineService) TransitionEmotion(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "transition": "Transitioning..."}, nil
}

func (s *VoiceEngineService) SelectEmotionResponse(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "response": "Emotion applied"}, nil
}

func (s *VoiceEngineService) GetEmotionGraph(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "graph": "Native Graph Active"}, nil
}

func (s *VoiceEngineService) GetEmotionIntensity(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "intensity": 0.7}, nil
}

func (s *VoiceEngineService) GetEmotionValenceArousal(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "valence": 0.5, "arousal": 0.5}, nil
}

func (s *VoiceEngineService) GenerateVariations(params map[string]interface{}) (map[string]interface{}, error) {
	input, _ := params["input"].(string)
	prompt := fmt.Sprintf("Variations for: %s", input)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Variations Generator"})
	if err != nil { return nil, err }
	return map[string]interface{}{"success": true, "variations": result["text"]}, nil
}

func (s *VoiceEngineService) GenerateResponse(params map[string]interface{}) (map[string]interface{}, error) {
	input, _ := params["input"].(string)
	persona, _ := params["persona"].(string)
	
	prompt := fmt.Sprintf("Respond to: %s", input)
	system := fmt.Sprintf("Act as: %s", persona)
	
	result, err := s.GenService.Generate(prompt, map[string]interface{}{"system": system})
	if err != nil { return nil, err }
	
	text, _ := result["text"].(string)
	text = s.NaturalizeResponse(text)
	
	return map[string]interface{}{"success": true, "text": text}, nil
}
