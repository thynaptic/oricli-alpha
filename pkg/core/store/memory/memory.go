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
