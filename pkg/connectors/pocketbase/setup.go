package pocketbase

import (
	"context"
	"log"
)

// Bootstrap ensures all required Oricli memory collections exist on PocketBase.
// It is safe to call on every startup — already-existing collections are skipped.
func Bootstrap(ctx context.Context, c *Client) error {
	collections := []CollectionSchema{
		memoriesSchema(),
		knowledgeFragmentsSchema(),
		spendLedgerSchema(),
		conversationSummariesSchema(),
	}

	for _, schema := range collections {
		exists, err := c.CollectionExists(ctx, schema.Name)
		if err != nil {
			return err
		}
		if exists {
			log.Printf("[pb-bootstrap] collection %q already exists — skipping", schema.Name)
			continue
		}
		if err := c.CreateCollection(ctx, schema); err != nil {
			return err
		}
		log.Printf("[pb-bootstrap] created collection %q", schema.Name)
	}
	return nil
}

// ─── Collection Schemas ───────────────────────────────────────────────────────

// memoriesSchema stores conversation fragments and curiosity findings.
// Embedding stored as JSON array. importance 0.0–1.0.
func memoriesSchema() CollectionSchema {
	return CollectionSchema{
		Name: "memories",
		Type: "base",
		Schema: []FieldSchema{
			{Name: "content", Type: "text", Required: true},
			{Name: "source", Type: "text"},   // "conversation" | "curiosity" | "summary"
			{Name: "topic", Type: "text"},
			{Name: "session_id", Type: "text"},
			{Name: "importance", Type: "number"},
			{Name: "access_count", Type: "number"},
			{Name: "last_accessed", Type: "text"}, // ISO8601
			{
				Name: "embedding",
				Type: "json",
				Options: map[string]any{"maxSize": 2000000},
			},
		},
	}
}

// knowledgeFragmentsSchema stores CuriosityDaemon research results per topic.
func knowledgeFragmentsSchema() CollectionSchema {
	return CollectionSchema{
		Name: "knowledge_fragments",
		Type: "base",
		Schema: []FieldSchema{
			{Name: "topic", Type: "text", Required: true},
			{Name: "intent", Type: "text"},
			{Name: "content", Type: "text", Required: true},
			{Name: "importance", Type: "number"},
			{Name: "access_count", Type: "number"},
			{
				Name:    "embedding",
				Type:    "json",
				Options: map[string]any{"maxSize": 2000000},
			},
		},
	}
}

// spendLedgerSchema stores RunPod monthly spend per service, survives restarts.
func spendLedgerSchema() CollectionSchema {
	return CollectionSchema{
		Name: "spend_ledger",
		Type: "base",
		Schema: []FieldSchema{
			{Name: "month", Type: "text", Required: true},   // "2026-03"
			{Name: "service", Type: "text", Required: true}, // "inference" | "imagegen"
			{Name: "amount", Type: "number", Required: true},
		},
	}
}

// conversationSummariesSchema stores compressed session summaries for RAG.
func conversationSummariesSchema() CollectionSchema {
	return CollectionSchema{
		Name: "conversation_summaries",
		Type: "base",
		Schema: []FieldSchema{
			{Name: "session_id", Type: "text", Required: true},
			{Name: "summary", Type: "text", Required: true},
			{Name: "message_count", Type: "number"},
			{
				Name:    "topics",
				Type:    "json",
				Options: map[string]any{"maxSize": 200000},
			},
			{
				Name:    "embedding",
				Type:    "json",
				Options: map[string]any{"maxSize": 2000000},
			},
		},
	}
}
