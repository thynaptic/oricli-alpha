package node

import (
	"fmt"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// IntentModule provides Intent Detection and Categorization via the Swarm Bus
type IntentModule struct {
	Bus    *bus.SwarmBus
	Intent *service.IntentService
	ID     string
}

// NewIntentModule creates a new intent module
func NewIntentModule(swarmBus *bus.SwarmBus, intent *service.IntentService) *IntentModule {
	return &IntentModule{
		Bus:    swarmBus,
		Intent: intent,
		ID:     "intent_categorizer",
	}
}

// Start initiates the subscription to the bus
func (n *IntentModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *IntentModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	if operation != "categorize_intent" && operation != "detect_intent" {
		return
	}

	// Bid for the task
	n.Bus.Publish(bus.Message{
		Topic: "tasks.bid",
		Payload: map[string]interface{}{
			"task_id":    msg.Payload["task_id"],
			"agent_id":   n.ID,
			"bid_amount": 0.05, // Extremely fast, keyword-based
			"confidence": 0.9,
		},
	})
}

func (n *IntentModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	// Execute
	intent := fmt.Sprintf("%v", params["intent"])
	userMessage := fmt.Sprintf("%v", params["user_message"])

	result := n.Intent.CategorizeIntent(intent, userMessage)

	// Publish result
	n.Bus.Publish(bus.Message{
		Topic:   "tasks.result",
		Payload: map[string]interface{}{
			"task_id": taskID,
			"success": true,
			"result":  result,
		},
	})
}
