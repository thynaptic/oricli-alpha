package service

import (
	"bytes"
	"context"
	"encoding/csv"
	"fmt"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/ledongthuc/pdf"
)

// DocumentIngestor ingests documents into MemoryBank and seeds CuriosityDaemon.
type DocumentIngestor struct {
	MemoryBank      *MemoryBank
	CuriosityDaemon *CuriosityDaemon

	mu   sync.RWMutex
	docs map[string]IngestedDoc
}

// IngestedDoc records metadata about a document that has been ingested.
type IngestedDoc struct {
	ID         string    `json:"id"`
	Filename   string    `json:"filename"`
	ChunkCount int       `json:"chunk_count"`
	IngestedAt time.Time `json:"ingested_at"`
	SizeBytes  int       `json:"size_bytes"`
}

// Ingest extracts text from data, chunks it, writes chunks to MemoryBank,
// and seeds CuriosityDaemon. Returns the number of chunks stored.
func (d *DocumentIngestor) Ingest(ctx context.Context, filename string, data []byte, mimeType string) (int, error) {
	text, err := d.extractText(filename, data, mimeType)
	if err != nil {
		return 0, fmt.Errorf("text extraction failed: %w", err)
	}

	chunks := chunkText(text, 400, 50)

	topic := strings.TrimSuffix(filepath.Base(filename), filepath.Ext(filename))

	for _, chunk := range chunks {
		d.MemoryBank.Write(MemoryFragment{
			Source:     "document",
			Provenance: ProvenanceSyntheticL1,
			Volatility: VolatilityStable,
			Topic:      topic,
			Content:    chunk,
			Importance: 0.75,
		})
	}

	if d.CuriosityDaemon != nil {
		seeds := extractTopics(text)
		if len(seeds) > 10 {
			seeds = seeds[:10]
		}
		for _, seed := range seeds {
			d.CuriosityDaemon.AddSeed(seed, "document")
		}
	}

	id := uuid.New().String()
	doc := IngestedDoc{
		ID:         id,
		Filename:   filename,
		ChunkCount: len(chunks),
		IngestedAt: time.Now(),
		SizeBytes:  len(data),
	}
	d.mu.Lock()
	if d.docs == nil {
		d.docs = make(map[string]IngestedDoc)
	}
	d.docs[id] = doc
	d.mu.Unlock()

	return len(chunks), nil
}

// ListDocs returns all ingested document records.
func (d *DocumentIngestor) ListDocs() []IngestedDoc {
	d.mu.RLock()
	defer d.mu.RUnlock()
	out := make([]IngestedDoc, 0, len(d.docs))
	for _, doc := range d.docs {
		out = append(out, doc)
	}
	return out
}

// extractText dispatches to the appropriate extractor based on file extension/MIME.
func (d *DocumentIngestor) extractText(filename string, data []byte, mimeType string) (string, error) {
	ext := strings.ToLower(filepath.Ext(filename))
	switch ext {
	case ".txt", ".md":
		return string(data), nil
	case ".csv":
		return extractCSV(data)
	case ".pdf":
		return extractPDF(data)
	default:
		return "", fmt.Errorf("unsupported file type: %s", ext)
	}
}

func extractCSV(data []byte) (string, error) {
	r := csv.NewReader(bytes.NewReader(data))
	records, err := r.ReadAll()
	if err != nil {
		return "", fmt.Errorf("csv parse error: %w", err)
	}

	const maxRows = 500
	var sb strings.Builder
	var headers []string
	for i, row := range records {
		if i == 0 {
			headers = row
			continue
		}
		if i > maxRows {
			break
		}
		sb.WriteString(fmt.Sprintf("Row %d: ", i))
		parts := make([]string, 0, len(row))
		for j, val := range row {
			col := fmt.Sprintf("%d", j)
			if j < len(headers) {
				col = headers[j]
			}
			parts = append(parts, fmt.Sprintf("%s=%s", col, val))
		}
		sb.WriteString(strings.Join(parts, ", "))
		sb.WriteByte('\n')
	}
	return sb.String(), nil
}

func extractPDF(data []byte) (string, error) {
	r, err := pdf.NewReader(bytes.NewReader(data), int64(len(data)))
	if err != nil {
		return "", fmt.Errorf("pdf open error: %w", err)
	}

	var sb strings.Builder
	numPages := r.NumPage()
	for i := 1; i <= numPages; i++ {
		page := r.Page(i)
		if page.V.IsNull() {
			continue
		}
		text, err := page.GetPlainText(nil)
		if err != nil {
			continue
		}
		sb.WriteString(text)
		sb.WriteByte('\n')
	}

	result := sb.String()
	if strings.TrimSpace(result) == "" {
		return "", fmt.Errorf("pdf contained no extractable text")
	}
	return result, nil
}

// chunkText splits text into chunks of ~chunkWords words with overlapWords overlap.
func chunkText(text string, chunkWords, overlapWords int) []string {
	words := strings.Fields(text)
	if len(words) == 0 {
		return nil
	}

	var chunks []string
	start := 0
	for start < len(words) {
		end := start + chunkWords
		if end > len(words) {
			end = len(words)
		}
		chunks = append(chunks, strings.Join(words[start:end], " "))
		if end == len(words) {
			break
		}
		start = end - overlapWords
		if start < 0 {
			start = 0
		}
	}
	return chunks
}
