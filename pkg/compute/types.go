package compute

import "time"

// ── Compute Tier IDs ──────────────────────────────────────────────────────────

const (
	TierLocal  = "local"  // Ollama small model — free, ~800ms
	TierMedium = "medium" // Ollama code/mid model — free, ~1200ms
	TierRemote = "remote" // RunPod vLLM — metered, ~4000ms
)

// ── Bid ───────────────────────────────────────────────────────────────────────

// Bid is a compute tier's offer to handle a task.
// Each Bidder constructs one based on current state + historical confidence.
type Bid struct {
	TierID            string  `json:"tier_id"`             // TierLocal | TierMedium | TierRemote
	TierName          string  `json:"tier_name"`           // human label
	EstimatedCostUSD  float64 `json:"estimated_cost_usd"`  // 0 for local/medium
	EstimatedLatencyMs int    `json:"estimated_latency_ms"`
	ConfidenceScore   float64 `json:"confidence_score"`    // 0.0–1.0 historical quality
	Available         bool    `json:"available"`           // false → governor must skip
	Rationale         string  `json:"rationale"`           // brief reasoning for logging
}

// ── BidRequest ────────────────────────────────────────────────────────────────

// BidRequest carries the context for a single generation decision.
// Built by GenerationService before calling BidGovernor.Adjudicate().
type BidRequest struct {
	TaskClass       string    `json:"task_class"`        // from InferTopicClass or complexity router
	Complexity      float64   `json:"complexity"`        // 0.0–1.0 from ComplexityScorer
	EstTokens       int       `json:"est_tokens"`        // estimated prompt tokens
	LatencyBudgetMs int       `json:"latency_budget_ms"` // 0 = no hard limit
	BudgetUSD       float64   `json:"budget_usd"`        // remaining daily budget
	CostWeight      float64   `json:"cost_weight"`       // governor tuning — higher = cheaper wins
	LatencyWeight   float64   `json:"latency_weight"`    // governor tuning — higher = faster wins
	Timestamp       time.Time `json:"timestamp"`
}

// DefaultWeights returns sensible defaults for a real-time streaming request.
func DefaultWeights() (costWeight, latencyWeight float64) {
	return 8.0, 1.5
}

// BackgroundWeights returns weights for a background/async task — cost matters more, latency less.
func BackgroundWeights() (costWeight, latencyWeight float64) {
	return 12.0, 0.3
}

// ── BidResult ─────────────────────────────────────────────────────────────────

// BidResult is the governor's decision.
type BidResult struct {
	Winner    Bid     `json:"winner"`
	AllBids   []Bid   `json:"all_bids"`
	Score     float64 `json:"score"`     // winning value score
	Rationale string  `json:"rationale"` // why this bid won
	Timestamp time.Time `json:"timestamp"`
}

// ── Bidder interface ──────────────────────────────────────────────────────────

// Bidder is implemented by each compute tier.
// A Bidder inspects the request + its own historical confidence to produce a Bid.
type Bidder interface {
	// Bid returns the tier's offer for the given request.
	Bid(req BidRequest) Bid
}

// ── TierOutcome ───────────────────────────────────────────────────────────────

// TierOutcome is recorded after a generation completes.
// FeedbackLedger uses it to update confidence scores.
type TierOutcome struct {
	TierID          string    `json:"tier_id"`
	TaskClass       string    `json:"task_class"`
	ActualLatencyMs int       `json:"actual_latency_ms"`
	ActualCostUSD   float64   `json:"actual_cost_usd"`
	AnomalyScore    float64   `json:"anomaly_score"`    // 0.0 = perfect, 1.0 = HIGH anomaly
	Success         bool      `json:"success"`          // false = anomaly/error
	Timestamp       time.Time `json:"timestamp"`
}
