package service

import (
	"context"
	"fmt"
	"sort"
	"strings"
)

// ConsensusPolicy defines how to reach agreement between agent outputs
type ConsensusPolicy string

const (
	PolicyMajority  ConsensusPolicy = "majority"
	PolicyUnanimity ConsensusPolicy = "unanimity"
	PolicyAverage   ConsensusPolicy = "average"
	PolicyMerge     ConsensusPolicy = "merge"
	PolicyMergeTop  ConsensusPolicy = "merge_top"
	PolicyWeighted  ConsensusPolicy = "weighted"
)

// AgentOpinion represents a single agent's output and confidence
type AgentOpinion struct {
	AgentID    string                 `json:"agent_id"`
	Content    string                 `json:"content"`
	Confidence float64                `json:"confidence"`
	Metadata   map[string]interface{} `json:"metadata"`
}

// ConsensusResult represents the outcome of a consensus operation
type ConsensusResult struct {
	Decision   string                 `json:"decision"`
	Confidence float64                `json:"confidence"`
	Opinions   []AgentOpinion         `json:"opinions"`
	Agreement  float64                `json:"agreement"`
	Policy     ConsensusPolicy        `json:"policy"`
	Metadata   map[string]interface{} `json:"metadata"`
}

// SwarmConsensusService manages multi-agent consensus logic
type SwarmConsensusService struct {
	genService *GenerationService
}

// NewSwarmConsensusService creates a new consensus service
func NewSwarmConsensusService(genService *GenerationService) *SwarmConsensusService {
	return &SwarmConsensusService{
		genService: genService,
	}
}

// ReachConsensus applies a consensus policy to a set of opinions
func (s *SwarmConsensusService) ReachConsensus(ctx context.Context, opinions []AgentOpinion, policy ConsensusPolicy) (*ConsensusResult, error) {
	if len(opinions) == 0 {
		return nil, fmt.Errorf("no opinions provided for consensus")
	}

	switch policy {
	case PolicyMajority:
		return s.reachMajorityConsensus(opinions), nil
	case PolicyMerge, PolicyMergeTop:
		return s.reachMergeConsensus(ctx, opinions, policy)
	case PolicyWeighted:
		return s.reachWeightedConsensus(opinions), nil
	default:
		return s.reachMajorityConsensus(opinions), nil
	}
}

func (s *SwarmConsensusService) reachMajorityConsensus(opinions []AgentOpinion) *ConsensusResult {
	counts := make(map[string]int)
	maxCount := 0
	winner := ""

	for _, o := range opinions {
		counts[o.Content]++
		if counts[o.Content] > maxCount {
			maxCount = counts[o.Content]
			winner = o.Content
		}
	}

	agreement := float64(maxCount) / float64(len(opinions))
	
	// Average confidence of the winner
	totalConf := 0.0
	winnerCount := 0
	for _, o := range opinions {
		if o.Content == winner {
			totalConf += o.Confidence
			winnerCount++
		}
	}

	confidence := totalConf / float64(winnerCount)

	return &ConsensusResult{
		Decision:   winner,
		Confidence: confidence,
		Agreement:  agreement,
		Opinions:   opinions,
		Policy:     PolicyMajority,
	}
}

func (s *SwarmConsensusService) reachWeightedConsensus(opinions []AgentOpinion) *ConsensusResult {
	weightedCounts := make(map[string]float64)
	maxWeight := 0.0
	winner := ""

	for _, o := range opinions {
		weightedCounts[o.Content] += o.Confidence
		if weightedCounts[o.Content] > maxWeight {
			maxWeight = weightedCounts[o.Content]
			winner = o.Content
		}
	}

	totalWeight := 0.0
	for _, weight := range weightedCounts {
		totalWeight += weight
	}

	agreement := maxWeight / totalWeight
	
	return &ConsensusResult{
		Decision:   winner,
		Confidence: agreement, // For weighted, agreement effectively IS the confidence
		Agreement:  agreement,
		Opinions:   opinions,
		Policy:     PolicyWeighted,
	}
}

func (s *SwarmConsensusService) reachMergeConsensus(ctx context.Context, opinions []AgentOpinion, policy ConsensusPolicy) (*ConsensusResult, error) {
	if s.genService == nil {
		// Fallback to majority if generation service is not available
		return s.reachMajorityConsensus(opinions), nil
	}

	// Sort by confidence
	sort.Slice(opinions, func(i, j int) bool {
		return opinions[i].Confidence > opinions[j].Confidence
	})

	targets := opinions
	if policy == PolicyMergeTop && len(opinions) > 3 {
		targets = opinions[:3]
	}

	var builder strings.Builder
	builder.WriteString("Please merge the following agent opinions into a single, cohesive consensus response. Resolve contradictions by favoring high-confidence inputs.\n\n")
	
	for i, o := range targets {
		builder.WriteString(fmt.Sprintf("Agent %d (Confidence: %.2f):\n%s\n\n", i+1, o.Confidence, o.Content))
	}

	// Simplified: use GenerationService directly
	resp, err := s.genService.Generate(builder.String(), map[string]interface{}{
		"temperature": 0.3,
	})
	if err != nil {
		return nil, err
	}

	avgConf := 0.0
	for _, o := range targets {
		avgConf += o.Confidence
	}
	avgConf /= float64(len(targets))

	responseText, _ := resp["text"].(string)

	return &ConsensusResult{
		Decision:   responseText,
		Confidence: avgConf,
		Agreement:  1.0, // Merged result is considered 100% agreed upon after synthesis
		Opinions:   opinions,
		Policy:     policy,
	}, nil
}
