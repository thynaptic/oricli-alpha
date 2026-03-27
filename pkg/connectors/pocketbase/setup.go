package pocketbase

import (
	"context"
	"fmt"
	"log"
	"os"
)

// Bootstrap ensures all required Oricli memory collections exist on PocketBase.
// It is safe to call on every startup — already-existing collections are skipped.
// Also ensures Oricli's analyst user account exists.
func Bootstrap(ctx context.Context, c *Client) error {
	collections := []CollectionSchema{
		memoriesSchema(),
		knowledgeFragmentsSchema(),
		spendLedgerSchema(),
		conversationSummariesSchema(),
		sovereignGoalsSchema(),
		canvasSharesSchema(),
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

	// Migrate existing collections to add epistemic hygiene fields if missing.
	if err := MigrateEpistemicFields(ctx, c); err != nil {
		log.Printf("[pb-bootstrap] epistemic migration warning: %v", err)
	}

	// Ensure Oricli's analyst account exists
	email := os.Getenv("PB_ORICLI_EMAIL")
	if email == "" {
		email = "oricli@thynaptic.com"
	}
	password := os.Getenv("PB_ORICLI_PASSWORD")
	if password == "" {
		password = "OricliSovereign2026!"
	}
	if err := CreateOricliUser(ctx, c, email, password); err != nil {
		log.Printf("[pb-bootstrap] Oricli user setup warning: %v", err)
	}

	return nil
}

// CreateOricliUser ensures Oricli's analyst user account exists in PocketBase.
// Idempotent — skips creation if the account already exists.
func CreateOricliUser(ctx context.Context, adminClient *Client, email, password string) error {
	// Check if user already exists via admin API
	result, err := adminClient.QueryRecords(ctx, "users",
		fmt.Sprintf(`email = "%s"`, email), "", 1)
	if err != nil {
		return fmt.Errorf("checking for existing oricli user: %w", err)
	}
	if result.TotalItems > 0 {
		log.Printf("[pb-bootstrap] Oricli analyst account already exists — skipping")
		return nil
	}

	// Create the user account via admin (bypasses email verification)
	userData := map[string]any{
		"email":           email,
		"emailVisibility": false,
		"password":        password,
		"passwordConfirm": password,
		"username":        "oricli",
		"name":            "Oricli",
		"role":            "analyst",
		"verified":        true,
	}
	_, err = adminClient.CreateRecord(ctx, "users", userData)
	if err != nil {
		return fmt.Errorf("creating oricli user: %w", err)
	}
	log.Printf("[pb-bootstrap] Created Oricli analyst account: %s", email)
	return nil
}

// OricliUserEnabled returns true if PB_ORICLI_EMAIL/PASSWORD are configured,
// or uses the default credentials if env vars are absent.
func OricliUserEmail() string {
	if v := os.Getenv("PB_ORICLI_EMAIL"); v != "" {
		return v
	}
	return "oricli@thynaptic.com"
}

func OricliUserPassword() string {
	if v := os.Getenv("PB_ORICLI_PASSWORD"); v != "" {
		return v
	}
	return "OricliSovereign2026!"
}

// ─── Collection Schemas ───────────────────────────────────────────────────────

// memoriesSchema stores conversation fragments and curiosity findings.
// author: "oricli" for her own thoughts/findings, "user" for conversation-derived.
// Epistemic hygiene fields:
//   provenance     — origin quality: user_stated|web_verified|synthetic_l1|synthetic_l2+|conversation
//   topic_volatility — decay class: stable|current|ephemeral
//   lineage_depth  — how many synthetic hops from ground truth (0=direct, 1=curiosity, 2+=derived)
func memoriesSchema() CollectionSchema {
	return CollectionSchema{
		Name: "memories",
		Type: "base",
		Schema: []FieldSchema{
			{Name: "content", Type: "text", Required: true},
			{Name: "source", Type: "text"},
			{Name: "author", Type: "text"},
			{Name: "topic", Type: "text"},
			{Name: "session_id", Type: "text"},
			{Name: "importance", Type: "number"},
			{Name: "access_count", Type: "number"},
			{Name: "last_accessed", Type: "text"},
			{Name: "provenance", Type: "text"},       // epistemic hygiene
			{Name: "topic_volatility", Type: "text"}, // stable|current|ephemeral
			{Name: "lineage_depth", Type: "number"},  // 0=ground truth, 1=synthetic_l1, ...
			{
				Name:    "embedding",
				Type:    "json",
				Options: map[string]any{"maxSize": 2000000},
			},
		},
	}
}

// knowledgeFragmentsSchema stores CuriosityDaemon research results per topic.
// Always authored by Oricli — these are her own epistemic findings.
func knowledgeFragmentsSchema() CollectionSchema {
	return CollectionSchema{
		Name: "knowledge_fragments",
		Type: "base",
		Schema: []FieldSchema{
			{Name: "topic", Type: "text", Required: true},
			{Name: "intent", Type: "text"},
			{Name: "content", Type: "text", Required: true},
			{Name: "author", Type: "text"},
			{Name: "importance", Type: "number"},
			{Name: "access_count", Type: "number"},
			{Name: "provenance", Type: "text"},       // always "synthetic_l1" for curiosity
			{Name: "topic_volatility", Type: "text"},
			{Name: "lineage_depth", Type: "number"},
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

// sovereignGoalsSchema stores the GoalService DAG objectives with full lifecycle fields.
func sovereignGoalsSchema() CollectionSchema {
	return CollectionSchema{
		Name: "sovereign_goals",
		Type: "base",
		Schema: []FieldSchema{
			{Name: "goal_id", Type: "text", Required: true, Options: map[string]any{"maxSize": 50}},
			{Name: "goal", Type: "text", Required: true, Options: map[string]any{"maxSize": 2000}},
			{Name: "priority", Type: "number"},
			{Name: "status", Type: "text", Required: true, Options: map[string]any{"maxSize": 20}},
			{
				Name:    "depends_on",
				Type:    "json",
				Options: map[string]any{"maxSize": 5000},
			},
			{Name: "retry_count", Type: "number"},
			{Name: "progress", Type: "number"},
			{
				Name:    "metadata",
				Type:    "json",
				Options: map[string]any{"maxSize": 10000},
			},
		},
	}
}

// epistemicFields are the three hygiene fields added to memories + knowledge_fragments.
var epistemicFields = []FieldSchema{
{Name: "provenance", Type: "text"},
{Name: "topic_volatility", Type: "text"},
{Name: "lineage_depth", Type: "number"},
}

// MigrateEpistemicFields patches existing memories and knowledge_fragments collections
// to add provenance, topic_volatility, and lineage_depth fields if they are missing.
// Safe to call on every startup — PatchCollectionSchema is idempotent.
func MigrateEpistemicFields(ctx context.Context, c *Client) error {
for _, coll := range []string{"memories", "knowledge_fragments"} {
exists, err := c.CollectionExists(ctx, coll)
if err != nil || !exists {
continue
}
if err := c.PatchCollectionSchema(ctx, coll, epistemicFields); err != nil {
log.Printf("[pb-migrate] %s: patch warning: %v", coll, err)
} else {
log.Printf("[pb-migrate] %s: epistemic fields OK", coll)
}
}
return nil
}

// canvasSharesSchema stores shared canvas documents accessible via public URL.
func canvasSharesSchema() CollectionSchema {
return CollectionSchema{
Name: "canvas_shares",
Type: "base",
Schema: []FieldSchema{
{Name: "share_id",  Type: "text", Required: true},
{Name: "title",     Type: "text"},
{Name: "doc_type",  Type: "text", Required: true},
{Name: "content",   Type: "text", Required: true, Options: map[string]any{"max": 2000000}},
{Name: "language",  Type: "text"},
},
}
}
