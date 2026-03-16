package service

import (
	"fmt"
	"log"
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
}

type AgentResult struct {
	TaskID    string      `json:"task_id"`
	AgentType AgentType   `json:"agent_type"`
	Success   bool        `json:"success"`
	Output    interface{} `json:"output"`
	Error     string      `json:"error,omitempty"`
}

// AgentCoordinator manages the fleet of specialized agents
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

// ExecuteTask sends a task to the bus and waits for the result
func (c *AgentCoordinator) ExecuteTask(task AgentTask, timeout time.Duration) (AgentResult, error) {
	if task.ID == "" {
		task.ID = uuid.New().String()[:8]
	}

	log.Printf("[Coordinator] Dispatching %s task: %s", task.AgentType, task.ID)

	// 1. Subscribe to result for this specific task
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

	// 2. Publish CFP for the agent
	c.Bus.Publish(bus.Message{
		Protocol: bus.CFP,
		Topic:    "tasks.cfp",
		SenderID: "coordinator",
		Payload: map[string]interface{}{
			"task_id":   task.ID,
			"operation": string(task.AgentType),
			"query":     task.Query,
			"params":    task.Context,
		},
	})

	// 3. Wait for result
	select {
	case res := <-resultCh:
		c.Mu.Lock()
		c.Results[task.ID] = res
		c.Mu.Unlock()
		return res, nil
	case <-time.After(timeout):
		return AgentResult{}, fmt.Errorf("task %s timed out after %v", task.ID, timeout)
	}
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

// GenerateCodeReasoning parallelizes code-specific cognitive tasks
func (c *AgentCoordinator) GenerateCodeReasoning(requirements string, timeout time.Duration) (map[string]interface{}, error) {
	log.Printf("[Coordinator] Starting reasoning-driven code generation for requirements")

	tasks := []AgentTask{
		{AgentType: "analysis", Query: fmt.Sprintf("Analyze semantic structure: %s", requirements)},
		{AgentType: "research", Query: fmt.Sprintf("Find relevant code patterns for: %s", requirements)},
	}

	results := c.ExecuteParallel(tasks, timeout)
	
	// Synthesis phase
	synthesisTask := AgentTask{
		AgentType: "synthesis",
		Query:     fmt.Sprintf("Synthesize code for: %s", requirements),
		Context: map[string]interface{}{
			"analysis": results[0].Output,
			"research": results[1].Output,
		},
	}

	finalRes, err := c.ExecuteTask(synthesisTask, timeout)
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"success": finalRes.Success,
		"code":    finalRes.Output,
		"steps":   results,
	}, nil
}
