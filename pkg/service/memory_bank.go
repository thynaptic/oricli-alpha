package service

import (
	"context"
	"fmt"
	"log"
	"math"
	"os"
	"strconv"
	"strings"
	"time"

	pb "github.com/thynaptic/oricli-go/pkg/connectors/pocketbase"
)

// MemoryBank bridges Oricli's runtime to PocketBase long-term storage.
//
// Architecture:
//   Hot  → chromem-go     (in-process vectors, session-scope)
//   Warm → LMDB           (fast KV, cross-session, local)
//   Cold → PocketBase     (durable, 200GB, long-term recall)
//
// This layer handles the cold tier: conversation fragments, curiosity findings,
// spend ledger (survives restarts), and conversation summaries for RAG.
type MemoryBank struct {
	client    *pb.Client
	maxRecs   int
	enabled   bool
}

// MemoryFragment is a unit of long-term memory.
type MemoryFragment struct {
	ID          string
	Content     string
	Source      string  // "conversation" | "curiosity" | "summary"
	Topic       string
	SessionID   string
	Importance  float64 // 0.0–1.0
	AccessCount int
	LastAccessed time.Time
}

// NewMemoryBank creates a MemoryBank from environment config.
// If PB_BASE_URL is not set, returns a disabled no-op bank.
func NewMemoryBank() *MemoryBank {
	client := pb.NewClientFromEnv()
	maxRecs := 500000
	if v := os.Getenv("PB_MEMORY_MAX_RECORDS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			maxRecs = n
		}
	}
	enabled := client.IsConfigured()
	if !enabled {
		log.Println("[memory-bank] PB_BASE_URL/PB_ADMIN_EMAIL/PB_ADMIN_PASSWORD not set — disabled")
	}
	return &MemoryBank{client: client, maxRecs: maxRecs, enabled: enabled}
}

// IsEnabled returns true if PocketBase credentials are configured.
func (m *MemoryBank) IsEnabled() bool { return m.enabled }

// Bootstrap creates all required PocketBase collections on first run.
// Safe to call every startup — skips existing collections.
func (m *MemoryBank) Bootstrap(ctx context.Context) error {
	if !m.enabled {
		return nil
	}
	return pb.Bootstrap(ctx, m.client)
}

// ─── Write ────────────────────────────────────────────────────────────────────

// Write stores a memory fragment to PocketBase asynchronously.
// Fires-and-forgets so it never blocks a chat response.
func (m *MemoryBank) Write(frag MemoryFragment) {
	if !m.enabled {
		return
	}
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		data := map[string]any{
			"content":       frag.Content,
			"source":        frag.Source,
			"topic":         frag.Topic,
			"session_id":    frag.SessionID,
			"importance":    frag.Importance,
			"access_count":  0,
			"last_accessed": time.Now().UTC().Format(time.RFC3339),
		}
		if _, err := m.client.CreateRecord(ctx, "memories", data); err != nil {
			log.Printf("[memory-bank] write error: %v", err)
		}
	}()
}

// WriteKnowledgeFragment stores a CuriosityDaemon finding.
func (m *MemoryBank) WriteKnowledgeFragment(topic, intent, content string, importance float64) {
	if !m.enabled {
		return
	}
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		data := map[string]any{
			"topic":        topic,
			"intent":       intent,
			"content":      content,
			"importance":   importance,
			"access_count": 0,
		}
		if _, err := m.client.CreateRecord(ctx, "knowledge_fragments", data); err != nil {
			log.Printf("[memory-bank] knowledge fragment write error: %v", err)
		}
	}()
}

// ─── Query ────────────────────────────────────────────────────────────────────

// QuerySimilar fetches the topN most recent memories matching a topic keyword.
// Uses PocketBase filter (keyword contains match) — no embedding needed for MVP.
// Returns a formatted context block ready for system prompt injection.
func (m *MemoryBank) QuerySimilar(ctx context.Context, topic string, topN int) ([]MemoryFragment, error) {
	if !m.enabled {
		return nil, nil
	}

	// Sanitize topic for PocketBase filter syntax
	safe := strings.ReplaceAll(topic, `"`, `'`)
	safe = strings.ReplaceAll(safe, `\`, ``)
	if len(safe) > 100 {
		safe = safe[:100]
	}

	filter := fmt.Sprintf(`topic ~ "%s" || content ~ "%s"`, safe, safe)
	result, err := m.client.QueryRecords(ctx, "memories", filter, "-importance,-created", topN)
	if err != nil {
		return nil, err
	}

	frags := make([]MemoryFragment, 0, len(result.Items))
	for _, item := range result.Items {
		frag := MemoryFragment{
			ID:         stringField(item, "id"),
			Content:    stringField(item, "content"),
			Source:     stringField(item, "source"),
			Topic:      stringField(item, "topic"),
			SessionID:  stringField(item, "session_id"),
			Importance: floatField(item, "importance"),
			AccessCount: intField(item, "access_count"),
		}
		frags = append(frags, frag)

		// bump access count asynchronously
		id := frag.ID
		count := frag.AccessCount + 1
		go func() {
			uctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			_ = m.client.UpdateRecord(uctx, "memories", id, map[string]any{
				"access_count": count,
				"last_accessed": time.Now().UTC().Format(time.RFC3339),
			})
		}()
	}
	return frags, nil
}

// QueryKnowledgeFragments returns known topics from previous curiosity bursts.
func (m *MemoryBank) QueryKnowledgeFragments(ctx context.Context, limit int) ([]string, error) {
	if !m.enabled {
		return nil, nil
	}
	result, err := m.client.QueryRecords(ctx, "knowledge_fragments", "", "-created", limit)
	if err != nil {
		return nil, err
	}
	topics := make([]string, 0, len(result.Items))
	for _, item := range result.Items {
		if t := stringField(item, "topic"); t != "" {
			topics = append(topics, t)
		}
	}
	return topics, nil
}

// FormatRAGContext formats memory fragments as a system prompt injection block.
// Capped at maxChars to avoid bloating the context window.
func FormatRAGContext(frags []MemoryFragment, maxChars int) string {
	if len(frags) == 0 {
		return ""
	}
	var sb strings.Builder
	sb.WriteString("## Relevant Memory Context\n")
	for _, f := range frags {
		entry := fmt.Sprintf("- [%s] %s\n", f.Topic, f.Content)
		if sb.Len()+len(entry) > maxChars {
			break
		}
		sb.WriteString(entry)
	}
	return sb.String()
}

// ─── Memory Recycling ─────────────────────────────────────────────────────────

// retentionScore computes a decay-adjusted importance score.
// retention = importance × log(1 + access_count) × e^(-age_days/180)
func retentionScore(importance float64, accessCount int, created time.Time) float64 {
	ageDays := time.Since(created).Hours() / 24
	return importance * math.Log1p(float64(accessCount)) * math.Exp(-ageDays/180)
}

// Recycle prunes the bottom 10% of memories by retention score when
// the total record count exceeds PB_MEMORY_MAX_RECORDS. Runs async.
func (m *MemoryBank) Recycle() {
	if !m.enabled {
		return
	}
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
		defer cancel()

		count, err := m.client.CountRecords(ctx, "memories")
		if err != nil || count <= m.maxRecs {
			return
		}

		pruneCount := count / 10 // 10% of total
		log.Printf("[memory-bank] recycling %d low-retention memories (total=%d, max=%d)", pruneCount, count, m.maxRecs)

		// Fetch bottom-importance, oldest records
		result, err := m.client.QueryRecords(ctx, "memories", "", "importance,created", pruneCount)
		if err != nil {
			log.Printf("[memory-bank] recycle query error: %v", err)
			return
		}

		pruned := 0
		for _, item := range result.Items {
			id := stringField(item, "id")
			if id == "" {
				continue
			}
			if err := m.client.DeleteRecord(ctx, "memories", id); err != nil {
				log.Printf("[memory-bank] recycle delete %s: %v", id, err)
			} else {
				pruned++
			}
		}
		log.Printf("[memory-bank] recycled %d memories", pruned)
	}()
}

// ─── Spend Ledger ─────────────────────────────────────────────────────────────

// PersistSpend upserts the RunPod monthly spend for a given service.
// month format: "2026-03". Runs async.
func (m *MemoryBank) PersistSpend(service, month string, amount float64) {
	if !m.enabled {
		return
	}
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		filter := fmt.Sprintf(`service = "%s" && month = "%s"`, service, month)
		result, err := m.client.QueryRecords(ctx, "spend_ledger", filter, "", 1)
		if err != nil {
			log.Printf("[memory-bank] spend query error: %v", err)
			return
		}

		data := map[string]any{"service": service, "month": month, "amount": amount}
		if result.TotalItems > 0 {
			id := stringField(result.Items[0], "id")
			_ = m.client.UpdateRecord(ctx, "spend_ledger", id, data)
		} else {
			_, _ = m.client.CreateRecord(ctx, "spend_ledger", data)
		}
	}()
}

// LoadSpend fetches the stored monthly spend for a service.
// Returns 0.0 if not found. Blocks until complete — call on startup only.
func (m *MemoryBank) LoadSpend(ctx context.Context, service, month string) float64 {
	if !m.enabled {
		return 0
	}
	filter := fmt.Sprintf(`service = "%s" && month = "%s"`, service, month)
	result, err := m.client.QueryRecords(ctx, "spend_ledger", filter, "", 1)
	if err != nil || result.TotalItems == 0 {
		return 0
	}
	return floatField(result.Items[0], "amount")
}

// ─── Conversation Summary ─────────────────────────────────────────────────────

// SaveConversationSummary stores a compressed session summary for future RAG.
func (m *MemoryBank) SaveConversationSummary(sessionID, summary string, msgCount int, topics []string) {
	if !m.enabled {
		return
	}
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		data := map[string]any{
			"session_id":    sessionID,
			"summary":       summary,
			"message_count": msgCount,
			"topics":        topics,
		}
		if _, err := m.client.CreateRecord(ctx, "conversation_summaries", data); err != nil {
			log.Printf("[memory-bank] summary write error: %v", err)
		}
	}()
}

// ─── Field helpers ────────────────────────────────────────────────────────────

func stringField(m map[string]any, key string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

func floatField(m map[string]any, key string) float64 {
	if v, ok := m[key]; ok {
		switch n := v.(type) {
		case float64:
			return n
		case int:
			return float64(n)
		}
	}
	return 0
}

func intField(m map[string]any, key string) int {
	return int(floatField(m, key))
}
