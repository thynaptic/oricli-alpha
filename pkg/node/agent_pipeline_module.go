package node

import (
	"context"
	"fmt"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// AgentPipelineModule provides end-to-end Q&A orchestration via the Swarm Bus
type AgentPipelineModule struct {
	Bus      *bus.SwarmBus
	Pipeline *service.AgentPipelineService
	ID       string
}

// NewAgentPipelineModule creates a new agent pipeline module
func NewAgentPipelineModule(swarmBus *bus.SwarmBus, pipeline *service.AgentPipelineService) *AgentPipelineModule {
	return &AgentPipelineModule{
		Bus:      swarmBus,
		Pipeline: pipeline,
		ID:       "agent_pipeline",
	}
}

// Start initiates the subscription to the bus
func (n *AgentPipelineModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *AgentPipelineModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	if operation != "run_pipeline" {
		return
	}

	taskID, _ := msg.Payload["task_id"].(string)

	// Bid for the task
	n.Bus.Publish(bus.Message{
		Protocol: bus.BID,
		Topic:    fmt.Sprintf("tasks.bid.%s", taskID),
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"agent_id":     n.ID,
			"compute_cost": 0.6, // Pipeline is relatively high cost but high value
			"confidence":   1.0,
		},
	})
}

func (n *AgentPipelineModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	// Execute
	ctx, cancel := context.WithTimeout(context.Background(), 300*time.Second)
	defer cancel()

	query, _ := params["query"].(string)
	limit := int(service.ToFloat64(params["limit"]))
	if limit <= 0 {
		limit = 10
	}
	
	sourcesRaw, _ := params["sources"].([]interface{})
	sources := make([]string, len(sourcesRaw))
	for i, s := range sourcesRaw {
		sources[i] = fmt.Sprintf("%v", s)
	}
	if len(sources) == 0 {
		sources = []string{"web", "memory"}
	}

	result, err := n.Pipeline.RunPipeline(ctx, query, limit, sources)

	// Publish result
	resPayload := map[string]interface{}{
		"task_id": taskID,
		"success": err == nil,
	}

	if err != nil {
		resPayload["error"] = err.Error()
	} else {
		resPayload["result"] = result
	}

	n.Bus.Publish(bus.Message{
		Topic:   "tasks.result",
		Payload: resPayload,
	})
}
