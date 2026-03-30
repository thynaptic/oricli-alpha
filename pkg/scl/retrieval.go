package scl

import (
	"context"
	"fmt"
	"strings"
)

// RetrievalEngine wraps the Ledger and assembles a ready-to-inject context window
// for the LLM. It is the single point of RAG injection — all agents that need
// knowledge call BuildContextWindow() instead of querying MemoryBank directly.
type RetrievalEngine struct {
	ledger *Ledger
}

// NewRetrievalEngine creates a RetrievalEngine backed by the given Ledger.
func NewRetrievalEngine(l *Ledger) *RetrievalEngine {
	return &RetrievalEngine{ledger: l}
}

// RetrievalOptions controls what the engine retrieves and how it's formatted.
type RetrievalOptions struct {
	// Tiers to search. Defaults to TierPriority order if empty.
	Tiers []Tier
	// TopKPerTier is the max records to pull per tier. Default 3.
	TopKPerTier int
	// MaxTokens is the approximate character budget for the injected window.
	// The engine trims from lowest-score records first. Default 2000 chars.
	MaxTokens int
	// IncludeMetadata adds (source, confidence) annotations to each record.
	IncludeMetadata bool
}

func defaultOpts(o RetrievalOptions) RetrievalOptions {
	if o.TopKPerTier <= 0 {
		o.TopKPerTier = 3
	}
	if o.MaxTokens <= 0 {
		o.MaxTokens = 2000
	}
	if len(o.Tiers) == 0 {
		o.Tiers = TierPriority
	}
	return o
}

// BuildContextWindow retrieves relevant knowledge records for a query and
// assembles them into a formatted string ready for LLM system-prompt injection.
//
// Output format:
//
//	--- Sovereign Knowledge Context ---
//	[corrections]
//	• If the user asks about X, always respond with Y.
//	[facts]
//	• <fact 1>
//	• <fact 2>
//	[skills]
//	• <skill trace>
//	------------------------------------
func (e *RetrievalEngine) BuildContextWindow(ctx context.Context, query string, opts RetrievalOptions) string {
	if !e.ledger.IsEnabled() {
		return ""
	}
	opts = defaultOpts(opts)

	topK := opts.TopKPerTier * len(opts.Tiers)
	records, err := e.ledger.Read(ctx, query, opts.Tiers, topK)
	if err != nil || len(records) == 0 {
		return ""
	}

	// Group by tier, preserving TierPriority order.
	byTier := make(map[Tier][]SCLRecord)
	for _, r := range records {
		byTier[r.Tier] = append(byTier[r.Tier], r)
	}

	var sb strings.Builder
	sb.WriteString("--- Sovereign Knowledge Context ---\n")

	charBudget := opts.MaxTokens
	for _, tier := range opts.Tiers {
		recs, ok := byTier[tier]
		if !ok || len(recs) == 0 {
			continue
		}
		sb.WriteString(fmt.Sprintf("[%s]\n", tier))
		for i, r := range recs {
			if i >= opts.TopKPerTier {
				break
			}
			line := "• " + strings.TrimSpace(r.Content)
			if opts.IncludeMetadata {
				line += fmt.Sprintf(" (confidence: %.2f, source: %s)", r.Confidence, r.Provenance)
			}
			line += "\n"
			if charBudget-len(line) < 0 {
				goto done
			}
			sb.WriteString(line)
			charBudget -= len(line)
		}
	}
done:
	sb.WriteString("------------------------------------\n")
	result := sb.String()
	// If only the header + footer were written, return empty (nothing useful).
	if strings.Count(result, "•") == 0 {
		return ""
	}
	return result
}

// QueryRecords is a direct retrieval call for admin inspection and tests.
// Returns raw SCLRecords without building a context window.
func (e *RetrievalEngine) QueryRecords(ctx context.Context, query string, tiers []Tier, topK int) ([]SCLRecord, error) {
	return e.ledger.Read(ctx, query, tiers, topK)
}

// SearchBySubject retrieves all active records for a specific subject string
// across all tiers. Used by the admin API for "show me everything about X".
func (e *RetrievalEngine) SearchBySubject(ctx context.Context, subject string, limit int) ([]SCLRecord, error) {
	if !e.ledger.IsEnabled() {
		return nil, nil
	}
	if limit <= 0 {
		limit = 20
	}
	filter := fmt.Sprintf("subject='%s' && superseded_by=''", subject)
	result, err := e.ledger.client.QueryRecords(ctx, sclCollection, filter, "-confidence,-updated", limit)
	if err != nil {
		return nil, err
	}
	var recs []SCLRecord
	for _, item := range result.Items {
		recs = append(recs, itemToRecord(item))
	}
	return recs, nil
}

// Browse returns all active records for an admin listing (paginated).
func (e *RetrievalEngine) Browse(ctx context.Context, tier Tier, page, perPage int) ([]SCLRecord, int, error) {
	if !e.ledger.IsEnabled() {
		return nil, 0, nil
	}
	if perPage <= 0 {
		perPage = 20
	}
	filter := "superseded_by=''"
	if tier != "" {
		filter = fmt.Sprintf("tier='%s' && superseded_by=''", tier)
	}
	result, err := e.ledger.client.QueryRecords(ctx, sclCollection, filter, "-confidence,-updated", perPage)
	if err != nil {
		// Lazy bootstrap on first call.
		if bErr := e.ledger.Bootstrap(ctx); bErr == nil {
			result, err = e.ledger.client.QueryRecords(ctx, sclCollection, filter, "-confidence,-updated", perPage)
		}
		if err != nil {
			return nil, 0, err
		}
	}
	var recs []SCLRecord
	for _, item := range result.Items {
		recs = append(recs, itemToRecord(item))
	}
	return recs, result.TotalItems, nil
}
