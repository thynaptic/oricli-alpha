package rag

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/thynaptic/ori-capsule/internal/safety"
)

const (
	DefaultMaxChunkChars   = 1200
	DefaultChunkOverlap    = 120
	DefaultTopK            = 5
	DefaultMaxContextRunes = 6000
)

// Chunk is one indexed text unit persisted under memoryDir/rag/.
type Chunk struct {
	ID        string            `json:"id"`
	Source    string            `json:"source"`
	Text      string            `json:"text"`
	Section   string            `json:"section,omitempty"`
	Metadata  map[string]string `json:"metadata,omitempty"`
	CreatedAt time.Time         `json:"created_at"`
}

// Store is a local BM25-backed RAG store (no embeds).
type Store struct {
	mu     sync.RWMutex
	dir    string
	chunks []Chunk
	index  *BM25Index
	guard  *safety.RagContentGuard
}

// Open loads (or creates) a store at memoryDir/rag/.
func Open(memoryDir string) (*Store, error) {
	dir := filepath.Join(memoryDir, "rag")
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return nil, err
	}
	s := &Store{dir: dir, index: NewBM25Index(), guard: safety.NewRagContentGuard()}
	if err := s.load(); err != nil {
		return nil, err
	}
	s.rebuildIndexLocked()
	return s, nil
}

func (s *Store) chunksPath() string { return filepath.Join(s.dir, "chunks.json") }

func (s *Store) load() error {
	path := s.chunksPath()
	b, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			s.chunks = nil
			return nil
		}
		return err
	}
	return json.Unmarshal(b, &s.chunks)
}

func (s *Store) persistLocked() error {
	b, err := json.MarshalIndent(s.chunks, "", "  ")
	if err != nil {
		return err
	}
	tmp := s.chunksPath() + ".tmp"
	if err := os.WriteFile(tmp, b, 0o600); err != nil {
		return err
	}
	return os.Rename(tmp, s.chunksPath())
}

func (s *Store) rebuildIndexLocked() {
	docs := make([]Document, 0, len(s.chunks))
	for _, c := range s.chunks {
		md := map[string]string{}
		for k, v := range c.Metadata {
			md[k] = v
		}
		md["source"] = c.Source
		if c.Section != "" {
			md["section"] = c.Section
		}
		docs = append(docs, Document{ID: c.ID, Content: c.Text, Metadata: md})
	}
	s.index.Rebuild(docs)
}

// IngestText chunks and indexes text from a named source.
func (s *Store) IngestText(source, text string, meta map[string]string) (int, error) {
	source = strings.TrimSpace(source)
	if source == "" {
		return 0, fmt.Errorf("source is required")
	}
	text = strings.TrimSpace(text)
	if text == "" {
		return 0, fmt.Errorf("text is empty")
	}
	scan := s.guard.ScanScrapedContent(text)
	text = strings.TrimSpace(scan.Sanitized)
	if text == "" {
		return 0, fmt.Errorf("text empty after rag content guard")
	}

	parts := ChunkText(text, DefaultMaxChunkChars, DefaultChunkOverlap)
	sections := InferChunkSections(parts, source)
	now := time.Now().UTC()
	added := 0

	s.mu.Lock()
	defer s.mu.Unlock()

	for i, part := range parts {
		partScan := s.guard.ScanScrapedContent(part)
		part = strings.TrimSpace(partScan.Sanitized)
		if part == "" {
			continue
		}
		id := chunkID(source, i, part)
		dup := false
		for _, existing := range s.chunks {
			if existing.ID == id {
				dup = true
				break
			}
		}
		if dup {
			continue
		}
		md := map[string]string{}
		for k, v := range meta {
			md[k] = v
		}
		md["source"] = source
		sectionTitle := ""
		if i < len(sections) {
			_, title, level, inferred := SectionMetaStrings(sections[i])
			sectionTitle = title
			md["section_id"] = sections[i].ID
			md["section"] = title
			md["section_level"] = level
			md["section_inferred"] = inferred
		}
		s.chunks = append(s.chunks, Chunk{
			ID:        id,
			Source:    source,
			Text:      part,
			Section:   sectionTitle,
			Metadata:  md,
			CreatedAt: now,
		})
		added++
	}
	if added == 0 {
		return 0, nil
	}
	if err := s.persistLocked(); err != nil {
		return 0, err
	}
	s.rebuildIndexLocked()
	return added, nil
}

// IngestFile reads a local file and ingests its contents.
func (s *Store) IngestFile(path string, meta map[string]string) (int, error) {
	path = strings.TrimSpace(path)
	if path == "" {
		return 0, fmt.Errorf("path is required")
	}
	b, err := os.ReadFile(path)
	if err != nil {
		return 0, err
	}
	source := filepath.Base(path)
	if meta == nil {
		meta = map[string]string{}
	}
	meta["path"] = path
	return s.IngestText(source, string(b), meta)
}

// Query runs BM25 retrieval.
func (s *Store) Query(query string, topK int) []Result {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.index == nil {
		return nil
	}
	if topK <= 0 {
		topK = DefaultTopK
	}
	return s.index.Search(query, topK, "")
}

// FormatContext builds a prompt-ready context block from BM25 hits.
func (s *Store) FormatContext(query string, topK, maxRunes int) string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.index == nil {
		return ""
	}
	if topK <= 0 {
		topK = DefaultTopK
	}
	hits := s.index.Search(query, topK, "")
	if len(hits) == 0 {
		return ""
	}
	if maxRunes <= 0 {
		maxRunes = DefaultMaxContextRunes
	}
	var b strings.Builder
	b.WriteString("Retrieved context (local BM25):\n")
	used := 0
	for i, h := range hits {
		text := h.Content
		if sec := h.Metadata["section"]; sec != "" {
			text = "[" + sec + "] " + text
		}
		line := fmt.Sprintf("%d. (score=%.3f source=%s) %s\n", i+1, h.Score, metaSource(h), text)
		if used+len([]rune(line)) > maxRunes {
			break
		}
		b.WriteString(line)
		used += len([]rune(line))
	}
	return strings.TrimSpace(b.String())
}

func metaSource(h Result) string {
	if h.Metadata != nil {
		if src := h.Metadata["source"]; src != "" {
			return src
		}
	}
	return h.ID
}

// Stats returns chunk count.
func (s *Store) Stats() map[string]any {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return map[string]any{
		"chunks": len(s.chunks),
		"dir":    s.dir,
		"mode":   "bm25",
	}
}

// Clear removes all chunks.
func (s *Store) Clear() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.chunks = nil
	s.rebuildIndexLocked()
	_ = os.Remove(s.chunksPath())
	return nil
}

func chunkID(source string, i int, text string) string {
	sum := sha256.Sum256([]byte(fmt.Sprintf("%s\n%d\n%s", source, i, text)))
	return hex.EncodeToString(sum[:12])
}
