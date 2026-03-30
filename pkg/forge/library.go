package forge

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sort"
	"strings"
	"sync"
	"time"

	pb "github.com/thynaptic/oricli-go/pkg/connectors/pocketbase"
)

const (
	jitToolsCollection = "jit_tools"
	DefaultMaxTools    = 50
)

// JITTool is a fully verified, stored tool in the library.
type JITTool struct {
	// PocketBase record ID
	ID string `json:"id,omitempty"`

	Name          string                 `json:"name"`
	Description   string                 `json:"description"`
	Source        string                 `json:"source"`        // bash script
	Parameters    map[string]interface{} `json:"parameters"`    // JSON Schema
	Justification string                 `json:"justification"` // serialized JustificationRequest
	GeneratedAt   time.Time              `json:"generated_at"`
	LastUsedAt    time.Time              `json:"last_used_at"`
	UseCount      int                    `json:"use_count"`
	Verified      bool                   `json:"verified"`
	ModelUsed     string                 `json:"model_used"`
}

// ToolLibrary is a PocketBase-backed store of JIT tools with a hard cap.
// On overflow the least-recently-used tool is evicted.
type ToolLibrary struct {
	pb       *pb.Client
	maxTools int

	mu    sync.RWMutex
	cache map[string]*JITTool // name → tool (in-memory mirror)
}

// NewToolLibrary creates a library backed by the given PB client.
// maxTools ≤ 0 uses DefaultMaxTools.
func NewToolLibrary(client *pb.Client, maxTools int) *ToolLibrary {
	if maxTools <= 0 {
		maxTools = DefaultMaxTools
	}
	return &ToolLibrary{
		pb:       client,
		maxTools: maxTools,
		cache:    make(map[string]*JITTool),
	}
}

// Bootstrap ensures the jit_tools PB collection exists and loads all stored
// tools into the in-memory cache.
func (l *ToolLibrary) Bootstrap(ctx context.Context) error {
	if l.pb == nil {
		return nil
	}
	exists, err := l.pb.CollectionExists(ctx, jitToolsCollection)
	if err != nil || !exists {
		if createErr := l.createCollection(ctx); createErr != nil {
			return fmt.Errorf("create jit_tools collection: %w", createErr)
		}
		log.Printf("[ToolLibrary] collection %q created", jitToolsCollection)
	}

	// Load all stored tools into cache.
	resp, err := l.pb.QueryRecords(ctx, jitToolsCollection, "", "-use_count", DefaultMaxTools)
	if err != nil {
		log.Printf("[ToolLibrary] load error: %v — starting empty", err)
		return nil
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	for _, rec := range resp.Items {
		tool := recordToTool(rec)
		if tool != nil {
			l.cache[tool.Name] = tool
		}
	}
	log.Printf("[ToolLibrary] loaded %d stored tools", len(l.cache))
	return nil
}

// Store saves a verified tool to PB and the in-memory cache.
// If the library is at capacity, the LRU tool is evicted first.
func (l *ToolLibrary) Store(ctx context.Context, tool JITTool) error {
	if tool.Name == "" {
		return fmt.Errorf("tool name required")
	}
	tool.GeneratedAt = time.Now().UTC()
	tool.LastUsedAt = tool.GeneratedAt
	tool.Verified = true

	// Evict if at cap.
	if err := l.evictIfNeeded(ctx); err != nil {
		log.Printf("[ToolLibrary] evict warning: %v", err)
	}

	// Serialize justification if missing.
	justBytes, _ := json.Marshal(tool.Justification)
	paramsBytes, _ := json.Marshal(tool.Parameters)

	data := map[string]interface{}{
		"name":          tool.Name,
		"description":   tool.Description,
		"source":        tool.Source,
		"parameters":    string(paramsBytes),
		"justification": string(justBytes),
		"generated_at":  tool.GeneratedAt.Format(time.RFC3339),
		"last_used_at":  tool.LastUsedAt.Format(time.RFC3339),
		"use_count":     0,
		"verified":      true,
		"model_used":    tool.ModelUsed,
	}

	if l.pb != nil {
		id, err := l.pb.CreateRecord(ctx, jitToolsCollection, data)
		if err != nil {
			return fmt.Errorf("PB store: %w", err)
		}
		tool.ID = id
	}

	l.mu.Lock()
	l.cache[tool.Name] = &tool
	l.mu.Unlock()

	log.Printf("[ToolLibrary] stored tool %q (library: %d/%d)", tool.Name, len(l.cache), l.maxTools)
	return nil
}

// Load retrieves a tool by name from the cache.
func (l *ToolLibrary) Load(name string) (*JITTool, bool) {
	l.mu.RLock()
	defer l.mu.RUnlock()
	t, ok := l.cache[name]
	return t, ok
}

// All returns a snapshot of all tools sorted by use_count descending.
func (l *ToolLibrary) All() []JITTool {
	l.mu.RLock()
	defer l.mu.RUnlock()
	tools := make([]JITTool, 0, len(l.cache))
	for _, t := range l.cache {
		tools = append(tools, *t)
	}
	sort.Slice(tools, func(i, j int) bool {
		return tools[i].UseCount > tools[j].UseCount
	})
	return tools
}

// Delete removes a tool from PB and the cache.
func (l *ToolLibrary) Delete(ctx context.Context, name string) error {
	l.mu.Lock()
	t, ok := l.cache[name]
	if ok {
		delete(l.cache, name)
	}
	l.mu.Unlock()

	if ok && t.ID != "" && l.pb != nil {
		if err := l.pb.DeleteRecord(ctx, jitToolsCollection, t.ID); err != nil {
			return fmt.Errorf("PB delete: %w", err)
		}
	}
	return nil
}

// BumpUseCount increments the use_count for a tool and updates last_used_at.
func (l *ToolLibrary) BumpUseCount(ctx context.Context, name string) {
	l.mu.Lock()
	t, ok := l.cache[name]
	if !ok {
		l.mu.Unlock()
		return
	}
	t.UseCount++
	t.LastUsedAt = time.Now().UTC()
	id := t.ID
	count := t.UseCount
	l.mu.Unlock()

	if id != "" && l.pb != nil {
		_ = l.pb.UpdateRecord(ctx, jitToolsCollection, id, map[string]interface{}{
			"use_count":    count,
			"last_used_at": time.Now().UTC().Format(time.RFC3339),
		})
	}
}

// Size returns the current number of stored tools.
func (l *ToolLibrary) Size() int {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return len(l.cache)
}

// evictIfNeeded removes the least-recently-used tool if at cap.
func (l *ToolLibrary) evictIfNeeded(ctx context.Context) error {
	l.mu.RLock()
	size := len(l.cache)
	l.mu.RUnlock()

	if size < l.maxTools {
		return nil
	}

	// Find LRU: least LastUsedAt, breaking ties by lowest UseCount.
	l.mu.RLock()
	var lruName string
	var lruTime time.Time
	for name, t := range l.cache {
		if lruName == "" || t.LastUsedAt.Before(lruTime) ||
			(t.LastUsedAt.Equal(lruTime) && t.UseCount < l.cache[lruName].UseCount) {
			lruName = name
			lruTime = t.LastUsedAt
		}
	}
	l.mu.RUnlock()

	if lruName == "" {
		return nil
	}

	log.Printf("[ToolLibrary] evicting LRU tool %q (last used: %s)", lruName, lruTime.Format(time.RFC3339))
	return l.Delete(ctx, lruName)
}

// ─── PocketBase helpers ───────────────────────────────────────────────────────

func (l *ToolLibrary) createCollection(ctx context.Context) error {
	if l.pb == nil {
		return nil
	}
	schema := pb.CollectionSchema{
		Name: jitToolsCollection,
		Type: "base",
		Schema: []pb.FieldSchema{
			{Name: "name", Type: "text", Required: true},
			{Name: "description", Type: "text"},
			{Name: "source", Type: "text", Options: map[string]any{"maxSize": 2000000}},
			{Name: "parameters", Type: "text", Options: map[string]any{"maxSize": 200000}},
			{Name: "justification", Type: "text", Options: map[string]any{"maxSize": 200000}},
			{Name: "generated_at", Type: "text"},
			{Name: "last_used_at", Type: "text"},
			{Name: "use_count", Type: "number"},
			{Name: "verified", Type: "bool"},
			{Name: "model_used", Type: "text"},
		},
	}
	return l.pb.CreateCollection(ctx, schema)
}

func recordToTool(rec map[string]interface{}) *JITTool {
	name, _ := rec["name"].(string)
	if name == "" {
		return nil
	}
	t := &JITTool{
		ID:          stringField(rec, "id"),
		Name:        name,
		Description: stringField(rec, "description"),
		Source:      stringField(rec, "source"),
		ModelUsed:   stringField(rec, "model_used"),
		Verified:    boolField(rec, "verified"),
		UseCount:    intField(rec, "use_count"),
	}

	// Parse parameters JSON.
	if p := stringField(rec, "parameters"); p != "" {
		var params map[string]interface{}
		if err := json.Unmarshal([]byte(p), &params); err == nil {
			t.Parameters = params
		}
	}

	// Parse timestamps.
	if s := stringField(rec, "generated_at"); s != "" {
		t.GeneratedAt, _ = time.Parse(time.RFC3339, s)
	}
	if s := stringField(rec, "last_used_at"); s != "" {
		t.LastUsedAt, _ = time.Parse(time.RFC3339, s)
	}
	t.Justification = stringField(rec, "justification")
	return t
}

func stringField(m map[string]interface{}, k string) string {
	v, _ := m[k].(string)
	return strings.TrimSpace(v)
}

func boolField(m map[string]interface{}, k string) bool {
	v, _ := m[k].(bool)
	return v
}

func intField(m map[string]interface{}, k string) int {
	switch v := m[k].(type) {
	case float64:
		return int(v)
	case int:
		return v
	}
	return 0
}
