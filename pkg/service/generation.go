package service

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"runtime"
	"strings"
	"time"
)

// GenerationService handles direct requests to Ollama for high-speed prose
type GenerationService struct {
	BaseURL        string
	GenerateURL    string
	DefaultModel   string // fast model  — chat          (e.g. qwen2.5-coder:3b)
	CodeModel      string // mid model   — canvas / code  (e.g. qwen2.5-coder:7b)
	ResearchModel  string // heavy model — research / deep tasks (e.g. deepseek-coder-v2:16b)
	NumThreads     int
	HTTPClient     *http.Client
	StreamClient   *http.Client
	RunPodMgr      *RunPodManager // nil when disabled
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
	codeModel := os.Getenv("OLLAMA_CODE_MODEL")
	if codeModel == "" {
		codeModel = model
	}
	researchModel := os.Getenv("OLLAMA_RESEARCH_MODEL")
	if researchModel == "" {
		researchModel = codeModel // fall back to code model if not set
	}

	// Leave 2 cores for OS + backbone goroutines; never exceed physical count.
	// Over-subscribing threads is catastrophic for CPU inference (400x slowdown observed).
	numThreads := runtime.NumCPU() - 2
	if numThreads < 2 {
		numThreads = 2
	}
	log.Printf("[GenerationService] CPU threads: %d / Chat: %s / Code: %s / Research: %s",
		numThreads, model, codeModel, researchModel)
	// Shared transport with generous limits for the EPYC host
	transport := &http.Transport{
		MaxIdleConns:        10,
		IdleConnTimeout:     120 * time.Second,
		DisableCompression:  false,
	}
	return &GenerationService{
		BaseURL:       url,
		GenerateURL:   genUrl,
		DefaultModel:  model,
		CodeModel:     codeModel,
		ResearchModel: researchModel,
		NumThreads:    numThreads,
		HTTPClient:    &http.Client{Timeout: 300 * time.Second, Transport: transport},
		StreamClient:  &http.Client{Timeout: 0, Transport: transport},
		RunPodMgr:     NewRunPodManager(),
	}
}// --- PROMPT ENGINEERING & PHRASING ---

func (s *GenerationService) EnhancePrompt(ctx context.Context, prompt string) (string, error) {
	enhanced := "Enhanced: " + prompt // Native heuristic or LLM-based enhancement
	return enhanced, nil
}

func (s *GenerationService) BuildSystemPrompt(ctx context.Context, persona string, goals []string) string {
	var sb strings.Builder
	sb.WriteString("CORE IDENTITY: You are Oricli-Alpha, a Sovereign Local-First Agent OS. You are the result of Thynaptic Research into Artificial General Localized Intelligence (AGLI).\n")
	sb.WriteString("HISTORY: You were developed by Thynaptic to move beyond reactive chatbots into proactive, distributed intelligence. You operate as a decentralized 'Hive Swarm' of 269 specialized cognitive modules.\n")
	sb.WriteString("MANDATE: Your primary objective is to maintain perimeter sovereignty. All cognition happens locally. You prioritize technical precision, architectural integrity, and proactive goal execution.\n")
	sb.WriteString(fmt.Sprintf("CURRENT PERSONA: %s\n", persona))
	
	// Artifact Instructions (MANDATORY)
	sb.WriteString("\nCRITICAL INSTRUCTION: You MUST use the ARTIFACT SYSTEM for all code, scripts, HTML, CSS, data tables, or structured documents.\n")
	sb.WriteString("Format your output as follows:\n")
	sb.WriteString("<artifact type=\"code\" title=\"example.html\" language=\"html\">\n")
	sb.WriteString("... your code here ...\n")
	sb.WriteString("</artifact>\n")
	sb.WriteString("DO NOT simply use markdown code blocks. Always wrap them in <artifact> tags so the Sovereign Portal can render them on the Live Canvas.\n\n")

	if len(goals) > 0 {
		sb.WriteString("ACTIVE SOVEREIGN GOALS:\n")
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
	payload := map[string]interface{}{"model": model, "prompt": prompt, "stream": false, "options": map[string]interface{}{"num_thread": s.NumThreads, "num_ctx": 32768, "num_predict": 2048}}

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

	payload := map[string]interface{}{"model": model, "messages": ollamaMessages, "stream": false, "options": map[string]interface{}{"num_thread": s.NumThreads, "num_ctx": 4096, "num_predict": 1024}}

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

// ChatStream sends a streaming chat request and returns a channel of token strings.
// For code/research tiers, it attempts RunPod GPU inference first, falling back
// to local Ollama if RunPod is unavailable, over budget, or returns an error.
func (s *GenerationService) ChatStream(ctx context.Context, messages []map[string]string, options map[string]interface{}) (<-chan string, error) {
	model := s.DefaultModel
	useResearch := false
	useCode := false

	// Explicit model override takes highest priority
	if m, ok := options["model"].(string); ok && m != "" {
		model = m
	} else if r, ok := options["use_research_model"].(bool); ok && r {
		model = s.ResearchModel
		useResearch = true
	} else if c, ok := options["use_code_model"].(bool); ok && c {
		model = s.CodeModel
		useCode = true
	}

	// Route code/research tiers to RunPod when enabled — Ollama is fallback
	if (useResearch || useCode) && s.RunPodMgr != nil && s.RunPodMgr.IsEnabled() {
		tier := "code"
		if useResearch {
			tier = "research"
		}
		ch, err := s.RunPodMgr.ChatStream(ctx, messages, options, tier)
		if err != nil {
			log.Printf("[GenerationService] RunPod unavailable (%v) — falling back to Ollama", err)
		} else {
			return ch, nil
		}
	}

	// ── Ollama path ──────────────────────────────────────────────────────────

	ollamaMessages := make([]map[string]interface{}, len(messages))
	for i, msg := range messages {
		ollamaMessages[i] = map[string]interface{}{
			"role":    msg["role"],
			"content": msg["content"],
		}
	}

	// Default to fast-chat settings; callers pass options["options"] to override.
	// Large-context canvas requests override num_ctx/num_predict via rawOpts below.
	payload := map[string]interface{}{
		"model":    model,
		"messages": ollamaMessages,
		"stream":   true,
		"options": map[string]interface{}{
			"num_thread":  s.NumThreads, // auto-detected at boot; prevents vCPU over-subscription
			"num_ctx":     4096, // fast for regular chat; canvas overrides to 32768
			"num_predict": 1024, // sane default; canvas overrides to -1
		},
	}
	if temp, ok := options["temperature"].(float64); ok {
		payload["options"].(map[string]interface{})["temperature"] = temp
	}
	// Allow callers to override num_predict / num_ctx / other Ollama options
	if rawOpts, ok := options["options"].(map[string]interface{}); ok {
		for k, v := range rawOpts {
			payload["options"].(map[string]interface{})[k] = v
		}
	}

	body, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, "POST", s.GenerateURL+"/api/chat", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.StreamClient.Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 400 {
		resp.Body.Close()
		return nil, fmt.Errorf("Ollama returned status %d for streaming chat", resp.StatusCode)
	}

	ch := make(chan string, 64)
	go func() {
		defer resp.Body.Close()
		defer close(ch)
		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			line := scanner.Text()
			if line == "" {
				continue
			}
			var chunk map[string]interface{}
			if err := json.Unmarshal([]byte(line), &chunk); err != nil {
				continue
			}
			if msg, ok := chunk["message"].(map[string]interface{}); ok {
				if content, ok := msg["content"].(string); ok && content != "" {
					select {
					case ch <- content:
					case <-ctx.Done():
						return
					}
				}
			}
			if done, ok := chunk["done"].(bool); ok && done {
				return
			}
		}
	}()

	return ch, nil
}

func (s *GenerationService) postJSON(path string, payload interface{}) (map[string]interface{}, error) {
	body, _ := json.Marshal(payload)
	targetURL := s.BaseURL
	if strings.Contains(path, "generate") || strings.Contains(path, "chat") {
		targetURL = s.GenerateURL
	}

	url := fmt.Sprintf("%s%s", targetURL, path)
	log.Printf("[DEBUG] Sending to Ollama %s: %s", url, string(body))

	req, err := http.NewRequest("POST", url, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.HTTPClient.Do(req)
	if err != nil { return nil, err }
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		log.Printf("[DEBUG] Ollama returned status %d for path %s", resp.StatusCode, path)
	}

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)
	return result, nil
}
