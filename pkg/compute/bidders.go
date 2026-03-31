package compute

import (
	"fmt"
	"os"
	"strconv"
)

// ── LocalBidder ───────────────────────────────────────────────────────────────

// LocalBidder represents the small Ollama model tier (e.g. qwen2.5:3b, ministral-3b).
// Always available, zero cost, fast latency.
type LocalBidder struct {
	ModelName string
	Feedback  *FeedbackLedger
	// baseLatencyMs is tuned from env or defaults.
	baseLatencyMs int
}

func NewLocalBidder(modelName string, feedback *FeedbackLedger) *LocalBidder {
	base := 900
	if v, err := strconv.Atoi(os.Getenv("COMPUTE_LOCAL_LATENCY_MS")); err == nil && v > 0 {
		base = v
	}
	return &LocalBidder{ModelName: modelName, Feedback: feedback, baseLatencyMs: base}
}

func (b *LocalBidder) Bid(req BidRequest) Bid {
	confidence := b.Feedback.ConfidenceFor(TierLocal, req.TaskClass)

	// Local struggles with heavy complexity — apply confidence penalty
	if req.Complexity > 0.75 {
		confidence *= 0.75
	} else if req.Complexity > 0.50 {
		confidence *= 0.88
	}

	return Bid{
		TierID:             TierLocal,
		TierName:           fmt.Sprintf("Local (%s)", b.ModelName),
		EstimatedCostUSD:   0,
		EstimatedLatencyMs: b.baseLatencyMs,
		ConfidenceScore:    confidence,
		Available:          true,
		Rationale:          fmt.Sprintf("local ollama, confidence=%.2f for %s", confidence, req.TaskClass),
	}
}

// ── MediumBidder ──────────────────────────────────────────────────────────────

// MediumBidder represents the Ollama code/mid-size model tier.
// Always available, zero cost, slightly higher latency than local.
type MediumBidder struct {
	ModelName string
	Feedback  *FeedbackLedger
	baseLatencyMs int
}

func NewMediumBidder(modelName string, feedback *FeedbackLedger) *MediumBidder {
	base := 1400
	if v, err := strconv.Atoi(os.Getenv("COMPUTE_MEDIUM_LATENCY_MS")); err == nil && v > 0 {
		base = v
	}
	return &MediumBidder{ModelName: modelName, Feedback: feedback, baseLatencyMs: base}
}

func (b *MediumBidder) Bid(req BidRequest) Bid {
	confidence := b.Feedback.ConfidenceFor(TierMedium, req.TaskClass)

	// Medium model shines on technical/code tasks — boost confidence
	switch req.TaskClass {
	case "technical", "procedural", "definition":
		confidence = min64(confidence*1.10, 0.99)
	}
	// Still penalise very heavy tasks — those belong to remote
	if req.Complexity > 0.85 {
		confidence *= 0.82
	}

	return Bid{
		TierID:             TierMedium,
		TierName:           fmt.Sprintf("Medium (%s)", b.ModelName),
		EstimatedCostUSD:   0,
		EstimatedLatencyMs: b.baseLatencyMs,
		ConfidenceScore:    confidence,
		Available:          true,
		Rationale:          fmt.Sprintf("medium ollama, confidence=%.2f for %s", confidence, req.TaskClass),
	}
}

// ── RemoteBidder ──────────────────────────────────────────────────────────────

// RemoteBidder represents the RunPod vLLM tier.
// Metered cost, high latency when cold, highest confidence for complex tasks.
type RemoteBidder struct {
	ModelName     string
	Feedback      *FeedbackLedger
	Available     bool    // injected at boot — false if RunPod not configured
	HourlyRateUSD float64 // current pod hourly rate (from RunPod manager)
	baseLatencyMs int     // cold-start estimate
	warmLatencyMs int     // warm pod estimate
	PodWarm       bool    // injected — true when pod is already running
}

func NewRemoteBidder(modelName string, feedback *FeedbackLedger, available bool, hourlyRate float64) *RemoteBidder {
	cold := 5000
	warm := 2500
	if v, err := strconv.Atoi(os.Getenv("COMPUTE_REMOTE_COLD_LATENCY_MS")); err == nil && v > 0 {
		cold = v
	}
	if v, err := strconv.Atoi(os.Getenv("COMPUTE_REMOTE_WARM_LATENCY_MS")); err == nil && v > 0 {
		warm = v
	}
	return &RemoteBidder{
		ModelName:     modelName,
		Feedback:      feedback,
		Available:     available,
		HourlyRateUSD: hourlyRate,
		baseLatencyMs: cold,
		warmLatencyMs: warm,
	}
}

func (b *RemoteBidder) Bid(req BidRequest) Bid {
	if !b.Available {
		return Bid{
			TierID:    TierRemote,
			TierName:  "Remote (RunPod)",
			Available: false,
			Rationale: "RunPod not configured",
		}
	}
	if req.BudgetUSD <= 0 {
		return Bid{
			TierID:    TierRemote,
			TierName:  "Remote (RunPod)",
			Available: false,
			Rationale: "daily budget exhausted",
		}
	}

	confidence := b.Feedback.ConfidenceFor(TierRemote, req.TaskClass)

	// Remote excels at high-complexity tasks
	if req.Complexity > 0.75 {
		confidence = min64(confidence*1.12, 0.99)
	}

	// Estimate cost: assume avg 12 seconds per generation at hourly rate
	estSeconds := 12.0
	if req.EstTokens > 2000 {
		estSeconds = 20.0
	}
	estCost := b.HourlyRateUSD * (estSeconds / 3600.0)

	// Check if this single call would exceed remaining budget
	if estCost > req.BudgetUSD {
		return Bid{
			TierID:    TierRemote,
			TierName:  "Remote (RunPod)",
			Available: false,
			Rationale: fmt.Sprintf("estimated cost $%.4f exceeds remaining budget $%.4f", estCost, req.BudgetUSD),
		}
	}

	latency := b.baseLatencyMs
	if b.PodWarm {
		latency = b.warmLatencyMs
	}

	return Bid{
		TierID:             TierRemote,
		TierName:           fmt.Sprintf("Remote (%s)", b.ModelName),
		EstimatedCostUSD:   estCost,
		EstimatedLatencyMs: latency,
		ConfidenceScore:    confidence,
		Available:          true,
		Rationale:          fmt.Sprintf("runpod vllm, warm=%v, cost=$%.4f, confidence=%.2f", b.PodWarm, estCost, confidence),
	}
}

// ── helpers ───────────────────────────────────────────────────────────────────

func min64(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}
