package node

import (
	"context"
	"fmt"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// StepSafetyModule provides reasoning step safety filtering via the Swarm Bus
type StepSafetyModule struct {
	Bus    *bus.SwarmBus
	Filter *service.StepSafetyFilterService
	ID     string
}

// NewStepSafetyModule creates a new step safety module
func NewStepSafetyModule(swarmBus *bus.SwarmBus, filter *service.StepSafetyFilterService) *StepSafetyModule {
	return &StepSafetyModule{
		Bus:    swarmBus,
		Filter: filter,
		ID:     "step_safety_filter",
	}
}

// Start initiates the subscription to the bus
func (n *StepSafetyModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *StepSafetyModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	if operation != "filter_step" {
		return
	}

	// Bid for the task
	n.Bus.Publish(bus.Message{
		Topic: "tasks.bid",
		Payload: map[string]interface{}{
			"task_id":    msg.Payload["task_id"],
			"agent_id":   n.ID,
			"bid_amount": 0.2, // Moderate cost for safety analysis
			"confidence": 1.0,
		},
	})
}

func (n *StepSafetyModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	// Execute
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	sessionID := fmt.Sprintf("%v", params["session_id"])
	stepID := fmt.Sprintf("%v", params["step_id"])
	content := fmt.Sprintf("%v", params["content"])
	
	previousRaw, _ := params["previous_steps"].([]interface{})
	previous := make([]string, len(previousRaw))
	for i, p := range previousRaw {
		previous[i] = fmt.Sprintf("%v", p)
	}

	result, err := n.Filter.FilterStep(ctx, sessionID, stepID, content, previous)

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
