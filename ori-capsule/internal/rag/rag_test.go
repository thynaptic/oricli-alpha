package rag_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/thynaptic/ori-capsule/internal/rag"
)

func TestChunkTextAndSections(t *testing.T) {
	parts := rag.ChunkText("# Intro\nhello world\n\n# Details\nmore text about widgets", 40, 5)
	if len(parts) == 0 {
		t.Fatal("expected chunks")
	}
	secs := rag.InferChunkSections(parts, "doc.md")
	if len(secs) != len(parts) {
		t.Fatalf("section count %d != chunks %d", len(secs), len(parts))
	}
	if secs[0].Title == "" {
		t.Fatal("expected section title")
	}
}

func TestBM25Search(t *testing.T) {
	idx := rag.NewBM25Index()
	idx.Rebuild([]rag.Document{
		{ID: "1", Content: "cats love tuna fish", Metadata: map[string]string{"source": "a"}},
		{ID: "2", Content: "dogs chase frisbees in the park", Metadata: map[string]string{"source": "b"}},
		{ID: "3", Content: "tuna recipes for dinner", Metadata: map[string]string{"source": "c"}},
	})
	hits := idx.Search("tuna fish", 2, "")
	if len(hits) == 0 {
		t.Fatal("expected hits")
	}
	if hits[0].ID != "1" && hits[0].ID != "3" {
		t.Fatalf("unexpected top hit %s", hits[0].ID)
	}
}

func TestStoreIngestQuery(t *testing.T) {
	dir := t.TempDir()
	store, err := rag.Open(dir)
	if err != nil {
		t.Fatal(err)
	}
	n, err := store.IngestText("guide.md", "# Setup\nBM25 retrieval uses keyword ranking.\n\n# Usage\nCall ingest then query.", nil)
	if err != nil {
		t.Fatal(err)
	}
	if n == 0 {
		t.Fatal("expected added chunks")
	}
	hits := store.Query("keyword ranking BM25", 3)
	if len(hits) == 0 {
		t.Fatal("expected query hits")
	}
	ctx := store.FormatContext("BM25 retrieval", 3, 2000)
	if !strings.Contains(ctx, "BM25") && !strings.Contains(strings.ToLower(ctx), "keyword") {
		t.Fatalf("unexpected context: %q", ctx)
	}
	store2, err := rag.Open(dir)
	if err != nil {
		t.Fatal(err)
	}
	if store2.Stats()["chunks"].(int) == 0 {
		t.Fatal("expected persisted chunks")
	}
}

func TestIngestFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "note.txt")
	if err := os.WriteFile(path, []byte("ori-capsule local rag without embeddings"), 0o600); err != nil {
		t.Fatal(err)
	}
	store, err := rag.Open(filepath.Join(dir, "mem"))
	if err != nil {
		t.Fatal(err)
	}
	n, err := store.IngestFile(path, nil)
	if err != nil || n != 1 {
		t.Fatalf("ingest file: n=%d err=%v", n, err)
	}
}

func TestValidateFetchURL(t *testing.T) {
	if err := rag.ValidateFetchURL("https://example.com/doc"); err != nil {
		t.Fatal(err)
	}
	if err := rag.ValidateFetchURL("http://127.0.0.1/x"); err == nil {
		t.Fatal("expected localhost block")
	}
	if err := rag.ValidateFetchURL("ftp://example.com"); err == nil {
		t.Fatal("expected scheme block")
	}
}
