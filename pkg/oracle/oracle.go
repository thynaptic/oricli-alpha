package oracle

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	copilot "github.com/github/copilot-sdk/go"
	"gopkg.in/yaml.v3"
)

var (
	client     *copilot.Client
	clientMu   sync.RWMutex
	clientOnce sync.Once
)

const (
	defaultCopilotPort = 8090
	sessionTTL         = 30 * time.Minute
)

// Route tier defaults — used when the SDK catalog hasn't loaded yet.
// These are intentionally conservative: real selection happens via RefreshModelCatalog.

// sessionEntry holds a live SDK session and its last-used timestamp.
type sessionEntry struct {
	session  *copilot.Session
	lastUsed time.Time
}

// sessionPool maps sessionID → *sessionEntry. Sessions are reused across turns.
var sessionPool sync.Map

// agentCache avoids re-reading .github/agents/ on every session use.
var (
	agentCache    []copilot.CustomAgentConfig
	agentCacheMu  sync.RWMutex
	agentCacheAt  time.Time
	agentCacheTTL = 5 * time.Minute
)

const (
	defaultCopilotLightModel    = "claude-haiku-4.5"
	defaultCopilotHeavyModel    = "auto"
	defaultCopilotResearchModel = "claude-sonnet-4.6"
)

// Init initializes the Copilot SDK client.
func Init(port int) {
	clientOnce.Do(func() {
		// Let the SDK manage its own copilot subprocess (stdio mode, dynamic port).
		// DaemonManager still starts a daemon for legacy use, but the SDK process
		// is independent to avoid port conflicts and ACP handshake hangs.
		client = copilot.NewClient(nil)
		startCtx, startCancel := context.WithTimeout(context.Background(), 20*time.Second)
		defer startCancel()
		if err := client.Start(startCtx); err != nil {
			log.Printf("[Oracle] Failed to start Copilot SDK client: %v", err)
			client = nil
		} else {
			log.Printf("[Oracle] Copilot SDK client ready (port %d daemon also running)", port)
		}
		go RefreshModelCatalog()
		go sessionReaper()
	})
}

// CloseSession explicitly disconnects and removes a session from the pool.
// Call this when a conversation is definitively over (e.g. user logout, session expiry).
func CloseSession(sessionID string) {
	if v, ok := sessionPool.LoadAndDelete(sessionID); ok {
		entry := v.(*sessionEntry)
		entry.session.Disconnect()
	}
}

// sessionReaper runs in the background and disconnects sessions idle for > sessionTTL.
func sessionReaper() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()
	for range ticker.C {
		now := time.Now()
		sessionPool.Range(func(key, value any) bool {
			entry := value.(*sessionEntry)
			if now.Sub(entry.lastUsed) > sessionTTL {
				sessionPool.Delete(key)
				entry.session.Disconnect()
				log.Printf("[Oracle] session %s reaped after idle TTL", key)
			}
			return true
		})
	}
}

// GetClient returns the global SDK client instance.
func GetClient() *copilot.Client {
	clientMu.RLock()
	defer clientMu.RUnlock()
	return client
}

type Message struct {
	Role    string
	Content string
}

type Result struct {
	Answer string
	Source string
}

// Query performs a single-turn query using the Oracle.
func Query(stimulus string) *Result {
	return QueryWithDecision(stimulus, Decide(stimulus, RouteHints{IsCodeAction: true}), "default")
}

// QueryWithDecision performs a query with a pre-made decision.
func QueryWithDecision(stimulus string, decision Decision, sessionID string) *Result {
	if decision.Route == RouteImageReasoning {
		// Image reasoning now handled via SDK session
		log.Printf("[Oracle] Routing image-based query via SDK")
	}

	ch := ChatStreamWithDecision(context.Background(), []Message{{Role: "user", Content: stimulus}}, decision, sessionID)
	answer := Collect(ch)
	if answer == "" {
		return nil
	}
	return &Result{Answer: answer, Source: "copilot-sdk"}
}

// ChatStreamWithDecision streams a multi-turn conversation using the Oracle SDK.
// Sessions are pooled by sessionID — cold-start cost is paid once per conversation,
// not once per message.
func ChatStreamWithDecision(ctx context.Context, messages []Message, decision Decision, sessionID string) <-chan string {
	out := make(chan string, 128)
	c := GetClient()
	if c == nil {
		go func() {
			out <- "[Oracle SDK client not initialized]"
			close(out)
		}()
		return out
	}

	go func() {
		defer close(out)

		session, err := getOrCreateSession(ctx, c, messages, decision, sessionID)
		if err != nil {
			out <- fmt.Sprintf("[Oracle SDK Session Error: %v]", err)
			return
		}

		// Update last-used so the reaper doesn't evict a live session.
		if v, ok := sessionPool.Load(sessionID); ok {
			v.(*sessionEntry).lastUsed = time.Now()
		}

		// 1. Handle Streaming via Events
		unsubscribe := session.On(func(event copilot.SessionEvent) {
			if event.Type == copilot.SessionEventTypeAssistantMessageDelta {
				if d, ok := event.Data.(*copilot.AssistantMessageDeltaData); ok {
					out <- d.DeltaContent
				}
			}
		})
		defer unsubscribe()

		// 2. Send with Mode handling (Steering)
		lastMsg := ""
		if len(messages) > 0 {
			lastMsg = messages[len(messages)-1].Content
		}
		mode := "enqueue"
		if isSteeringIntent(lastMsg) {
			mode = "immediate"
		}

		opts := copilot.MessageOptions{
			Prompt: lastMsg,
			Mode:   mode,
		}
		if decision.Route == RouteImageReasoning {
			opts.Attachments = extractImageAttachments(lastMsg)
		}

		_, err = session.Send(ctx, opts)
		if err != nil {
			// Session may be dead — evict so next request gets a fresh one.
			sessionPool.Delete(sessionID)
			session.Disconnect()
			out <- fmt.Sprintf("[Oracle SDK Send Error: %v]", err)
			return
		}

		// 3. Wait for turn completion
		turnDone := make(chan struct{}, 1)
		session.On(func(event copilot.SessionEvent) {
			if event.Type == copilot.SessionEventTypeAssistantTurnEnd {
				select {
				case turnDone <- struct{}{}:
				default:
				}
			}
		})

		select {
		case <-turnDone:
		case <-ctx.Done():
		}
	}()

	return out
}

// getOrCreateSession returns a pooled session for sessionID, creating one if needed.
func getOrCreateSession(ctx context.Context, c *copilot.Client, messages []Message, decision Decision, sessionID string) (*copilot.Session, error) {
	if v, ok := sessionPool.Load(sessionID); ok {
		return v.(*sessionEntry).session, nil
	}

	// Cap session creation independently — CreateSession can hang if the daemon
	// is unresponsive without the caller's context ever timing out.
	createCtx, createCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer createCancel()

	agents := cachedLoadCustomAgents(".github/agents")

	config := &copilot.SessionConfig{
		SessionID:           sessionID,
		Agent:               decision.Agent,
		Model:               decision.Model,
		Streaming:           true,
		CustomAgents:        agents,
		SkillDirectories:    []string{".github/skills", "oricli_core/skills"},
		OnPermissionRequest: copilot.PermissionHandler.ApproveAll,
	}

	// Only wire MCP for routes that actually invoke tools.
	// Light/chat routes skip it — MCP OAuth discovery adds 30-80s to session init.
	if decision.Route == RouteHeavyReasoning || decision.Route == RouteResearch {
		config.MCPServers = map[string]copilot.MCPServerConfig{
			"ori-runtime": copilot.MCPHTTPServerConfig{
				URL: "https://glm.thynaptic.com/v1/mcp",
				Headers: map[string]string{
					"Authorization": "Bearer ori.8f9f406a.Mo5YFWO0Tx5IKE46fG1mXfA7kAyLzy",
				},
			},
		}
	}
	if len(messages) > 0 && messages[0].Role == "system" {
		config.SystemMessage = &copilot.SystemMessageConfig{
			Mode:    "replace",
			Content: messages[0].Content,
		}
	}

	session, err := c.CreateSession(createCtx, config)
	if err != nil {
		log.Printf("[Oracle] CreateSession failed (id=%q): %v", sessionID, err)
		resumeConfig := &copilot.ResumeSessionConfig{
			Model:               config.Model,
			CustomAgents:        config.CustomAgents,
			MCPServers:          config.MCPServers,
			SkillDirectories:    config.SkillDirectories,
			SystemMessage:       config.SystemMessage,
			Streaming:           true,
			OnPermissionRequest: copilot.PermissionHandler.ApproveAll,
		}
		session, err = c.ResumeSession(createCtx, sessionID, resumeConfig)
		if err != nil {
			return nil, err
		}
	}

	sessionPool.Store(sessionID, &sessionEntry{session: session, lastUsed: time.Now()})
	log.Printf("[Oracle] session %s created (model=%s)", sessionID, decision.Model)
	return session, nil
}

// cachedLoadCustomAgents returns LoadCustomAgents results, re-reading disk at most every 5 min.
func cachedLoadCustomAgents(dir string) []copilot.CustomAgentConfig {
	agentCacheMu.RLock()
	if time.Since(agentCacheAt) < agentCacheTTL {
		cached := agentCache
		agentCacheMu.RUnlock()
		return cached
	}
	agentCacheMu.RUnlock()

	agents, err := LoadCustomAgents(dir)
	if err != nil {
		return nil
	}

	agentCacheMu.Lock()
	agentCache = agents
	agentCacheAt = time.Now()
	agentCacheMu.Unlock()
	return agents
}

// LoadCustomAgents parses .agent.md files into SDK CustomAgent structs.
func LoadCustomAgents(dir string) ([]copilot.CustomAgentConfig, error) {
	files, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}

	var agents []copilot.CustomAgentConfig
	for _, f := range files {
		if !f.IsDir() && strings.HasSuffix(f.Name(), ".agent.md") {
			path := filepath.Join(dir, f.Name())
			data, err := os.ReadFile(path)
			if err != nil {
				continue
			}

			parts := strings.SplitN(string(data), "---", 3)
			if len(parts) < 3 {
				continue
			}

			var metadata struct {
				Name        string   `yaml:"name"`
				Description string   `yaml:"description"`
				Tools       []string `yaml:"tools"`
			}
			if err := yaml.Unmarshal([]byte(parts[1]), &metadata); err != nil {
				continue
			}

			agents = append(agents, copilot.CustomAgentConfig{
				Name:        metadata.Name,
				Description: metadata.Description,
				Tools:       metadata.Tools,
				Prompt:      strings.TrimSpace(parts[2]),
			})
		}
	}
	return agents, nil
}

func isSteeringIntent(msg string) bool {
	lower := strings.ToLower(msg)
	return strings.HasPrefix(lower, "stop") || 
		strings.HasPrefix(lower, "actually") || 
		strings.HasPrefix(lower, "no, ") ||
		strings.HasPrefix(lower, "wait")
}

func ShouldQuery(stimulus string, trapCount int) bool {
	if trapCount == 0 {
		return false
	}
	s := strings.ToLower(strings.TrimSpace(stimulus))
	return strings.Contains(s, "?") || strings.HasPrefix(s, "how") ||
		strings.HasPrefix(s, "what") || strings.HasPrefix(s, "why") ||
		strings.HasPrefix(s, "which") || strings.HasPrefix(s, "do i") ||
		strings.HasPrefix(s, "does")
}

func extractImageAttachments(msg string) []copilot.Attachment {
	var attachments []copilot.Attachment
	// Simple heuristic: look for absolute paths ending in image extensions
	words := strings.Fields(msg)
	for _, w := range words {
		ext := strings.ToLower(filepath.Ext(w))
		if ext == ".png" || ext == ".jpg" || ext == ".jpeg" || ext == ".webp" {
			if filepath.IsAbs(w) {
				if _, err := os.Stat(w); err == nil {
					p := w // capture local var
					attachments = append(attachments, copilot.Attachment{
						Type: "file",
						Path: &p,
					})
				}
			}
		}
	}
	return attachments
}

func copilotModelForRoute(route Route) string {
	// 1. Explicit env overrides always win.
	switch route {
	case RouteHeavyReasoning:
		if m := strings.TrimSpace(os.Getenv("ORACLE_COPILOT_MODEL_HEAVY")); m != "" {
			return m
		}
	case RouteResearch:
		if m := strings.TrimSpace(os.Getenv("ORACLE_COPILOT_MODEL_RESEARCH")); m != "" {
			return m
		}
		if m := strings.TrimSpace(os.Getenv("ORACLE_COPILOT_MODEL_HEAVY")); m != "" {
			return m
		}
	default:
		if m := strings.TrimSpace(os.Getenv("ORACLE_COPILOT_MODEL_LIGHT")); m != "" {
			return m
		}
	}
	if m := strings.TrimSpace(os.Getenv("ORACLE_COPILOT_MODEL")); m != "" && !strings.HasPrefix(m, "gpt-4.1") {
		return m
	}

	// 2. Catalog selection (auto-refreshed, 24h TTL).
	if m := catalogModelForRoute(route); m != "" {
		return m
	}

	// 3. Hardcoded defaults as last resort.
	switch route {
	case RouteHeavyReasoning:
		return defaultCopilotHeavyModel
	case RouteResearch:
		return defaultCopilotResearchModel
	default:
		return defaultCopilotLightModel
	}
}

// FormatInjection maintains backward compatibility for system prompt overrides.
func FormatInjection(r *Result) string {
	if r == nil {
		return ""
	}
	return fmt.Sprintf(
		"### SYSTEM OVERRIDE — FINAL ANSWER PROVIDED\n"+
			"A trusted high-capability system has already solved this question.\n"+
			"STOP. Do not reason. Do not compute. Do not second-guess.\n"+
			"Your ONLY task is to state this answer exactly:\n"+
			"ANSWER: %s\n"+
			"### END SYSTEM OVERRIDE\n",
		r.Answer,
	)
}

// Collect drains a ChatStream channel and returns the full response string.
func Collect(ch <-chan string) string {
	var sb strings.Builder
	for tok := range ch {
		sb.WriteString(tok)
	}
	return sb.String()
}

func Available() bool {
	return GetClient() != nil
}

func AvailableForRoute(route Route) bool {
	return Available()
}

// ConvertMsgs is kept for compatibility.
func ConvertMsgs(msgs []map[string]string) []Message {
	out := make([]Message, 0, len(msgs))
	for _, m := range msgs {
		out = append(out, Message{Role: m["role"], Content: m["content"]})
	}
	return out
}
