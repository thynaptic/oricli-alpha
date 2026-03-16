package node

import (
	"fmt"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ConversationalModule provides basic greetings and engagement via the Swarm Bus
type ConversationalModule struct {
	Bus     *bus.SwarmBus
	Service *service.ConversationalService
	ID      string
}

// NewConversationalModule creates a new conversational module
func NewConversationalModule(swarmBus *bus.SwarmBus, svc *service.ConversationalService) *ConversationalModule {
	return &ConversationalModule{
		Bus:     swarmBus,
		Service: svc,
		ID:      "conversational_defaults",
	}
}

// Start initiates the subscription to the bus
func (n *ConversationalModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *ConversationalModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	supportedOps := map[string]bool{
		"generate_response":    true,
		"add_back_channeling": true,
	}

	if !supportedOps[operation] {
		return
	}

	// Bid for the task
	bid := 0.05
	conf := 0.1
	
	if operation == "generate_response" {
		messages, _ := msg.Payload["params"].(map[string]interface{})["messages"].([]interface{})
		lastMsg := ""
		if len(messages) > 0 {
			lastMsg, _ = messages[len(messages)-1].(map[string]interface{})["content"].(string)
		}
		_, conf = n.Service.GenerateDefaultResponse(lastMsg)
	}

	n.Bus.Publish(bus.Message{
		Topic: "tasks.bid",
		Payload: map[string]interface{}{
			"task_id":    msg.Payload["task_id"],
			"agent_id":   n.ID,
			"bid_amount": bid,
			"confidence": conf,
		},
	})
}

func (n *ConversationalModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})
	operation, _ := msg.Payload["operation"].(string)

	var result interface{}
	var success bool = true

	switch operation {
	case "generate_response":
		messages, _ := params["messages"].([]interface{})
		lastMsg := ""
		if len(messages) > 0 {
			lastMsg, _ = messages[len(messages)-1].(map[string]interface{})["content"].(string)
		}
		text, conf := n.Service.GenerateDefaultResponse(lastMsg)
		result = map[string]interface{}{
			"text":       text,
			"confidence": conf,
			"method":     "conversational_default",
		}
	case "add_back_channeling":
		resp, _ := params["response"].(string)
		userInput, _ := params["user_input"].(string)
		text, added := n.Service.AddBackChanneling(resp, userInput)
		result = map[string]interface{}{
			"response_with_back_channeling": text,
			"added": added,
		}
	}

	// Publish result
	n.Bus.Publish(bus.Message{
		Topic:   "tasks.result",
		Payload: map[string]interface{}{
			"task_id": taskID,
			"success": success,
			"result":  result,
		},
	})
}
