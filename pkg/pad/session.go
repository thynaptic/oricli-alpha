package pad

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/google/uuid"
	pb "github.com/thynaptic/oricli-go/pkg/connectors/pocketbase"
)

const padSessionsCollection = "pad_sessions"

// SessionStatus represents the lifecycle state of a DispatchSession.
type SessionStatus string

const (
	StatusPending   SessionStatus = "pending"
	StatusRunning   SessionStatus = "running"
	StatusDone      SessionStatus = "done"
	StatusFailed    SessionStatus = "failed"
)

// DispatchSession tracks the full lifecycle of a parallel dispatch.
type DispatchSession struct {
	ID          string         `json:"id"`
	Query       string         `json:"query"`
	Strategy    Strategy       `json:"strategy"`
	Tasks       []WorkerTask   `json:"tasks"`
	Results     []WorkerResult `json:"results"`
	Synthesis   string         `json:"synthesis"`
	Status      SessionStatus  `json:"status"`
	WorkerCount int            `json:"worker_count"`
	StartedAt   time.Time      `json:"started_at"`
	CompletedAt time.Time      `json:"completed_at,omitempty"`
	DurationMS  int64          `json:"duration_ms"`
	Error       string         `json:"error,omitempty"`
}

// SessionStore persists DispatchSessions to PocketBase and caches recent ones in memory.
type SessionStore struct {
	pb    *pb.Client
	mu    sync.RWMutex
	cache []*DispatchSession // ordered newest-first, max 50 in-memory
}

// NewSessionStore creates a store. pb may be nil (memory-only mode).
func NewSessionStore(client *pb.Client) *SessionStore {
	return &SessionStore{
		pb:    client,
		cache: make([]*DispatchSession, 0, 50),
	}
}

// Bootstrap ensures the pad_sessions collection exists in PocketBase.
func (s *SessionStore) Bootstrap(ctx context.Context) error {
	if s.pb == nil {
		return nil
	}
	exists, err := s.pb.CollectionExists(ctx, padSessionsCollection)
	if err != nil || !exists {
		if createErr := s.createCollection(ctx); createErr != nil {
			return fmt.Errorf("create pad_sessions collection: %w", createErr)
		}
		log.Printf("[PAD:SessionStore] collection %q created", padSessionsCollection)
	}
	return nil
}

// Save persists a session to PB and prepends it to the in-memory cache.
func (s *SessionStore) Save(ctx context.Context, session *DispatchSession) error {
	if session.ID == "" {
		session.ID = uuid.New().String()
	}

	s.mu.Lock()
	s.cache = append([]*DispatchSession{session}, s.cache...)
	if len(s.cache) > 50 {
		s.cache = s.cache[:50]
	}
	s.mu.Unlock()

	if s.pb == nil {
		return nil
	}

	tasksJSON, _ := json.Marshal(session.Tasks)
	resultsJSON, _ := json.Marshal(session.Results)

	data := map[string]interface{}{
		"session_id":   session.ID,
		"query":        session.Query,
		"strategy":     string(session.Strategy),
		"tasks":        string(tasksJSON),
		"results":      string(resultsJSON),
		"synthesis":    session.Synthesis,
		"status":       string(session.Status),
		"worker_count": session.WorkerCount,
		"started_at":   session.StartedAt.Format(time.RFC3339),
		"completed_at": session.CompletedAt.Format(time.RFC3339),
		"duration_ms":  session.DurationMS,
		"error":        session.Error,
	}

	if _, err := s.pb.CreateRecord(ctx, padSessionsCollection, data); err != nil {
		log.Printf("[PAD:SessionStore] PB save error: %v", err)
	}
	return nil
}

// List returns up to n recent sessions from in-memory cache.
func (s *SessionStore) List(n int) []*DispatchSession {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if n <= 0 || n > len(s.cache) {
		n = len(s.cache)
	}
	out := make([]*DispatchSession, n)
	copy(out, s.cache[:n])
	return out
}

// Get finds a session by ID from the in-memory cache.
func (s *SessionStore) Get(id string) (*DispatchSession, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, sess := range s.cache {
		if sess.ID == id {
			return sess, true
		}
	}
	return nil, false
}

// ─────────────────────────────────────────────────────────────────────────────
// PocketBase schema
// ─────────────────────────────────────────────────────────────────────────────

func (s *SessionStore) createCollection(ctx context.Context) error {
	if s.pb == nil {
		return nil
	}
	schema := pb.CollectionSchema{
		Name: padSessionsCollection,
		Type: "base",
		Schema: []pb.FieldSchema{
			{Name: "session_id", Type: "text", Required: true},
			{Name: "query", Type: "text", Options: map[string]any{"maxSize": 200000}},
			{Name: "strategy", Type: "text"},
			{Name: "tasks", Type: "text", Options: map[string]any{"maxSize": 200000}},
			{Name: "results", Type: "text", Options: map[string]any{"maxSize": 2000000}},
			{Name: "synthesis", Type: "text", Options: map[string]any{"maxSize": 2000000}},
			{Name: "status", Type: "text"},
			{Name: "worker_count", Type: "number"},
			{Name: "started_at", Type: "text"},
			{Name: "completed_at", Type: "text"},
			{Name: "duration_ms", Type: "number"},
			{Name: "error", Type: "text"},
		},
	}
	return s.pb.CreateCollection(ctx, schema)
}
