package memory

import (
"context"
"fmt"
"sync"
"time"

"github.com/thynaptic/oricli-go/pkg/core/model"
"github.com/thynaptic/oricli-go/pkg/core/store"
)

type MemoryStore struct {
store.Store

mu   sync.RWMutex
keys map[string][]model.APIKeyRecord // prefix -> records
}

func New() *MemoryStore {
return &MemoryStore{
keys: make(map[string][]model.APIKeyRecord),
}
}

func (s *MemoryStore) Health(ctx context.Context) error { return nil }
func (s *MemoryStore) Close() error                     { return nil }

func (s *MemoryStore) CreateTenant(ctx context.Context, name string) (model.Tenant, error) {
return model.Tenant{ID: "local", Name: name, Status: "active", CreatedAt: time.Now()}, nil
}

func (s *MemoryStore) CreateAPIKey(ctx context.Context, rec model.APIKeyRecord) (model.APIKeyRecord, error) {
if rec.ID == "" {
rec.ID = fmt.Sprintf("key-%d", time.Now().UnixNano())
}
rec.CreatedAt = time.Now()

s.mu.Lock()
defer s.mu.Unlock()
s.keys[rec.Prefix] = append(s.keys[rec.Prefix], rec)
return rec, nil
}

func (s *MemoryStore) GetAPIKeysByPrefix(ctx context.Context, prefix string) ([]model.APIKeyRecord, error) {
s.mu.RLock()
defer s.mu.RUnlock()
recs, ok := s.keys[prefix]
if !ok {
return nil, nil
}
out := make([]model.APIKeyRecord, len(recs))
copy(out, recs)
return out, nil
}

// Stub implementations for methods not needed by the in-memory store.
// These satisfy the store.Store interface without hitting the nil embedded field.
func (s *MemoryStore) ListTenants(_ context.Context, _ int) ([]model.Tenant, error) {
return []model.Tenant{{ID: "default", Name: "default", Status: "active"}}, nil
}
func (s *MemoryStore) CreateRole(_ context.Context, role model.Role) (model.Role, error) { return role, nil }
func (s *MemoryStore) UpsertModelPolicy(_ context.Context, p model.ModelPolicy) (model.ModelPolicy, error) { return p, nil }
func (s *MemoryStore) GetModelPolicy(_ context.Context, _ string) (model.ModelPolicy, error) { return model.ModelPolicy{}, fmt.Errorf("not found") }
func (s *MemoryStore) UpsertCognitivePolicy(_ context.Context, p model.CognitivePolicy) (model.CognitivePolicy, error) { return p, nil }
func (s *MemoryStore) GetCognitivePolicy(_ context.Context, _ string) (model.CognitivePolicy, error) { return model.CognitivePolicy{}, fmt.Errorf("not found") }
func (s *MemoryStore) UpsertQuota(_ context.Context, q model.Quota) (model.Quota, error) { return q, nil }
func (s *MemoryStore) GetQuota(_ context.Context, _ string) (model.Quota, error) { return model.Quota{}, fmt.Errorf("not found") }
func (s *MemoryStore) CreateIdempotencyRecord(_ context.Context, rec model.IdempotencyRecord) (model.IdempotencyRecord, error) { return rec, nil }
func (s *MemoryStore) GetIdempotencyRecord(_ context.Context, _, _ string) (model.IdempotencyRecord, error) { return model.IdempotencyRecord{}, fmt.Errorf("not found") }
func (s *MemoryStore) CreateAuditEvent(_ context.Context, ev model.AuditEvent) (model.AuditEvent, error) { return ev, nil }
func (s *MemoryStore) ListAuditEvents(_ context.Context, _ string, _ int) ([]model.AuditEvent, error) { return nil, nil }
func (s *MemoryStore) UpsertMemoryNode(_ context.Context, n model.MemoryNode) (model.MemoryNode, error) { return n, nil }
func (s *MemoryStore) ListMemoryNodes(_ context.Context, _, _ string, _ int) ([]model.MemoryNode, error) { return nil, nil }
func (s *MemoryStore) CleanupExpired(_ context.Context, _ time.Time) error { return nil }
