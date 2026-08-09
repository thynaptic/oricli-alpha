package memory

import (
	"fmt"
	"log"
	"path/filepath"
	"strings"
	"time"
)

// Runtime wires the consumer memory stack for the API layer.
type Runtime struct {
	Dir     string
	Bridge  *Bridge
	Sessions *SessionStore
	Belief  *BeliefTracker
	Chronos *ChronosIndex
	Graph   *WorkingGraph
	Clock   *Clock
	State   *StateTools
	Affect  *AffectStore
	Cache   *ResponseCache
	Pool    *TouchPool
	Spaces  *SpacesStore
	Tasks   *TaskStore
}

type OpenOptions struct {
	Dir            string
	EncryptionKey  string
	MaxSessionTurns int
}

func Open(opts OpenOptions) (*Runtime, error) {
	dir := opts.Dir
	if dir == "" {
		dir = ".memory"
	}
	bridge, err := OpenBridge(dir, opts.EncryptionKey)
	if err != nil {
		return nil, fmt.Errorf("memory bridge: %w", err)
	}
	spaces, err := NewSpacesStore(filepath.Join(dir, "spaces"))
	if err != nil {
		_ = bridge.Close()
		return nil, err
	}
	tasks, err := OpenTaskStore(filepath.Join(dir, "tasks"))
	if err != nil {
		_ = bridge.Close()
		return nil, err
	}
	tools := NewStateTools(bridge)
	rt := &Runtime{
		Dir:      dir,
		Bridge:   bridge,
		Sessions: NewSessionStore(bridge, opts.MaxSessionTurns),
		Belief:   NewBeliefTracker(),
		Chronos:  NewChronosIndex(2000),
		Graph:    NewWorkingGraph(),
		Clock:    NewClock(filepath.Join(dir, "session_chronos")),
		State:    tools,
		Affect:   NewAffectStore(tools),
		Cache:    NewResponseCache(filepath.Join(dir, "cache")),
		Pool:     NewTouchPool(30 * time.Minute),
		Spaces:   spaces,
		Tasks:    tasks,
	}
	log.Printf("[memory] ready dir=%s bridge=bbolt sessions chronos graph belief cache spaces tasks", dir)
	return rt, nil
}

func (rt *Runtime) Close() {
	if rt == nil {
		return
	}
	if rt.Tasks != nil {
		_ = rt.Tasks.Close()
	}
	if rt.Bridge != nil {
		_ = rt.Bridge.Close()
	}
}

// ChatMessage is a minimal role/content pair for merge helpers.
type ChatMessage struct {
	Role    string
	Content string
}

// PrepareChat loads session history (if thin client history), updates belief/clock/graph,
// and returns prompt fragments + possibly expanded messages. No embeds.
func (rt *Runtime) PrepareChat(sessionID string, msgs []ChatMessage) (expanded []ChatMessage, extras string, cacheHit string) {
	if rt == nil {
		return msgs, "", ""
	}
	rt.Pool.Touch(sessionID)

	var lastUser string
	for i := len(msgs) - 1; i >= 0; i-- {
		if msgs[i].Role == "user" {
			lastUser = msgs[i].Content
			break
		}
	}

	if lastUser != "" {
		if hit, ok := rt.Cache.Get(lastUser); ok {
			cacheHit = hit
		}
	}

	expanded = msgs
	if sessionID != "" {
		stored, err := rt.Sessions.Load(sessionID)
		if err != nil {
			log.Printf("[memory] session load: %v", err)
		} else if len(stored) > 0 {
			in := make([]struct{ Role, Content string }, len(msgs))
			for i, m := range msgs {
				in[i] = struct{ Role, Content string }{m.Role, m.Content}
			}
			merged := MergeForRequest(stored, in, 24)
			expanded = make([]ChatMessage, len(merged))
			for i, m := range merged {
				expanded[i] = ChatMessage{Role: m.Role, Content: m.Content}
			}
		}
		rt.Clock.RecordActivity(sessionID)
		if lastUser != "" {
			rt.Clock.RecordEvent(sessionID, EventUser, lastUser)
			rt.Graph.NoteTurn(sessionID, lastUser)
		}
	}

	if lastUser != "" {
		bs := rt.Belief.Get(sessionID)
		bs.Update(lastUser)
		rt.Affect.Touch(sessionID, float64(bs.FrustrationRisk), bs.CurrentGoal)
	}

	var parts []string
	if sessionID != "" {
		if t := rt.Clock.FormatForPrompt(sessionID); t != "" {
			parts = append(parts, t)
		}
	}
	if b := rt.Belief.Get(sessionID).FormatForPrompt(); b != "" {
		parts = append(parts, b)
	}
	if lastUser != "" {
		if hits := rt.Graph.KeywordHits(lastUser, 5); len(hits) > 0 {
			var sb strings.Builder
			sb.WriteString("### WORKING MEMORY GRAPH\n")
			for _, h := range hits {
				sb.WriteString("- " + h.Content + "\n")
			}
			sb.WriteString("### END WORKING MEMORY GRAPH")
			parts = append(parts, sb.String())
		}
	}
	return expanded, strings.Join(parts, "\n\n"), cacheHit
}

// AfterReply persists turns + chronos observe asynchronously (never blocks TTFB).
func (rt *Runtime) AfterReply(sessionID, userText, assistantText string) {
	if rt == nil {
		return
	}
	go func() {
		now := time.Now().UTC()
		if sessionID != "" {
			turns := []Turn{}
			if userText != "" {
				turns = append(turns, Turn{Role: "user", Content: userText, At: now})
			}
			if assistantText != "" {
				turns = append(turns, Turn{Role: "assistant", Content: assistantText, At: now})
			}
			if err := rt.Sessions.Append(sessionID, turns...); err != nil {
				log.Printf("[memory] session append: %v", err)
			}
			rt.Clock.RecordEvent(sessionID, EventAssistant, assistantText)
			_ = rt.Bridge.Put(CatEpisodic, fmt.Sprintf("%s-%d", sessionID, now.UnixNano()), map[string]any{
				"session_id": sessionID,
				"user":       truncate(userText, 2000),
				"assistant":  truncate(assistantText, 4000),
			}, map[string]any{"source": "chat"})
		}
		rt.Chronos.Observe(ObserveInput{
			ID:         fmt.Sprintf("chat-%d", now.UnixNano()),
			Content:    truncate(userText+" → "+assistantText, 500),
			Topic:      extractTopic(userText),
			Source:     "conversation",
			Importance: 0.5,
			Volatility: "current",
			CreatedAt:  now,
		})
		if userText != "" && assistantText != "" {
			rt.Cache.PutAsync(userText, assistantText)
		}
	}()
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n]
}
