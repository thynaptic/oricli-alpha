package api

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/enterprise/rag"
)

// SpaceRecord is the metadata for a single project space.
type SpaceRecord struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Description string    `json:"description"`
	CreatedAt   time.Time `json:"created_at"`
	DocCount    int       `json:"doc_count"`
}

// SpacesStore is a thread-safe, JSON-backed store for SpaceRecord entries.
type SpacesStore struct {
	mu       sync.RWMutex
	filePath string
	records  []SpaceRecord
}

// NewSpacesStore loads (or creates) the JSON file at filePath.
func NewSpacesStore(filePath string) *SpacesStore {
	s := &SpacesStore{filePath: filePath}
	if err := s.load(); err != nil {
		log.Printf("[SpacesStore] init (will start empty): %v", err)
	}
	return s
}

func (s *SpacesStore) load() error {
	data, err := os.ReadFile(s.filePath)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	return json.Unmarshal(data, &s.records)
}

func (s *SpacesStore) save() error {
	if err := os.MkdirAll(filepath.Dir(s.filePath), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(s.records, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(s.filePath, data, 0o644)
}

// List returns a shallow copy of all records.
func (s *SpacesStore) List() []SpaceRecord {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]SpaceRecord, len(s.records))
	copy(out, s.records)
	return out
}

// Create adds a new SpaceRecord and persists it.
func (s *SpacesStore) Create(name, description string) SpaceRecord {
	s.mu.Lock()
	defer s.mu.Unlock()
	rec := SpaceRecord{
		ID:          fmt.Sprintf("sp_%d", time.Now().UnixNano()),
		Name:        name,
		Description: description,
		CreatedAt:   time.Now().UTC(),
	}
	s.records = append(s.records, rec)
	if err := s.save(); err != nil {
		log.Printf("[SpacesStore] save error: %v", err)
	}
	return rec
}

// Get returns the record with the given id, or false if not found.
func (s *SpacesStore) Get(id string) (SpaceRecord, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, r := range s.records {
		if r.ID == id {
			return r, true
		}
	}
	return SpaceRecord{}, false
}

// Delete removes the record with the given id and persists.
func (s *SpacesStore) Delete(id string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	for i, r := range s.records {
		if r.ID == id {
			s.records = append(s.records[:i], s.records[i+1:]...)
			if err := s.save(); err != nil {
				log.Printf("[SpacesStore] save error: %v", err)
			}
			return true
		}
	}
	return false
}

// IncrDocCount increments DocCount for the given id and persists.
func (s *SpacesStore) IncrDocCount(id string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	for i := range s.records {
		if s.records[i].ID == id {
			s.records[i].DocCount++
			if err := s.save(); err != nil {
				log.Printf("[SpacesStore] save error: %v", err)
			}
			return
		}
	}
}

// ── HTTP handlers ────────────────────────────────────────────────────────────

// GET /v1/spaces
func (s *ServerV2) handleListSpaces(c *gin.Context) {
	c.JSON(http.StatusOK, s.spacesStore.List())
}

// POST /v1/spaces
func (s *ServerV2) handleCreateSpace(c *gin.Context) {
	var body struct {
		Name        string `json:"name"`
		Description string `json:"description"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.Name == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "name is required"})
		return
	}
	rec := s.spacesStore.Create(body.Name, body.Description)
	c.JSON(http.StatusCreated, rec)
}

// DELETE /v1/spaces/:id
func (s *ServerV2) handleDeleteSpace(c *gin.Context) {
	id := c.Param("id")
	if !s.spacesStore.Delete(id) {
		c.JSON(http.StatusNotFound, gin.H{"error": "space not found"})
		return
	}
	// Clear the enterprise layer knowledge for this space.
	if layer, err := s.resolveEnterpriseLayer(id); err == nil {
		if clearErr := layer.ClearKnowledge(); clearErr != nil {
			log.Printf("[Spaces] clear knowledge for %s: %v", id, clearErr)
		}
		s.entLayers.Delete(id)
	}
	c.JSON(http.StatusOK, gin.H{"deleted": true})
}

// POST /v1/spaces/:id/documents
func (s *ServerV2) handleSpaceDocumentUpload(c *gin.Context) {
	id := c.Param("id")
	if _, ok := s.spacesStore.Get(id); !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "space not found"})
		return
	}

	fh, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "file field required"})
		return
	}

	dir := filepath.Join("data", "spaces", id)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "could not create space directory"})
		return
	}

	dst := filepath.Join(dir, filepath.Base(fh.Filename))
	src, err := fh.Open()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "could not open upload"})
		return
	}
	defer src.Close()

	out, err := os.Create(dst)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "could not save file"})
		return
	}
	defer out.Close()
	if _, err := io.Copy(out, src); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "could not write file"})
		return
	}

	s.spacesStore.IncrDocCount(id)

	// Index asynchronously so the request returns immediately.
	go func() {
		layer, lerr := s.resolveEnterpriseLayer(id)
		if lerr != nil {
			log.Printf("[Spaces] resolve layer for %s: %v", id, lerr)
			return
		}
		stats, ierr := layer.IndexDirectory(dir, rag.DefaultIndexOptions())
		if ierr != nil {
			log.Printf("[Spaces] index error for space %s: %v", id, ierr)
			return
		}
		log.Printf("[Spaces] indexed space %s: %+v", id, stats)
	}()

	c.JSON(http.StatusOK, gin.H{
		"success":  true,
		"filename": fh.Filename,
		"space_id": id,
	})
}

// GET /v1/spaces/:id/documents
func (s *ServerV2) handleListSpaceDocuments(c *gin.Context) {
	id := c.Param("id")
	if _, ok := s.spacesStore.Get(id); !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "space not found"})
		return
	}

	dir := filepath.Join("data", "spaces", id)
	entries, err := os.ReadDir(dir)
	if os.IsNotExist(err) {
		c.JSON(http.StatusOK, gin.H{"files": []string{}})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "could not list documents"})
		return
	}

	type fileInfo struct {
		Name string `json:"name"`
		Size int64  `json:"size"`
	}
	files := make([]fileInfo, 0, len(entries))
	for _, e := range entries {
		if !e.IsDir() {
			info, err := e.Info()
			size := int64(0)
			if err == nil {
				size = info.Size()
			}
			files = append(files, fileInfo{Name: e.Name(), Size: size})
		}
	}
	c.JSON(http.StatusOK, gin.H{"files": files})
}
