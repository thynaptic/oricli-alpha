package service

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
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
	if url == "" {
		url = "http://localhost:11434"
	}
	model := os.Getenv("OLLAMA_MODEL")
	if model == "" {
		model = "qwen2:1.5b"
	}

	return &GenerationService{
		BaseURL:      url,
		DefaultModel: model,
		HTTPClient: &http.Client{
			Timeout: 120 * time.Second,
		},
	}
}

func (s *GenerationService) Generate(prompt string, options map[string]interface{}) (map[string]interface{}, error) {
	model := s.DefaultModel
	if m, ok := options["model"].(string); ok && m != "" {
		model = m
	}

	fmt.Printf("[GenService] Prompt: %s (Model: %s)\n", prompt, model)

	// Try /api/generate first (Ollama Native)
	payload := map[string]interface{}{
		"model":  model,
		"prompt": prompt,
		"stream": false,
		"options": map[string]interface{}{
			"num_thread": 2, // Keep CPU usage sane
		},
	}

	if temp, ok := options["temperature"].(float64); ok {
		payload["options"].(map[string]interface{})["temperature"] = temp
	}

	data, err := s.postJSON("/api/generate", payload)
	
	// Check for model not found and fallback
	if err != nil && (contains(err.Error(), "404") || contains(err.Error(), "not found")) && model != s.DefaultModel {
		fmt.Printf("[GenService] Model %s not found, falling back to %s\n", model, s.DefaultModel)
		options["model"] = s.DefaultModel
		return s.Generate(prompt, options)
	}

	if err == nil {
		if resp, ok := data["response"].(string); ok {
			fmt.Printf("[GenService] Ollama success: %d chars\n", len(resp))
			return map[string]interface{}{
				"success":    true,
				"text":       resp,
				"model":      model,
				"method":     "go_ollama_native",
				"confidence": 0.95,
			}, nil
		}
	} else {
		fmt.Printf("[GenService] Ollama native error: %v\n", err)
	}

	// Fallback to OpenAI-compatible endpoint if native fails
	return s.Chat( []map[string]string{
		{"role": "user", "content": prompt},
	}, options)
}

func (s *GenerationService) Chat(messages []map[string]string, options map[string]interface{}) (map[string]interface{}, error) {
	model := s.DefaultModel
	if m, ok := options["model"].(string); ok && m != "" {
		model = m
	}

	fmt.Printf("[GenService] Chatting with %d messages (Model: %s)\n", len(messages), model)

	payload := map[string]interface{}{
		"model":    model,
		"messages": messages,
		"stream":   false,
	}

	data, err := s.postJSON("/api/chat", payload)

	// Check for model not found and fallback
	if err != nil && (contains(err.Error(), "404") || contains(err.Error(), "not found")) && model != s.DefaultModel {
		fmt.Printf("[GenService] Model %s not found in chat, falling back to %s\n", model, s.DefaultModel)
		options["model"] = s.DefaultModel
		return s.Chat(messages, options)
	}

	if err != nil {
		fmt.Printf("[GenService] Ollama chat error: %v\n", err)
		return nil, err
	}

	if msg, ok := data["message"].(map[string]interface{}); ok {
		if content, ok := msg["content"].(string); ok {
			fmt.Printf("[GenService] Ollama chat success: %d chars\n", len(content))
			return map[string]interface{}{
				"success":    true,
				"text":       content,
				"model":      model,
				"method":     "go_ollama_chat",
				"confidence": 0.95,
			}, nil
		}
	}

	return nil, fmt.Errorf("invalid response format from Ollama")
}

func contains(s, substr string) bool {
	return bytes.Contains([]byte(s), []byte(substr))
}

func (s *GenerationService) postJSON(path string, payload interface{}) (map[string]interface{}, error) {
	body, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

	url := fmt.Sprintf("%s%s", s.BaseURL, path)
	
	maxRetries := 3
	var lastErr error

	for i := 0; i < maxRetries; i++ {
		if i > 0 {
			fmt.Printf("[GenService] Retrying Ollama (%d/%d) after error: %v\n", i, maxRetries, lastErr)
			time.Sleep(2 * time.Second)
		}

		resp, err := s.HTTPClient.Post(url, "application/json", bytes.NewReader(body))
		if err != nil {
			lastErr = err
			continue
		}
		
		if resp.StatusCode != http.StatusOK {
			respBody, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			lastErr = fmt.Errorf("Ollama returned status %d: %s", resp.StatusCode, string(respBody))
			
			// Only retry on "busy" or "503"
			if resp.StatusCode == http.StatusServiceUnavailable || contains(string(respBody), "busy") {
				continue
			}
			return nil, lastErr
		}

		var result map[string]interface{}
		err = json.NewDecoder(resp.Body).Decode(&result)
		resp.Body.Close()
		if err != nil {
			return nil, err
		}

		return result, nil
	}

	return nil, fmt.Errorf("all retries failed: %w", lastErr)
}
