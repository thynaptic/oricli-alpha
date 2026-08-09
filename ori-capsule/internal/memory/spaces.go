package memory

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// Space is a named consumer project container (local files only).
type Space struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	CreatedAt time.Time `json:"created_at"`
}

// SpacesStore is a minimal local registry — no enterprise RAG layer.
type SpacesStore struct {
	mu    sync.RWMutex
	path  string
	items map[string]Space
}

func NewSpacesStore(dir string) (*SpacesStore, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	s := &SpacesStore{
		path:  filepath.Join(dir, "spaces.json"),
		items: make(map[string]Space),
	}
	_ = s.load()
	return s, nil
}

func (s *SpacesStore) List() []Space {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]Space, 0, len(s.items))
	for _, v := range s.items {
		out = append(out, v)
	}
	return out
}

func (s *SpacesStore) Upsert(id, name string) Space {
	s.mu.Lock()
	defer s.mu.Unlock()
	sp, ok := s.items[id]
	if !ok {
		sp = Space{ID: id, Name: name, CreatedAt: time.Now().UTC()}
	} else if name != "" {
		sp.Name = name
	}
	s.items[id] = sp
	_ = s.saveLocked()
	return sp
}

func (s *SpacesStore) Get(id string) (Space, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	sp, ok := s.items[id]
	return sp, ok
}

func (s *SpacesStore) load() error {
	data, err := os.ReadFile(s.path)
	if err != nil {
		return err
	}
	return json.Unmarshal(data, &s.items)
}

func (s *SpacesStore) saveLocked() error {
	data, err := json.MarshalIndent(s.items, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(s.path, data, 0o600)
}
