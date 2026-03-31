package compute

import (
	"fmt"
	"log"
	"sync"
	"time"
)

const (
	defaultCostWeight    = 8.0
	defaultLatencyWeight = 1.5
	decisionLogSize      = 100
)

// ── BidGovernor ───────────────────────────────────────────────────────────────

// BidGovernor collects bids from all registered Bidders and selects the winner.
// Scoring function: value = confidence / (1 + cost×CostWeight + latencyNorm×LatencyWeight)
// where latencyNorm = EstimatedLatencyMs / 10000
//
// The governor always falls back to the local tier if no other bid is viable.
type BidGovernor struct {
	mu      sync.RWMutex
	bidders []Bidder
	log     []BidResult // rolling decision log
}

// NewBidGovernor creates a BidGovernor with the given Bidders.
// Order matters for fallback: first bidder is the default fallback (should be local).
func NewBidGovernor(bidders ...Bidder) *BidGovernor {
	return &BidGovernor{
		bidders: bidders,
		log:     make([]BidResult, 0, decisionLogSize),
	}
}

// Adjudicate collects bids from all registered Bidders and returns the best one.
// It never returns an error — falls back to first available bidder in the worst case.
func (g *BidGovernor) Adjudicate(req BidRequest) BidResult {
	if req.CostWeight == 0 {
		req.CostWeight = defaultCostWeight
	}
	if req.LatencyWeight == 0 {
		req.LatencyWeight = defaultLatencyWeight
	}
	if req.Timestamp.IsZero() {
		req.Timestamp = time.Now()
	}

	// Collect all bids
	bids := make([]Bid, 0, len(g.bidders))
	for _, bidder := range g.bidders {
		bid := bidder.Bid(req)
		bids = append(bids, bid)
	}

	// Score available bids
	bestScore := -1.0
	bestIdx := -1
	for i, bid := range bids {
		if !bid.Available {
			continue
		}
		score := g.score(bid, req)
		if score > bestScore {
			bestScore = score
			bestIdx = i
		}
	}

	var winner Bid
	var rationale string

	if bestIdx >= 0 {
		winner = bids[bestIdx]
		rationale = fmt.Sprintf("winner: %s (score=%.4f) | %s", winner.TierID, bestScore, winner.Rationale)
	} else {
		// All bids unavailable — force local as last resort
		winner = Bid{
			TierID:             TierLocal,
			TierName:           "Local (forced fallback)",
			EstimatedCostUSD:   0,
			EstimatedLatencyMs: 1000,
			ConfidenceScore:    0.50,
			Available:          true,
			Rationale:          "all tiers unavailable — forced local fallback",
		}
		bestScore = g.score(winner, req)
		rationale = "forced fallback: all tiers unavailable"
		log.Printf("[BidGovernor] WARNING — all tiers unavailable, falling back to local")
	}

	result := BidResult{
		Winner:    winner,
		AllBids:   bids,
		Score:     bestScore,
		Rationale: rationale,
		Timestamp: time.Now(),
	}

	g.recordDecision(result)
	return result
}

// RecentDecisions returns the last n decisions from the rolling log.
func (g *BidGovernor) RecentDecisions(n int) []BidResult {
	g.mu.RLock()
	defer g.mu.RUnlock()
	if n > len(g.log) {
		n = len(g.log)
	}
	out := make([]BidResult, n)
	copy(out, g.log[len(g.log)-n:])
	return out
}

// ── Scoring ───────────────────────────────────────────────────────────────────

// score computes the value score for a bid.
// Higher is better. Formula:
//
//	value = confidence / (1 + cost_penalty + latency_penalty)
//
// cost_penalty  = EstimatedCostUSD × CostWeight
// latency_penalty = (EstimatedLatencyMs / 10000) × LatencyWeight
//
// Latency hard-cut: if LatencyBudgetMs > 0 and bid exceeds it, score = 0.
func (g *BidGovernor) score(bid Bid, req BidRequest) float64 {
	if !bid.Available {
		return -1
	}
	// Hard latency cut
	if req.LatencyBudgetMs > 0 && bid.EstimatedLatencyMs > req.LatencyBudgetMs {
		return 0
	}
	costPenalty := bid.EstimatedCostUSD * req.CostWeight
	latencyNorm := float64(bid.EstimatedLatencyMs) / 10000.0
	latencyPenalty := latencyNorm * req.LatencyWeight
	denom := 1.0 + costPenalty + latencyPenalty
	return bid.ConfidenceScore / denom
}

// ── Internal ──────────────────────────────────────────────────────────────────

func (g *BidGovernor) recordDecision(result BidResult) {
	g.mu.Lock()
	defer g.mu.Unlock()
	if len(g.log) >= decisionLogSize {
		g.log = g.log[1:]
	}
	g.log = append(g.log, result)
}
