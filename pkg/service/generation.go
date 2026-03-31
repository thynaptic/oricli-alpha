package service

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"runtime"
	"strings"
	"time"

	"github.com/thynaptic/oricli-go/pkg/metacog"
	"github.com/thynaptic/oricli-go/pkg/scl"
	"github.com/thynaptic/oricli-go/pkg/therapy"
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
	RunPodMgr      *RunPodManager           // KoboldCpp-based (code/research tiers, legacy)
	PrimaryMgr     *PrimaryInferenceManager // vLLM-based (all tiers, RUNPOD_PRIMARY=true)
	Governor       *CostGovernor            // daily spend cap — blocks RunPod escalation when exhausted
	CrystalCache   *scl.CrystalCache        // Skill Crystallization — LLM-bypass for proven patterns
	MetacogDetector *metacog.Detector        // Phase 8: inline metacognitive anomaly detection
	Therapy         *TherapyKit              // Phase 15: DBT/CBT/REBT therapeutic cognition stack
}

// TherapyKit groups Phase 15 components injected from main.go.
// Using a wrapper struct avoids a large number of optional fields.
type TherapyKit struct {
	Skills  *therapy.SkillRunner
	Detect  *therapy.DistortionDetector
	ABC     *therapy.ABCAuditor
	Chain   *therapy.ChainAnalyzer
	Log     *therapy.EventLog
}

// DefaultLLMModel returns the configured chat model from OLLAMA_MODEL env var.
// All background daemons should use this instead of hardcoded model names so
// that the same model stays resident in Ollama memory and avoids eviction.
func DefaultLLMModel() string {
	if m := os.Getenv("OLLAMA_MODEL"); m != "" {
		return m
	}
	return "qwen3:1.7b"
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
	svc := &GenerationService{
		BaseURL:       url,
		GenerateURL:   genUrl,
		DefaultModel:  model,
		CodeModel:     codeModel,
		ResearchModel: researchModel,
		NumThreads:    numThreads,
		HTTPClient:    &http.Client{Timeout: 300 * time.Second, Transport: transport},
		StreamClient:  &http.Client{Timeout: 0, Transport: transport},
		RunPodMgr:     NewRunPodManager(),
		PrimaryMgr:    NewPrimaryInferenceManager(),
	}
	if svc.PrimaryMgr != nil && os.Getenv("RUNPOD_PRIMARY") == "true" {
		log.Printf("[GenerationService] RUNPOD_PRIMARY=true — all tiers will route through vLLM pod")
		svc.PrimaryMgr.WarmOnStart()
	}
	return svc
}

// prewarmModel sends a minimal chat request to Ollama to load the model into RAM.
// Sets keep_alive to 60m so it stays hot between conversations.
func (s *GenerationService) prewarmModel(model string) {
	payload := map[string]interface{}{
		"model":      model,
		"messages":   []map[string]interface{}{{"role": "user", "content": "."}},
		"stream":     false,
		"keep_alive": "60m",
		"options":    map[string]interface{}{"num_predict": 1},
	}
	if strings.HasPrefix(strings.ToLower(model), "qwen3") {
		payload["think"] = false
	}
	body, _ := json.Marshal(payload)
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, "POST", s.GenerateURL+"/api/chat", bytes.NewReader(body))
	if err != nil {
		log.Printf("[GenerationService] pre-warm request error: %v", err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := s.HTTPClient.Do(req)
	if err != nil {
		log.Printf("[GenerationService] pre-warm failed for %s: %v", model, err)
		return
	}
	resp.Body.Close()
	log.Printf("[GenerationService] pre-warm complete: %s is ready", model)
}

// --- PROMPT ENGINEERING & PHRASING ---

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

	// ── Skill Crystallization: LLM-bypass for proven patterns ──
	if s.CrystalCache != nil {
		if resp, skillID, hit := s.CrystalCache.Match(prompt); hit {
			log.Printf("[Crystal] HIT skill=%s — LLM bypassed", skillID)
			return map[string]interface{}{
				"success":  true,
				"text":     resp,
				"response": resp,
				"model":    "crystal/" + skillID,
				"method":   "crystal_bypass",
				"confidence": 0.99,
			}, nil
		}
	}

	// When RUNPOD_PRIMARY=true and the pod is warm, route Generate through the 32B
	// vLLM pod. This ensures PAL code generation, SelfDiscover reasoning steps, and
	// any other Generate callers benefit from the full model — not just ChatStream.
	if s.PrimaryMgr != nil && s.PrimaryMgr.IsEnabled() &&
		os.Getenv("RUNPOD_PRIMARY") == "true" && s.PrimaryMgr.PodState() == StateWarm {
		msgs := []map[string]string{{"role": "user", "content": prompt}}
		if sys, ok := options["system"].(string); ok && sys != "" {
			msgs = append([]map[string]string{{"role": "system", "content": sys}}, msgs...)
		}
		genCtx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
		defer cancel()
		ch, err := s.PrimaryMgr.ChatStream(genCtx, msgs, options)
		if err == nil {
			var sb strings.Builder
			for tok := range ch {
				sb.WriteString(tok)
			}
			if text := strings.TrimSpace(sb.String()); text != "" {
				return map[string]interface{}{"success": true, "response": text, "text": text, "model": model, "method": "runpod_primary", "confidence": 0.97}, nil
			}
		}
		log.Printf("[GenerationService] Generate: RunPod fallback to Ollama (%v)", err)
	}

	// num_ctx MUST match ChatStream (4096) so Ollama never reallocates the KV cache.
	// A mismatch causes a full model reload (~20-60s) on the next chat request.
	payload := map[string]interface{}{"model": model, "prompt": prompt, "stream": false, "options": map[string]interface{}{"num_thread": s.NumThreads, "num_ctx": 4096, "num_predict": 512}}

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
			if s.MetacogDetector != nil {
				if evt := s.MetacogDetector.Check(prompt, resp); evt != nil && evt.Severity == "HIGH" {
					log.Printf("[Metacog] %s — retrying with self-reflection prefix", evt.Type)
					reflectPrompt := metacog.SelfReflectPrompt(evt)
					reflectPrompt += s.therapyAugment(prompt, resp, evt.ID, string(evt.Type))
					reflectPrompt += prompt
					retry, rerr := s.Chat([]map[string]string{{"role": "user", "content": reflectPrompt}}, options)
					if rerr == nil {
						return retry, nil
					}
				}
			}
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

	payload := map[string]interface{}{"model": model, "messages": ollamaMessages, "stream": false, "think": false, "options": map[string]interface{}{"num_thread": s.NumThreads, "num_ctx": 4096, "num_predict": 512}}

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
			if s.MetacogDetector != nil {
				// Derive a representative prompt from the last user message
				promptForCheck := ""
				if len(messages) > 0 {
					promptForCheck = messages[len(messages)-1]["content"]
				}
				if evt := s.MetacogDetector.Check(promptForCheck, content); evt != nil && evt.Severity == "HIGH" {
					log.Printf("[Metacog] %s in Chat — retrying with self-reflection prefix", evt.Type)
					therapyCtx := s.therapyAugment(promptForCheck, content, evt.ID, string(evt.Type))
					// Prepend self-reflection as a new system message + replay conversation
					reflectContent := metacog.SelfReflectPrompt(evt) + therapyCtx
					reflectMsg := map[string]string{"role": "system", "content": reflectContent}
					retryMsgs := append([]map[string]string{reflectMsg}, messages...)
					retryOpts := make(map[string]interface{})
					for k, v := range options {
						retryOpts[k] = v
					}
					retryOpts["_metacog_retry"] = true // prevent infinite recursion
					if _, isRetry := options["_metacog_retry"]; !isRetry {
						if retry, rerr := s.Chat(retryMsgs, retryOpts); rerr == nil {
							return retry, nil
						}
					}
				}
			}
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

	// ── Complexity routing — auto-escalate hard tasks to RunPod ──────────
	// Runs before explicit tier checks so it can upgrade an unclassified
	// request. Explicit model/tier overrides from the caller still win.
	if IsComplexityRoutingEnabled() {
		complexity := ClassifyComplexity(messages)
		if complexity.Tier > TierLocal {
			// Governor hard-cap: if daily budget is exhausted, stay local.
			estimatedCost := EstimateRunPodCost(1)
			if s.Governor != nil && !s.Governor.CanSpend(estimatedCost) {
				log.Printf("[GenerationService] CostGovernor: daily cap hit — forcing TierLocal (was %s)", complexity.Tier)
			} else {
				ApplyComplexityRouting(complexity, options)
				log.Printf("[GenerationService] complexity=%s score=%.2f reasons=%v",
					complexity.Tier, complexity.Score, complexity.Reasons)
			}
		}
	}

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

	// Complexity router heavy escalation — treat as RunPod primary even if
	// RUNPOD_PRIMARY=false. Lets specific hard tasks spin up the pod on demand.
	escalate, _ := options["_escalate_to_runpod"].(bool)
	if escalate && s.PrimaryMgr != nil && s.PrimaryMgr.IsEnabled() && os.Getenv("RUNPOD_PRIMARY") != "true" {
		log.Printf("[GenerationService] complexity escalation → PrimaryMgr (RunPod)")
		out := make(chan string, 64)
		go func() {
			defer close(out)
			podState := s.PrimaryMgr.PodState()
			if podState == StateOff || podState == StateWarming {
				out <- podCallout("escalation")
			}
			ch, err := s.PrimaryMgr.ChatStream(ctx, messages, options)
			if err != nil {
				log.Printf("[GenerationService] escalation RunPod failed (%v) — falling back to Ollama", err)
				out <- podCallout("fallback")
				if ollamaCh, oErr := s.ollamaChatStream(ctx, messages, model, options); oErr == nil {
					for tok := range ollamaCh {
						out <- tok
					}
				}
				return
			}
			for tok := range ch {
				out <- tok
			}
		}()
		return out, nil
	}

	// RUNPOD_PRIMARY mode: route ALL tiers through the vLLM pod.
	// Emits a personality callout if the pod is cold, then blocks on Ensure.
	// If the pod never comes up, falls back to Ollama in the same channel.
	if s.PrimaryMgr != nil && s.PrimaryMgr.IsEnabled() && os.Getenv("RUNPOD_PRIMARY") == "true" {
		podState := s.PrimaryMgr.PodState()
		podModel := s.PrimaryMgr.PodModelName()
		wasWaiting := podState == StateOff || podState == StateWarming

		out := make(chan string, 64)
		go func() {
			defer close(out)

			// Escalation callout if the pod is cold or still warming up.
			if podState == StateOff {
				if podModel != "" {
					out <- podCalloutWithModel(podModel)
				} else {
					out <- podCallout("escalation")
				}
			} else if podState == StateWarming {
				out <- podCallout("warming")
			}

			ch, err := s.PrimaryMgr.ChatStream(ctx, messages, options)
			if err != nil {
				log.Printf("[GenerationService] PrimaryMgr unavailable (%v) — falling back to Ollama", err)
				out <- podCallout("fallback")
				// Pipe Ollama into the same channel so the user gets a real response.
				ollamaCh, oErr := s.ollamaChatStream(ctx, messages, model, options)
				if oErr == nil {
					for tok := range ollamaCh {
						out <- tok
					}
				}
				return
			}

			// Success handoff — only when the user actually waited for the pod.
			if wasWaiting {
				out <- podHandoff(s.PrimaryMgr.PodModelName())
			}

			for tok := range ch {
				out <- tok
			}
		}()
		return out, nil
	}

	// Route code/research tiers to KoboldCpp RunPod when enabled (legacy path).
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

	return s.ollamaChatStream(ctx, messages, model, options)
}

// DirectOllama bypasses all routing logic (RunPod, complexity escalation, vLLM)
// and calls Ollama synchronously. Use for bench/studio paths where latency matters
// more than capability and adding a 15s vLLM timeout is unacceptable.
func (s *GenerationService) DirectOllama(ctx context.Context, messages []map[string]string, options map[string]interface{}) (<-chan string, error) {
	model := s.DefaultModel
	if m, ok := options["model"].(string); ok && m != "" {
		model = m
	}
	return s.ollamaChatStream(ctx, messages, model, options)
}

// ollamaChatStream is the raw Ollama streaming path, extracted so it can be
// called directly as a fallback from the RunPod routing block.
func (s *GenerationService) ollamaChatStream(ctx context.Context, messages []map[string]string, model string, options map[string]interface{}) (<-chan string, error) {
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
		"model":      model,
		"messages":   ollamaMessages,
		"stream":     true,
		"keep_alive": "60m", // keep model hot; cold loads take 60+ s on CPU-only VPS
		"options": map[string]interface{}{
			"num_thread":  s.NumThreads, // auto-detected at boot; prevents vCPU over-subscription
			"num_ctx":     4096, // covers system-prompt + skill + RAG + history comfortably
			"num_predict": 512,  // 512 tokens covers most conversational answers; canvas overrides to -1
		},
	}
	if temp, ok := options["temperature"].(float64); ok {
		payload["options"].(map[string]interface{})["temperature"] = temp
	}
	// Disable Qwen3 extended thinking for chat to keep tok/s high.
	// Only set on qwen3 models — other models silently drop the stream when this field is present.
	if strings.HasPrefix(strings.ToLower(model), "qwen3") {
		payload["think"] = false
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
		errBody, _ := io.ReadAll(io.LimitReader(resp.Body, 512))
		resp.Body.Close()
		return nil, fmt.Errorf("Ollama returned status %d for streaming chat: %s", resp.StatusCode, strings.TrimSpace(string(errBody)))
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

// DirectOllamaSingle makes a single (non-streaming) Ollama call and returns the
// full response text. Used by subsystems that need a simple string back (Sentinel,
// Curator, Crystallization checks) without managing a streaming channel.
func (s *GenerationService) DirectOllamaSingle(ctx context.Context, messages []map[string]string) (string, error) {
	model := s.DefaultModel
	ollamaMessages := make([]map[string]interface{}, len(messages))
	for i, msg := range messages {
		ollamaMessages[i] = map[string]interface{}{"role": msg["role"], "content": msg["content"]}
	}
	payload := map[string]interface{}{
		"model":      model,
		"messages":   ollamaMessages,
		"stream":     false,
		"keep_alive": "60m",
		"options": map[string]interface{}{
			"num_thread":  s.NumThreads,
			"num_ctx":     4096,
			"num_predict": 1024,
			"temperature": 0.2,
		},
	}
	if strings.HasPrefix(strings.ToLower(model), "qwen3") {
		payload["think"] = false
	}
	result, err := s.postJSON("/api/chat", payload)
	if err != nil {
		return "", err
	}
	if msg, ok := result["message"].(map[string]interface{}); ok {
		if content, ok := msg["content"].(string); ok {
			return content, nil
		}
	}
	return "", fmt.Errorf("unexpected ollama response shape: %v", result)
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

// ---------------------------------------------------------------------------
// Phase 15 — Therapy augmentation
// ---------------------------------------------------------------------------

// therapyAugment runs Phase 15 therapy layer on a HIGH anomaly.
// Returns additional context to prepend to the self-reflection prompt.
// Never blocks — all therapy paths are fail-open.
func (s *GenerationService) therapyAugment(query, response, anomalyID, anomalyType string) string {
if s.Therapy == nil {
return ""
}
t := s.Therapy

// 1. STOP — log and flag the pause
stopInv := t.Skills.STOP(anomalyType, response)
log.Printf("[Therapy] STOP invoked — %s", stopInv.Reason)

// 2. Detect distortion
result := t.Detect.Detect(response, anomalyType)
log.Printf("[Therapy] Distortion detected: %s (%.2f, %s)", result.Distortion, result.Confidence, result.Source)

// 3. Record in chain analyzer for audit trail
if t.Chain != nil {
t.Chain.Record(query, response, result.Distortion, 0.0, 0.0, anomalyType)
}

// 4. Build targeted therapy context for the retry prompt
if result.Distortion == therapy.DistortionNone {
return "\n[THERAPY] No specific cognitive distortion detected. Apply general Beginner's Mind — reset assumptions and respond from first principles.\n"
}

return "\n[THERAPY] Cognitive distortion detected: " + string(result.Distortion) + ".\n" +
"Evidence: " + result.Evidence + "\n" +
"Correction: " + distortionCorrectionHint(result.Distortion) + "\n"
}

// distortionCorrectionHint returns a one-line corrective instruction per distortion type.
func distortionCorrectionHint(d therapy.DistortionType) string {
switch d {
case therapy.AllOrNothing:
return "Avoid absolute framing. Present partial, nuanced, or conditional answers."
case therapy.FortuneTelling:
return "Do not predict outcomes as certainties. State what is known and what is uncertain."
case therapy.Magnification:
return "Scale confidence to match actual evidence. Avoid amplifying uncertainty or certainty beyond what the data supports."
case therapy.EmotionalReasoning:
return "Separate tone from logic. Base the answer on facts, not on the emotional register of the query."
case therapy.ShouldStatements:
return "Replace rigid 'must/should/always' framing with conditional or contextual framing."
case therapy.Overgeneralization:
return "Limit the scope of claims to what was actually observed or asked. Do not extrapolate broadly."
case therapy.MindReading:
return "Respond to what was literally asked. Do not assume hidden intent or unstated meaning."
case therapy.Labeling:
return "Describe the specific situation rather than applying a categorical label."
case therapy.Personalization:
return "Attribute causes accurately. Avoid taking on responsibility that belongs to external factors."
default:
return "Apply Describe-No-Judge: state observations without evaluative framing."
}
}
