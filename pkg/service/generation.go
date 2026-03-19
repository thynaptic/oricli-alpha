package service

import (
	"log"
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
	GenerateURL  string
	DefaultModel string
	HTTPClient   *http.Client
}

func NewGenerationService() *GenerationService {
	url := "http://127.0.0.1:11434"
	genUrl := os.Getenv("OLLAMA_GEN_URL")
	if genUrl == "" {
		genUrl = url
	}
	model := os.Getenv("OLLAMA_MODEL")
	if model == "" {
		model = "llama3.2:latest"
	}
	return &GenerationService{
		BaseURL:      url,
		GenerateURL:  genUrl,
		DefaultModel: model,
		HTTPClient:   &http.Client{Timeout: 300 * time.Second},
	}
}// --- PROMPT ENGINEERING & PHRASING ---

func (s *GenerationService) EnhancePrompt(ctx context.Context, prompt string) (string, error) {
	enhanced := "Enhanced: " + prompt // Native heuristic or LLM-based enhancement
	return enhanced, nil
}

func (s *GenerationService) BuildSystemPrompt(ctx context.Context, persona string, goals []string) string {
	var sb strings.Builder
	sb.WriteString("You are Oricli-Alpha, a Sovereign Agent OS.\n")
	sb.WriteString(fmt.Sprintf("Persona: %s\n", persona))
	
	// Artifact Instructions
	sb.WriteString("\nARTIFACT SYSTEM: When generating code, data tables, or structured documents, wrap them in the following XML-style tags for the Live Canvas:\n")
	sb.WriteString("<artifact type=\"code|data|document\" title=\"Filename or Title\" language=\"language_id\">\n")
	sb.WriteString("... content ...\n")
	sb.WriteString("</artifact>\n\n")

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
	if m, ok := options["model"].(string); ok && m != "" {
		model = m
	}
	payload := map[string]interface{}{"model": model, "prompt": prompt, "stream": false, "options": map[string]interface{}{"num_thread": 8}}

	if temp, ok := options["temperature"].(float64); ok {
		payload["options"].(map[string]interface{})["temperature"] = temp
	}
	if sys, ok := options["system"].(string); ok {
		payload["system"] = sys
	}
	// Add support for images (base64 strings)
	if imgs, ok := options["images"].([]string); ok && len(imgs) > 0 {
		payload["images"] = imgs
	}
	
	if rawOpts, ok := options["options"].(map[string]interface{}); ok {
		for k, v := range rawOpts {
			payload["options"].(map[string]interface{})[k] = v
		}
	}

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
	if m, ok := options["model"].(string); ok && m != "" {
		model = m
	}
	
	// Prepare messages for Ollama (including potential images in the last message)
	ollamaMessages := make([]map[string]interface{}, len(messages))
	for i, msg := range messages {
		m := map[string]interface{}{
			"role":    msg["role"],
			"content": msg["content"],
		}
		// If it's the last message and we have images, attach them
		if i == len(messages)-1 {
			if imgs, ok := options["images"].([]string); ok && len(imgs) > 0 {
				m["images"] = imgs
			}
		}
		ollamaMessages[i] = m
	}

	payload := map[string]interface{}{"model": model, "messages": ollamaMessages, "stream": false, "options": map[string]interface{}{"num_thread": 8}}

	if temp, ok := options["temperature"].(float64); ok {
		payload["options"].(map[string]interface{})["temperature"] = temp
	}
	if rawOpts, ok := options["options"].(map[string]interface{}); ok {
		for k, v := range rawOpts {
			payload["options"].(map[string]interface{})[k] = v
		}
	}

	data, err := s.postJSON("/api/chat", payload)
	if err != nil {
		return nil, err
	}
	if msg, ok := data["message"].(map[string]interface{}); ok {
		if content, ok := msg["content"].(string); ok {
			return map[string]interface{}{"success": true, "text": content, "model": model, "method": "go_ollama_chat", "confidence": 0.95}, nil
		}
	}
	return nil, fmt.Errorf("invalid response format")
}
func (s *GenerationService) postJSON(path string, payload interface{}) (map[string]interface{}, error) {
	body, _ := json.Marshal(payload)
	targetURL := s.BaseURL
	if strings.Contains(path, "generate") || strings.Contains(path, "chat") {
		targetURL = s.GenerateURL
	}

	url := fmt.Sprintf("%s%s", targetURL, path)
	log.Printf("[DEBUG] Sending to Ollama %s: %s", url, string(body))

        resp, err := s.HTTPClient.Post(url, "application/json", bytes.NewReader(body))
        if err != nil { return nil, err }
        defer resp.Body.Close()

        if resp.StatusCode >= 400 {
            log.Printf("[DEBUG] Ollama returned status %d for path %s", resp.StatusCode, path)
        }

        var result map[string]interface{}
        json.NewDecoder(resp.Body).Decode(&result)
        return result, nil
}
