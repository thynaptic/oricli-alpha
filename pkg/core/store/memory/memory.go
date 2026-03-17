package memory

import (
	"context"
	"github.com/thynaptic/oricli-go/pkg/core/model"
	"github.com/thynaptic/oricli-go/pkg/core/store"
)

type MemoryStore struct{
    store.Store
}

func New() *MemoryStore {
	return &MemoryStore{}
}

func (s *MemoryStore) Health(ctx context.Context) error { return nil }
func (s *MemoryStore) Close() error { return nil }

func (s *MemoryStore) CreateTenant(ctx context.Context, name string) (model.Tenant, error) {
	return model.Tenant{ID: "local", Name: name}, nil
}

func (s *MemoryStore) GetAPIKeysByPrefix(ctx context.Context, prefix string) ([]model.APIKeyRecord, error) {
    return []model.APIKeyRecord{{ID: "test", Prefix: "test_", TenantID: "local"}}, nil
}
