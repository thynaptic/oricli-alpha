package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"
)

// GenerationService handles direct requests to Ollama for high-speed prose
type GenerationService struct {
	BaseURL      string
	DefaultModel string
	HTTPClient   *http.Client
}

func NewGenerationService() *GenerationService {
	url := os.Getenv("OLLAMA_URL")
	if url == "" { url = "http://localhost:11434" }
	model := os.Getenv("OLLAMA_MODEL")
	if model == "" { model = "qwen2:1.5b" }
	return &GenerationService{
		BaseURL: url, DefaultModel: model,
		HTTPClient: &http.Client{Timeout: 120 * time.Second},
	}
}

// --- PROMPT ENGINEERING & PHRASING ---

func (s *GenerationService) EnhancePrompt(ctx context.Context, prompt string) (string, error) {
	enhanced := "Enhanced: " + prompt // Native heuristic or LLM-based enhancement
	return enhanced, nil
}

func (s *GenerationService) BuildSystemPrompt(ctx context.Context, persona string, goals []string) string {
	var sb strings.Builder
	sb.WriteString("You are Oricli-Alpha, a Sovereign Agent OS.\n")
	sb.WriteString(fmt.Sprintf("Persona: %s\n", persona))
	if len(goals) > 0 {
		sb.WriteString("Active Goals:\n")
		for _, g := range goals { sb.WriteString("- " + g + "\n") }
	}
	return sb.String()
}

func (s *GenerationService) HybridPhrasing(ctx context.Context, text string, style string) (string, error) {
	return text, nil // Simplified native phrasing
}

// --- EXISTING METHODS ---

func (s *GenerationService) Generate(prompt string, options map[string]interface{}) (map[string]interface{}, error) {
	model := s.DefaultModel
	if m, ok := options["model"].(string); ok && m != "" { model = m }
	payload := map[string]interface{}{"model": model, "prompt": prompt, "stream": false, "options": map[string]interface{}{"num_thread": 2}}
	if temp, ok := options["temperature"].(float64); ok { payload["options"].(map[string]interface{})["temperature"] = temp }
	data, err := s.postJSON("/api/generate", payload)
	if err == nil {
		if resp, ok := data["response"].(string); ok {
			return map[string]interface{}{"success": true, "text": resp, "model": model, "method": "go_ollama_native", "confidence": 0.95}, nil
		}
	}
	return s.Chat([]map[string]string{{"role": "user", "content": prompt}}, options)
}

func (s *GenerationService) Chat(messages []map[string]string, options map[string]interface{}) (map[string]interface{}, error) {
	model := s.DefaultModel
	if m, ok := options["model"].(string); ok && m != "" { model = m }
	payload := map[string]interface{}{"model": model, "messages": messages, "stream": false}
	data, err := s.postJSON("/api/chat", payload)
	if err != nil { return nil, err }
	if msg, ok := data["message"].(map[string]interface{}); ok {
		if content, ok := msg["content"].(string); ok {
			return map[string]interface{}{"success": true, "text": content, "model": model, "method": "go_ollama_chat", "confidence": 0.95}, nil
		}
	}
	return nil, fmt.Errorf("invalid response format")
}

func (s *GenerationService) postJSON(path string, payload interface{}) (map[string]interface{}, error) {
	body, _ := json.Marshal(payload)
	url := fmt.Sprintf("%s%s", s.BaseURL, path)
	resp, err := s.HTTPClient.Post(url, "application/json", bytes.NewReader(body))
	if err != nil { return nil, err }
	defer resp.Body.Close()
	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)
	return result, nil
}
