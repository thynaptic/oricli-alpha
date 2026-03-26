package service

import (
	"context"
	"fmt"
	"log"
	"math"
	"os"
	"strconv"
	"strings"
	"time"

	pb "github.com/thynaptic/oricli-go/pkg/connectors/pocketbase"
)

// MemoryBank bridges Oricli's runtime to PocketBase long-term storage.
//
// Architecture:
//   Hot  → chromem-go     (in-process vectors, session-scope)
//   Warm → LMDB           (fast KV, cross-session, local)
//   Cold → PocketBase     (durable, 200GB, long-term recall)
//
// Two PocketBase identities:
//   adminClient  — collection management + conversation/system writes
//   oricliClient — Oricli's analyst account; owns her curiosity findings
//                  and internal thoughts (visible as "oricli" in PB admin UI)
type MemoryBank struct {
	adminClient  *pb.Client
	oricliClient *pb.Client
	embedder     *Embedder
	maxRecs      int
	enabled      bool
}

// ─── Epistemic Hygiene Types ──────────────────────────────────────────────────

// Provenance describes the origin quality of a memory. Higher trust = more RAG weight.
type Provenance string

const (
	ProvenanceUserStated   Provenance = "user_stated"   // user explicitly stated this fact (anchor — never recycled)
	ProvenanceWebVerified  Provenance = "web_verified"  // retrieved directly from a live URL with timestamp
	ProvenanceConversation Provenance = "conversation"  // inferred from chat exchange
	ProvenanceSyntheticL1  Provenance = "synthetic_l1"  // curiosity: summarised from web results
	ProvenanceSyntheticL2  Provenance = "synthetic_l2+" // derived from another synthetic memory
	ProvenanceContrastive  Provenance = "contrastive"   // ACCEPTED/REJECTED pair from emoji/correction feedback
	ProvenanceSolved       Provenance = "solved"         // verified good response — used by CBR to adapt past solutions
	ProvenanceGold         Provenance = "gold"           // 📌-bookmarked: highest trust, never recycled, DreamDaemon priority
)

// RAG weight multiplier per provenance level.
// user_stated anchors always bypass normal ranking and inject first.
var provenanceWeight = map[Provenance]float32{
	ProvenanceUserStated:   1.5,
	ProvenanceSolved:       1.4,
	ProvenanceGold:         1.6,
	ProvenanceContrastive:  1.3,
	ProvenanceWebVerified:  1.2,
	ProvenanceConversation: 0.9,
	ProvenanceSyntheticL1:  0.85,
	ProvenanceSyntheticL2:  0.6,
}

// Volatility controls the decay half-life used in Recycle().
type Volatility string

const (
	VolatilityStable    Volatility = "stable"    // 180-day half-life  — science, fundamentals
	VolatilityCurrent   Volatility = "current"   // 30-day half-life   — tech, AI, software
	VolatilityEphemeral Volatility = "ephemeral" // 7-day half-life    — prices, news, events
)

// halfLifeDays returns the decay half-life in days for a volatility class.
func (v Volatility) halfLifeDays() float64 {
	switch v {
	case VolatilityEphemeral:
		return 7
	case VolatilityCurrent:
		return 30
	default:
		return 180
	}
}

// InferVolatility classifies a topic string into a volatility class based on
// keywords. Used when volatility is not explicitly provided by the caller.
func InferVolatility(topic string) Volatility {
	t := strings.ToLower(topic)
	ephemeralKeywords := []string{"price", "market", "stock", "news", "today", "breaking", "weather", "score", "event", "election", "earnings"}
	for _, kw := range ephemeralKeywords {
		if strings.Contains(t, kw) {
			return VolatilityEphemeral
		}
	}
	currentKeywords := []string{"ai", "gpt", "llm", "model", "framework", "library", "api", "release", "version", "update", "software", "cloud", "crypto", "blockchain", "startup", "tech"}
	for _, kw := range currentKeywords {
		if strings.Contains(t, kw) {
			return VolatilityCurrent
		}
	}
	return VolatilityStable
}

// ─── MemoryFragment ───────────────────────────────────────────────────────────

// MemoryFragment is a unit of long-term memory.
type MemoryFragment struct {
	ID           string
	Content      string
	Source       string     // "conversation" | "curiosity" | "summary"
	Topic        string
	SessionID    string
	Importance   float64    // 0.0–1.0
	AccessCount  int
	LastAccessed time.Time
	// Epistemic hygiene
	Provenance   Provenance // origin quality — controls RAG weight
	Volatility   Volatility // decay class — controls Recycle half-life
	LineageDepth int        // synthetic hops from ground truth (0=direct)
}

// NewMemoryBank creates a MemoryBank from environment config.
// If PB_BASE_URL is not set, returns a disabled no-op bank.
func NewMemoryBank() *MemoryBank {
	adminClient := pb.NewClientFromEnv()
	maxRecs := 500000
	if v := os.Getenv("PB_MEMORY_MAX_RECORDS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			maxRecs = n
		}
	}
	enabled := adminClient.IsConfigured()
	if !enabled {
		log.Println("[memory-bank] PB_BASE_URL/PB_ADMIN_EMAIL/PB_ADMIN_PASSWORD not set — disabled")
		return &MemoryBank{adminClient: adminClient, maxRecs: maxRecs, enabled: false}
	}

	// Create Oricli's user-scoped client (analyst account)
	baseURL := strings.TrimRight(os.Getenv("PB_BASE_URL"), "/")
	oricliEmail := pb.OricliUserEmail()
	oricliPassword := pb.OricliUserPassword()
	oricliClient := pb.NewUserClient(baseURL, oricliEmail, oricliPassword)

	return &MemoryBank{
		adminClient:  adminClient,
		oricliClient: oricliClient,
		embedder:     NewEmbedder(),
		maxRecs:      maxRecs,
		enabled:      true,
	}
}

// IsEnabled returns true if PocketBase credentials are configured.
func (m *MemoryBank) IsEnabled() bool { return m.enabled }

func (m *MemoryBank) GetAdminClient() *pb.Client {
	return m.adminClient
}

// HasSource returns true if at least one memory fragment with the given source
// already exists in PocketBase. Uses a direct DB query — no embedder required.
func (m *MemoryBank) HasSource(source string) bool {
	if !m.enabled || m.adminClient == nil {
		return false
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	filter := fmt.Sprintf("source='%s'", source)
	result, err := m.adminClient.QueryRecords(ctx, "memories", filter, "", 1)
	if err != nil {
		return false
	}
	return result != nil && result.TotalItems > 0
}

// Bootstrap creates all required PocketBase collections on first run,
// and ensures Oricli's analyst account exists.
// Safe to call every startup — skips existing collections/users.
func (m *MemoryBank) Bootstrap(ctx context.Context) error {
	if !m.enabled {
		return nil
	}
	return pb.Bootstrap(ctx, m.adminClient)
}

// ─── Write ────────────────────────────────────────────────────────────────────

// Write stores a memory fragment to PocketBase asynchronously.
// Fires-and-forgets so it never blocks a chat response.
// source="curiosity" → written under Oricli's analyst account (author="oricli")
// source="conversation"|"summary" → written under admin (author="user")
func (m *MemoryBank) Write(frag MemoryFragment) {
	if !m.enabled {
		return
	}
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		author := "user"
		client := m.adminClient
		if frag.Source == "curiosity" {
			author = "oricli"
			client = m.oricliClient
		}

		data := map[string]any{
			"content":         frag.Content,
			"source":          frag.Source,
			"author":          author,
			"topic":           frag.Topic,
			"session_id":      frag.SessionID,
			"importance":      frag.Importance,
			"access_count":    0,
			"last_accessed":   time.Now().UTC().Format(time.RFC3339),
			"provenance":      string(frag.Provenance),
			"topic_volatility": string(frag.Volatility),
			"lineage_depth":   frag.LineageDepth,
		}
		id, err := client.CreateRecord(ctx, "memories", data)
		if err != nil {
			log.Printf("[memory-bank] write error: %v", err)
			return
		}
		// Async embedding — patch the record after creation so write latency is unchanged
		go func() {
			ectx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
			defer cancel()
			vec := m.embedder.Embed(ectx, frag.Content)
			if vec != nil {
				_ = client.UpdateRecord(ectx, "memories", id, map[string]any{
					"embedding": Float32ToJSON(vec),
				})
			}
		}()
	}()
}

// WriteKnowledgeFragment stores a CuriosityDaemon finding under Oricli's
// analyst account — these are her own epistemic discoveries (provenance=synthetic_l1).
func (m *MemoryBank) WriteKnowledgeFragment(topic, intent, content string, importance float64) {
	if !m.enabled {
		return
	}
	vol := InferVolatility(topic)
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		data := map[string]any{
			"topic":           topic,
			"intent":          intent,
			"content":         content,
			"author":          "oricli",
			"importance":      importance,
			"access_count":    0,
			"provenance":      string(ProvenanceSyntheticL1),
			"topic_volatility": string(vol),
			"lineage_depth":   1,
		}
		id, err := m.oricliClient.CreateRecord(ctx, "knowledge_fragments", data)
		if err != nil {
			log.Printf("[memory-bank] knowledge fragment write error: %v", err)
			return
		}
		go func() {
			ectx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
			defer cancel()
			vec := m.embedder.Embed(ectx, topic+" "+content)
			if vec != nil {
				_ = m.oricliClient.UpdateRecord(ectx, "knowledge_fragments", id, map[string]any{
					"embedding": Float32ToJSON(vec),
				})
			}
		}()
	}()
}

// ─── Query ────────────────────────────────────────────────────────────────────

// QuerySimilar fetches the topN most recent memories matching a topic keyword.
// Uses PocketBase filter (keyword contains match) — no embedding needed for MVP.
// Returns a formatted context block ready for system prompt injection.
// QuerySimilar fetches the topN most relevant memories for a query.
// Strategy:
//  1. Keyword pre-filter (topic/content contains match) → up to 50 candidates
//  2. Generate query embedding via nomic-embed-text
//  3. Cosine re-rank candidates that have embeddings populated
//  4. Fall back to importance/recency order if embeddings unavailable
func (m *MemoryBank) QuerySimilar(ctx context.Context, query string, topN int) ([]MemoryFragment, error) {
	if !m.enabled {
		return nil, nil
	}

	// ── Build keyword filter ──────────────────────────────────────────────────
	// Split query into individual meaningful keywords and build OR conditions.
	// This prevents the "what is SCAI?" bug where the full phrase never matches.
	keywords := extractQueryKeywords(query, 6)
	var filterParts []string
	for _, kw := range keywords {
		kw = strings.ReplaceAll(kw, `"`, `'`)
		kw = strings.ReplaceAll(kw, `\`, ``)
		filterParts = append(filterParts, fmt.Sprintf(`topic ~ "%s"`, kw), fmt.Sprintf(`content ~ "%s"`, kw))
	}

	var result *pb.ListRecordsResponse
	var err error

	if len(filterParts) > 0 {
		filter := strings.Join(filterParts, " || ")
		result, err = m.adminClient.QueryRecords(ctx, "memories", filter, "-importance,-created", 50)
		if err != nil {
			return nil, err
		}
	}

	// ── High-importance fallback ──────────────────────────────────────────────
	// Always include top-importance records (identity seed, user-stated facts)
	// so they can compete in cosine re-ranking even if no keyword matched.
	hiResult, hiErr := m.adminClient.QueryRecords(ctx, "memories", "importance>=0.9", "-importance,-created", 20)
	if hiErr == nil && hiResult != nil {
		seen := map[string]bool{}
		var merged []map[string]any
		if result != nil {
			merged = append(merged, result.Items...)
			for _, it := range result.Items {
				if id, ok := it["id"].(string); ok {
					seen[id] = true
				}
			}
		}
		for _, it := range hiResult.Items {
			id, _ := it["id"].(string)
			if !seen[id] {
				merged = append(merged, it)
				seen[id] = true
			}
		}
		if result == nil {
			result = hiResult
		}
		result.Items = merged
	}

	if result == nil || len(result.Items) == 0 {
		return nil, nil
	}

	// Generate query embedding for cosine re-ranking.
	// Use the caller's context so the 8s RAG deadline from server_v2 is honoured.
	// If the embedder is cold (all-minilm evicted by qwen3), this fails fast
	// and we fall back to importance-based scoring below — no 90s block.
	queryVec := m.embedder.Embed(ctx, query)

	type scoredFrag struct {
		frag  MemoryFragment
		score float32
	}
	scored := make([]scoredFrag, 0, len(result.Items))

	for _, item := range result.Items {
		prov := Provenance(stringField(item, "provenance"))
		if prov == "" {
			prov = ProvenanceSyntheticL1 // legacy records default to lowest-trust synthetic
		}
		lineage := intField(item, "lineage_depth")

		frag := MemoryFragment{
			ID:           stringField(item, "id"),
			Content:      stringField(item, "content"),
			Source:       stringField(item, "source"),
			Topic:        stringField(item, "topic"),
			SessionID:    stringField(item, "session_id"),
			Importance:   floatField(item, "importance"),
			AccessCount:  intField(item, "access_count"),
			Provenance:   prov,
			Volatility:   Volatility(stringField(item, "topic_volatility")),
			LineageDepth: lineage,
		}

		// ── Scoring ──────────────────────────────────────────────────────────
		// Base: cosine similarity (or importance as fallback)
		var base float32
		if queryVec != nil {
			if docVec := JSONToFloat32(item["embedding"]); docVec != nil {
				base = CosineSimilarity(queryVec, docVec)
			}
		}
		if base == 0 {
			base = float32(frag.Importance)
		}

		// Provenance multiplier — penalises deep synthetic lineage
		weight, ok := provenanceWeight[prov]
		if !ok {
			// Handle "synthetic_l2+" and any unknown values by provenance prefix
			weight = float32(0.6) / float32(max(lineage, 1))
		}

		score := base * weight

		// user_stated anchors get a large bonus so they always float to the top
		if prov == ProvenanceUserStated {
			score += 10.0
		}

		scored = append(scored, scoredFrag{frag: frag, score: score})
	}

	// Sort descending by score
	for i := 1; i < len(scored); i++ {
		for j := i; j > 0 && scored[j].score > scored[j-1].score; j-- {
			scored[j], scored[j-1] = scored[j-1], scored[j]
		}
	}

	// Take topN
	if topN > len(scored) {
		topN = len(scored)
	}
	frags := make([]MemoryFragment, topN)
	for i := 0; i < topN; i++ {
		frags[i] = scored[i].frag
		// Bump access count asynchronously
		id := frags[i].ID
		count := frags[i].AccessCount + 1
		go func() {
			uctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			_ = m.adminClient.UpdateRecord(uctx, "memories", id, map[string]any{
				"access_count":  count,
				"last_accessed": time.Now().UTC().Format(time.RFC3339),
			})
		}()
	}
	return frags, nil
}

// QuerySimilarStrings is a convenience wrapper over QuerySimilar that returns
// plain content strings. Used by the cognition.TaskExecutor to avoid a direct
// import dependency on the service package from within the cognition package.
func (m *MemoryBank) QuerySimilarStrings(ctx context.Context, query string, topN int) ([]string, error) {
	frags, err := m.QuerySimilar(ctx, query, topN)
	if err != nil || len(frags) == 0 {
		return nil, err
	}
	out := make([]string, len(frags))
	for i, f := range frags {
		out[i] = f.Content
	}
	return out, nil
}

// extractQueryKeywords splits a query into meaningful keywords for PocketBase
// filter construction. Strips stopwords and short tokens so "what is SCAI?"
// becomes ["SCAI"] rather than trying to match the full phrase.
func extractQueryKeywords(query string, max int) []string {
	stopWords := map[string]bool{
		"what": true, "is": true, "are": true, "the": true, "a": true, "an": true,
		"how": true, "does": true, "do": true, "can": true, "you": true, "me": true,
		"tell": true, "explain": true, "describe": true, "about": true, "with": true,
		"for": true, "your": true, "my": true, "its": true, "it": true, "this": true,
		"that": true, "was": true, "were": true, "and": true, "or": true, "of": true,
		"in": true, "on": true, "at": true, "to": true, "from": true, "by": true,
		"have": true, "has": true, "had": true, "be": true, "been": true, "being": true,
		"please": true, "could": true, "would": true, "should": true, "will": true,
	}
	words := strings.FieldsFunc(strings.ToLower(query), func(r rune) bool {
		return r == ' ' || r == '?' || r == '.' || r == '!' || r == ',' || r == '"' || r == '\''
	})
	seen := map[string]bool{}
	out := make([]string, 0, max)
	for _, w := range words {
		if len(w) < 3 || stopWords[w] || seen[w] {
			continue
		}
		seen[w] = true
		out = append(out, w)
		if len(out) >= max {
			break
		}
	}
	return out
}

// QueryKnowledgeFragments returns known topics from previous curiosity bursts.
func (m *MemoryBank) QueryKnowledgeFragments(ctx context.Context, limit int) ([]string, error) {
	if !m.enabled {
		return nil, nil
	}
	result, err := m.adminClient.QueryRecords(ctx, "knowledge_fragments", "", "-created", limit)
	if err != nil {
		return nil, err
	}
	topics := make([]string, 0, len(result.Items))
	for _, item := range result.Items {
		if t := stringField(item, "topic"); t != "" {
			topics = append(topics, t)
		}
	}
	return topics, nil
}

// KnowledgeCount returns how many knowledge_fragments exist for a given topic.
// Used by CuriosityDaemon for novelty-cap enforcement.
func (m *MemoryBank) KnowledgeCount(ctx context.Context, topic string) int {
	if !m.enabled {
		return 0
	}
	safe := strings.ReplaceAll(topic, `"`, `'`)
	if len(safe) > 80 {
		safe = safe[:80]
	}
	filter := fmt.Sprintf(`topic ~ "%s"`, safe)
	result, err := m.adminClient.QueryRecords(ctx, "knowledge_fragments", filter, "", 1)
	if err != nil {
		return 0
	}
	return result.TotalItems
}

// FormatRAGContext formats memory fragments as a system prompt injection block.
// Capped at maxChars to avoid bloating the context window.
func FormatRAGContext(frags []MemoryFragment, maxChars int) string {
	if len(frags) == 0 {
		return ""
	}
	var sb strings.Builder
	sb.WriteString("## Relevant Memory Context\n")
	for _, f := range frags {
		entry := fmt.Sprintf("- [%s] %s\n", f.Topic, f.Content)
		if sb.Len()+len(entry) > maxChars {
			break
		}
		sb.WriteString(entry)
	}
	return sb.String()
}

// ─── Memory Recycling ─────────────────────────────────────────────────────────

// retentionScore computes a decay-adjusted importance score.
// Uses per-record volatility class for the half-life instead of a hardcoded 180 days.
// Formula: importance × log(1 + access_count) × e^(-age_days / halfLife)
// user_stated anchors always return +Inf so they are never pruned. Gold memories are also immortal.
func retentionScore(importance float64, accessCount int, created time.Time, prov Provenance, vol Volatility) float64 {
	if prov == ProvenanceUserStated || prov == ProvenanceGold {
		return math.Inf(1) // anchors and gold bookmarks are immortal
	}
	halfLife := vol.halfLifeDays()
	if halfLife == 0 {
		halfLife = 180
	}
	ageDays := time.Since(created).Hours() / 24
	return importance * math.Log1p(float64(accessCount)) * math.Exp(-ageDays/halfLife)
}

// Recycle prunes the bottom 10% of memories by retention score when
// QueryBySource fetches the most recent MemoryFragments matching any of the given source values.
// Used by DreamDaemon to pull learning signals for consolidation.
func (m *MemoryBank) QueryBySource(ctx context.Context, sources []string, limit int) ([]MemoryFragment, error) {
	if !m.enabled || len(sources) == 0 {
		return nil, nil
	}

	var parts []string
	for _, s := range sources {
		safe := strings.ReplaceAll(s, `"`, `'`)
		parts = append(parts, fmt.Sprintf(`source = "%s"`, safe))
	}
	filter := strings.Join(parts, " || ")

	result, err := m.adminClient.QueryRecords(ctx, "memories", filter, "-created", limit)
	if err != nil {
		return nil, err
	}

	frags := make([]MemoryFragment, 0, len(result.Items))
	for _, item := range result.Items {
		prov := Provenance(stringField(item, "provenance"))
		if prov == "" {
			prov = ProvenanceConversation
		}
		frags = append(frags, MemoryFragment{
			ID:         stringField(item, "id"),
			Content:    stringField(item, "content"),
			Source:     stringField(item, "source"),
			Topic:      stringField(item, "topic"),
			Importance: floatField(item, "importance"),
			Provenance: prov,
		})
	}
	return frags, nil
}

// QuerySolved fetches solved-case fragments ranked by similarity to the given topic.
// Used by CBR engine to find past successful responses to adapt for the current query.
func (m *MemoryBank) QuerySolved(ctx context.Context, topic string, limit int) ([]MemoryFragment, error) {
	if !m.enabled {
		return nil, nil
	}
	filter := fmt.Sprintf(`provenance = "%s"`, string(ProvenanceSolved))
	result, err := m.adminClient.QueryRecords(ctx, "memories", filter, "-importance", limit*3)
	if err != nil {
		return nil, err
	}

	// Re-rank by topic keyword overlap (lightweight — no embedding call)
	topicWords := extractQueryKeywords(topic, 8)
	type scored struct {
		frag  MemoryFragment
		score int
	}
	var candidates []scored
	for _, item := range result.Items {
		content := strings.ToLower(stringField(item, "content"))
		s := 0
		for _, w := range topicWords {
			if strings.Contains(content, w) {
				s++
			}
		}
		if s > 0 {
			candidates = append(candidates, scored{
				frag: MemoryFragment{
					ID:         stringField(item, "id"),
					Content:    stringField(item, "content"),
					Source:     stringField(item, "source"),
					Topic:      stringField(item, "topic"),
					Importance: floatField(item, "importance"),
					Provenance: ProvenanceSolved,
				},
				score: s,
			})
		}
	}

	// Sort descending by keyword overlap
	for i := 1; i < len(candidates); i++ {
		for j := i; j > 0 && candidates[j].score > candidates[j-1].score; j-- {
			candidates[j], candidates[j-1] = candidates[j-1], candidates[j]
		}
	}

	out := make([]MemoryFragment, 0, limit)
	for i, c := range candidates {
		if i >= limit {
			break
		}
		out = append(out, c.frag)
	}
	return out, nil
}


// Rules:
//   - user_stated (anchor) memories are never pruned
//   - Decay half-life is per-record based on topic_volatility field
func (m *MemoryBank) Recycle() {
	if !m.enabled {
		return
	}
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
		defer cancel()

		count, err := m.adminClient.CountRecords(ctx, "memories")
		if err != nil || count <= m.maxRecs {
			return
		}

		pruneCount := count / 10
		log.Printf("[memory-bank] recycling up to %d low-retention memories (total=%d, max=%d)", pruneCount, count, m.maxRecs)

		// Fetch oldest + lowest-importance candidates, excluding user_stated anchors
		filter := `provenance != "user_stated"`
		result, err := m.adminClient.QueryRecords(ctx, "memories", filter, "importance,created", pruneCount*3)
		if err != nil {
			log.Printf("[memory-bank] recycle query error: %v", err)
			return
		}

		// Score each candidate and sort ascending (worst first)
		type candidate struct {
			id    string
			score float64
		}
		candidates := make([]candidate, 0, len(result.Items))
		for _, item := range result.Items {
			id := stringField(item, "id")
			if id == "" {
				continue
			}
			imp := floatField(item, "importance")
			acc := intField(item, "access_count")
			prov := Provenance(stringField(item, "provenance"))
			vol := Volatility(stringField(item, "topic_volatility"))
			if vol == "" {
				vol = InferVolatility(stringField(item, "topic"))
			}
			// Parse created timestamp
			var created time.Time
			if ts := stringField(item, "created"); ts != "" {
				created, _ = time.Parse(time.RFC3339, ts)
			}
			if created.IsZero() {
				created = time.Now().Add(-24 * time.Hour)
			}
			candidates = append(candidates, candidate{id: id, score: retentionScore(imp, acc, created, prov, vol)})
		}

		// Sort ascending by score (lowest = most pruneable)
		for i := 1; i < len(candidates); i++ {
			for j := i; j > 0 && candidates[j].score < candidates[j-1].score; j-- {
				candidates[j], candidates[j-1] = candidates[j-1], candidates[j]
			}
		}

		// Prune bottom pruneCount
		if pruneCount > len(candidates) {
			pruneCount = len(candidates)
		}
		pruned := 0
		for _, c := range candidates[:pruneCount] {
			if err := m.adminClient.DeleteRecord(ctx, "memories", c.id); err != nil {
				log.Printf("[memory-bank] recycle delete %s: %v", c.id, err)
			} else {
				pruned++
			}
		}
		log.Printf("[memory-bank] recycled %d memories", pruned)
	}()
}

// ─── Spend Ledger ─────────────────────────────────────────────────────────────

// PersistSpend upserts the RunPod monthly spend for a given service.
// month format: "2026-03". Runs async.
func (m *MemoryBank) PersistSpend(service, month string, amount float64) {
	if !m.enabled {
		return
	}
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		filter := fmt.Sprintf(`service = "%s" && month = "%s"`, service, month)
		result, err := m.adminClient.QueryRecords(ctx, "spend_ledger", filter, "", 1)
		if err != nil {
			log.Printf("[memory-bank] spend query error: %v", err)
			return
		}

		data := map[string]any{"service": service, "month": month, "amount": amount}
		if result.TotalItems > 0 {
			id := stringField(result.Items[0], "id")
			_ = m.adminClient.UpdateRecord(ctx, "spend_ledger", id, data)
		} else {
			_, _ = m.adminClient.CreateRecord(ctx, "spend_ledger", data)
		}
	}()
}

// LoadSpend fetches the stored monthly spend for a service.
// Returns 0.0 if not found. Blocks until complete — call on startup only.
func (m *MemoryBank) LoadSpend(ctx context.Context, service, month string) float64 {
	if !m.enabled {
		return 0
	}
	filter := fmt.Sprintf(`service = "%s" && month = "%s"`, service, month)
	result, err := m.adminClient.QueryRecords(ctx, "spend_ledger", filter, "", 1)
	if err != nil || result.TotalItems == 0 {
		return 0
	}
	return floatField(result.Items[0], "amount")
}

// ─── Conversation Summary ─────────────────────────────────────────────────────

// SaveConversationSummary stores a compressed session summary for future RAG.
func (m *MemoryBank) SaveConversationSummary(sessionID, summary string, msgCount int, topics []string) {
	if !m.enabled {
		return
	}
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		data := map[string]any{
			"session_id":    sessionID,
			"summary":       summary,
			"message_count": msgCount,
			"topics":        topics,
		}
		if _, err := m.adminClient.CreateRecord(ctx, "conversation_summaries", data); err != nil {
			log.Printf("[memory-bank] summary write error: %v", err)
		}
	}()
}

// ─── Field helpers ────────────────────────────────────────────────────────────

func stringField(m map[string]any, key string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

func floatField(m map[string]any, key string) float64 {
	if v, ok := m[key]; ok {
		switch n := v.(type) {
		case float64:
			return n
		case int:
			return float64(n)
		}
	}
	return 0
}

func intField(m map[string]any, key string) int {
	return int(floatField(m, key))
}

// ─── Paginated List (for Memory Browser API) ─────────────────────────────────

// PBMemoryRecord is a raw PocketBase record map for API responses.
// Named "PBMemoryRecord" to avoid collision with LMDB's MemoryRecord in memory.go.
type PBMemoryRecord map[string]any

// ListMemories fetches paginated memory records with optional filters.
func (m *MemoryBank) ListMemories(ctx context.Context, source, author, topic string, page, perPage int) ([]PBMemoryRecord, int, error) {
if !m.enabled {
return nil, 0, nil
}

var clauses []string
if source != "" {
clauses = append(clauses, fmt.Sprintf("source = \"%s\"", strings.ReplaceAll(source, "\"", "'")))
}
if author != "" {
clauses = append(clauses, fmt.Sprintf("author = \"%s\"", strings.ReplaceAll(author, "\"", "'")))
}
if topic != "" {
safe := strings.ReplaceAll(topic, "\"", "'")
clauses = append(clauses, fmt.Sprintf("topic ~ \"%s\"", safe))
}

filter := strings.Join(clauses, " && ")
offset := (page - 1) * perPage

result, err := m.adminClient.QueryRecordsPage(ctx, "memories", filter, "-created", perPage, offset)
if err != nil {
return nil, 0, err
}

recs := make([]PBMemoryRecord, len(result.Items))
for i, item := range result.Items {
delete(item, "embedding")
recs[i] = PBMemoryRecord(item)
}
return recs, result.TotalItems, nil
}

// ListKnowledgeFragments fetches paginated knowledge_fragment records.
func (m *MemoryBank) ListKnowledgeFragments(ctx context.Context, topic, author string, page, perPage int) ([]PBMemoryRecord, int, error) {
if !m.enabled {
return nil, 0, nil
}

var clauses []string
if topic != "" {
safe := strings.ReplaceAll(topic, "\"", "'")
clauses = append(clauses, fmt.Sprintf("topic ~ \"%s\"", safe))
}
if author != "" {
clauses = append(clauses, fmt.Sprintf("author = \"%s\"", strings.ReplaceAll(author, "\"", "'")))
}

filter := strings.Join(clauses, " && ")
offset := (page - 1) * perPage

result, err := m.adminClient.QueryRecordsPage(ctx, "knowledge_fragments", filter, "-created", perPage, offset)
if err != nil {
return nil, 0, err
}

recs := make([]PBMemoryRecord, len(result.Items))
for i, item := range result.Items {
delete(item, "embedding")
recs[i] = PBMemoryRecord(item)
}
return recs, result.TotalItems, nil
}
