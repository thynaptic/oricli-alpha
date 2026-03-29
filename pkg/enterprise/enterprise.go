// Package enterprise provides the ORI Studio SMB knowledge layer.
//
// It pairs with the Tenant Constitution (.ori files) to give each SMB deployment
// both behavioral rules (constitution) and company-specific knowledge (this layer).
//
// Usage:
//
//	layer, err := enterprise.New("acme-corp")
//	if err != nil { ... }
//	defer layer.Close()
//
//	// Ingest from a directory
//	layer.IndexDirectory("/path/to/company/docs", rag.DefaultIndexOptions())
//
//	// Query at inference time
//	context, err := layer.QueryKnowledge(ctx, userQuery, 5)
package enterprise

import (
	"context"
	"fmt"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/enterprise/connectors"
	"github.com/thynaptic/oricli-go/pkg/enterprise/memory"
	"github.com/thynaptic/oricli-go/pkg/enterprise/rag"
)

// Layer is the SMB enterprise knowledge layer for a single tenant namespace.
// It wraps a namespace-isolated MemoryManager with RAG indexing capabilities.
type Layer struct {
	namespace string
	mm        *memory.MemoryManager
}

// New creates an enterprise knowledge Layer scoped to the given namespace.
// Each SMB tenant should use a unique namespace (e.g., company slug).
func New(namespace string) (*Layer, error) {
	if strings.TrimSpace(namespace) == "" {
		return nil, fmt.Errorf("enterprise: namespace must not be empty")
	}
	mm, err := memory.NewMemoryManager()
	if err != nil {
		return nil, fmt.Errorf("enterprise: init memory manager: %w", err)
	}
	mm.SetActiveNamespace(namespace)
	return &Layer{namespace: namespace, mm: mm}, nil
}

// Namespace returns the active tenant namespace.
func (l *Layer) Namespace() string { return l.namespace }

// HasKnowledge returns true if the namespace has any indexed content.
func (l *Layer) HasKnowledge() bool {
	segs, err := l.mm.SnapshotKnowledgeSegments(1)
	return err == nil && len(segs) > 0
}

// QueryKnowledge retrieves the top-k most relevant knowledge segments for a query.
// Returns formatted context strings ready to inject into a system prompt.
func (l *Layer) QueryKnowledge(_ context.Context, query string, topK int) ([]string, error) {
	return l.mm.RetrieveKnowledge(query, topK)
}

// QueryKnowledgeSegments returns full KnowledgeSegment structs with metadata.
func (l *Layer) QueryKnowledgeSegments(_ context.Context, query string, topK int) ([]memory.KnowledgeSegment, error) {
	return l.mm.RetrieveKnowledgeSegments(query, topK)
}

// IndexDirectory ingests all documents under dir into this tenant's namespace.
func (l *Layer) IndexDirectory(dir string, opts rag.IndexOptions) (rag.IndexStats, error) {
	return rag.IndexDirectory(l.mm, dir, opts)
}

// IndexConnector ingests documents from a connector (Notion, GitHub, Google Drive, etc.)
// into this tenant's namespace.
func (l *Layer) IndexConnector(ctx context.Context, c connectors.Connector, fetchOpts connectors.FetchOptions) (rag.IndexStats, error) {
	return rag.IndexConnector(ctx, c, l.mm, rag.DefaultIndexOptions(), fetchOpts)
}

// Memory returns the underlying MemoryManager for advanced use.
func (l *Layer) Memory() *memory.MemoryManager { return l.mm }

// ClearKnowledge deletes all indexed knowledge documents for this namespace.
func (l *Layer) ClearKnowledge() error {
	return l.mm.ClearNamespace(l.namespace)
}

// DefaultIndexOptions exposes rag.DefaultIndexOptions at the enterprise package level.
func DefaultIndexOptions() rag.IndexOptions { return rag.DefaultIndexOptions() }

// Close is a no-op placeholder for future cleanup (e.g., flushing indexes).
func (l *Layer) Close() {}
