package service

import (
	"fmt"
	"log"
	"sort"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/bus"
)

type AgentType string

const (
	AgentSearch    AgentType = "search"
	AgentRanking   AgentType = "ranking"
	AgentSynthesis AgentType = "synthesis"
	AgentResearch  AgentType = "research"
	AgentAnalysis  AgentType = "analysis"
	AgentAnswer    AgentType = "answer"
)

type AgentTask struct {
	ID           string                 `json:"id"`
	AgentType    AgentType              `json:"agent_type"`
	Query        string                 `json:"query"`
	Context      map[string]interface{} `json:"context"`
	Dependencies []string               `json:"dependencies"`
	Priority     int                    `json:"priority"`
	RequireGosh  bool                   `json:"require_gosh"`
	Bounty       float64                `json:"bounty"` // Metacog token reward
}

type AgentBid struct {
	AgentID    string  `json:"agent_id"`
	TaskID     string  `json:"task_id"`
	Confidence float64 `json:"confidence"`
	TokenBid   float64 `json:"token_bid"`           // Skin in the game
	GoshTrace  string  `json:"gosh_trace,omitempty"` // Sandbox validation
	Reason     string  `json:"reason"`
}

type AgentResult struct {
	TaskID    string      `json:"task_id"`
	AgentType AgentType   `json:"agent_type"`
	Success   bool        `json:"success"`
	Output    interface{} `json:"output"`
	Error     string      `json:"error,omitempty"`
}

// AgentCoordinator manages the fleet of specialized agents using the Contract Net Protocol (CNP)
type AgentCoordinator struct {
	Bus     *bus.SwarmBus
	Results map[string]AgentResult
	Mu      sync.RWMutex
}

func NewAgentCoordinator(swarmBus *bus.SwarmBus) *AgentCoordinator {
	return &AgentCoordinator{
		Bus:     swarmBus,
		Results: make(map[string]AgentResult),
	}
}

// ExecuteTask orchestrates the full CNP lifecycle: CFP -> Bidding -> Acceptance -> Result
func (c *AgentCoordinator) ExecuteTask(task AgentTask, timeout time.Duration) (AgentResult, error) {
	if task.ID == "" {
		task.ID = uuid.New().String()[:8]
	}

	log.Printf("[Coordinator] Starting CNP session for %s task: %s (Bounty: %.2f)", task.AgentType, task.ID, task.Bounty)

	// 1. Collect Bids
	bids, err := c.CollectBids(task, timeout/2)
	if err != nil || len(bids) == 0 {
		return AgentResult{}, fmt.Errorf("failed to collect bids for task %s: %v", task.ID, err)
	}

	// 2. Select Winner
	winner := c.SelectWinner(task, bids)
	log.Printf("[Coordinator] Winner selected for %s: %s (Confidence: %.2f, TokenBid: %.2f)", task.ID, winner.AgentID, winner.Confidence, winner.TokenBid)

	// 3. Subscribe to result
	resultCh := make(chan AgentResult, 1)
	topic := fmt.Sprintf("agent.result.%s", task.ID)
	
	c.Bus.Subscribe(topic, func(msg bus.Message) {
		res := AgentResult{
			TaskID:    task.ID,
			AgentType: task.AgentType,
			Success:   msg.Protocol == bus.RESULT,
			Output:    msg.Payload["result"],
		}
		if msg.Protocol == bus.ERROR {
			res.Error, _ = msg.Payload["error"].(string)
		}
		resultCh <- res
	})

	// 4. Accept Bid
	c.Bus.Publish(bus.Message{
		Protocol:    bus.ACCEPT,
		Topic:       "tasks.accept",
		SenderID:    "coordinator",
		RecipientID: winner.AgentID,
		Payload: map[string]interface{}{
			"task_id": task.ID,
			"bounty":  task.Bounty,
		},
	})

	// 5. Wait for result
	select {
	case res := <-resultCh:
		c.Mu.Lock()
		c.Results[task.ID] = res
		c.Mu.Unlock()
		
		// If successful, we would normally trigger the Bounty payout here
		if res.Success {
			c.handleBountyPayout(winner, task.Bounty)
		}
		
		return res, nil
	case <-time.After(timeout / 2):
		return AgentResult{}, fmt.Errorf("task %s timed out waiting for result", task.ID)
	}
}

func (c *AgentCoordinator) handleBountyPayout(winner AgentBid, bounty float64) {
	log.Printf("[Coordinator] Payout initiated: %.2f MetacogTokens -> Agent %s", bounty, winner.AgentID)
	// In Phase 3, this will call the AgentProfileService to update the wallet
}

// CollectBids broadcasts a CFP and listens for AgentBids
func (c *AgentCoordinator) CollectBids(task AgentTask, timeout time.Duration) ([]AgentBid, error) {
	bidCh := make(chan AgentBid, 10)
	topic := fmt.Sprintf("agent.bid.%s", task.ID)
	
	c.Bus.Subscribe(topic, func(msg bus.Message) {
		if msg.Protocol == bus.BID {
			bid := AgentBid{
				AgentID:    msg.SenderID,
				TaskID:     task.ID,
				Confidence: msg.Payload["confidence"].(float64),
				Reason:     msg.Payload["reason"].(string),
			}
			if tbid, ok := msg.Payload["token_bid"].(float64); ok {
				bid.TokenBid = tbid
			}
			if trace, ok := msg.Payload["gosh_trace"].(string); ok {
				bid.GoshTrace = trace
			}
			bidCh <- bid
		}
	})

	// Publish CFP
	c.Bus.Publish(bus.Message{
		Protocol: bus.CFP,
		Topic:    "tasks.cfp",
		SenderID: "coordinator",
		Payload: map[string]interface{}{
			"task_id":      task.ID,
			"operation":    string(task.AgentType),
			"query":        task.Query,
			"require_gosh": task.RequireGosh,
			"bounty":       task.Bounty,
		},
	})

	var bids []AgentBid
	start := time.Now()
	for time.Since(start) < timeout {
		select {
		case bid := <-bidCh:
			bids = append(bids, bid)
		case <-time.After(timeout - time.Since(start)):
			goto done
		}
	}

done:
	return bids, nil
}

// SelectWinner picks the best agent based on confidence, Gosh verification, and skin in the game (tokens)
func (c *AgentCoordinator) SelectWinner(task AgentTask, bids []AgentBid) AgentBid {
	sort.Slice(bids, func(i, j int) bool {
		// 1. Mandatory Gosh priority
		if task.RequireGosh {
			if bids[i].GoshTrace != "" && bids[j].GoshTrace == "" {
				return true
			}
			if bids[i].GoshTrace == "" && bids[j].GoshTrace != "" {
				return false
			}
		}
		
		// 2. Token Bid (Skin in the game)
		if bids[i].TokenBid != bids[j].TokenBid {
			return bids[i].TokenBid > bids[j].TokenBid
		}

		// 3. Confidence fallback
		return bids[i].Confidence > bids[j].Confidence
	})
	return bids[0]
}

// GenerateCodeReasoning is a high-level helper for the API to request synthesis tasks.
func (c *AgentCoordinator) GenerateCodeReasoning(query string, timeout time.Duration) (map[string]interface{}, error) {
	task := AgentTask{
		AgentType:   AgentSynthesis,
		Query:       query,
		RequireGosh: true,
		Bounty:      100.0, // Default bounty for API requests
	}

	res, err := c.ExecuteTask(task, timeout)
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"success": res.Success,
		"code":    res.Output,
		"task_id": res.TaskID,
	}, nil
}

// ExecuteParallel runs multiple tasks simultaneously using Goroutines
func (c *AgentCoordinator) ExecuteParallel(tasks []AgentTask, timeout time.Duration) []AgentResult {
	var wg sync.WaitGroup
	results := make([]AgentResult, len(tasks))

	for i, t := range tasks {
		wg.Add(1)
		go func(idx int, task AgentTask) {
			defer wg.Done()
			res, err := c.ExecuteTask(task, timeout)
			if err != nil {
				results[idx] = AgentResult{TaskID: task.ID, Success: false, Error: err.Error()}
			} else {
				results[idx] = res
			}
		}(i, t)
	}
	wg.Wait()
	return results
}
