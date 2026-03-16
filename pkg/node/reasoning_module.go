package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ReasoningModule handles deep thinking natively in Go
type ReasoningModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	CoT        *service.CoTReasoningService
	ToT        *service.ToTReasoningService
	MCTS       *service.MCTSReasoningService
}

func NewReasoningModule(swarmBus *bus.SwarmBus, cot *service.CoTReasoningService, tot *service.ToTReasoningService, mcts *service.MCTSReasoningService) *ReasoningModule {
	return &ReasoningModule{
		ID:         "go_native_reasoning",
		ModuleName: "reasoning_engine",
		Operations: []string{"chain_of_thought", "tree_of_thought", "mcts_reasoning"},
		Bus:        swarmBus,
		CoT:        cot,
		ToT:        tot,
		MCTS:       mcts,
	}
}

func (m *ReasoningModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[ReasoningModule] %s started and listening for deep thinking tasks.", m.ModuleName)
}

func (m *ReasoningModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	supported := false
	for _, op := range m.Operations {
		if op == operation {
			supported = true
			break
		}
	}

	if !supported {
		return
	}

	taskID, _ := msg.Payload["task_id"].(string)

	bidPayload := map[string]interface{}{
		"task_id":      taskID,
		"operation":     operation,
		"confidence":    1.0,
		"compute_cost":  5, // Thinking has some cost
		"node_id":       m.ID,
		"module_name":   m.ModuleName,
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     bidPayload,
	})
}

func (m *ReasoningModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[ReasoningModule] Executing native %s for task %s", operation, taskID)

	var result interface{}
	var err error

	query, _ := params["query"].(string)
	if query == "" {
		query, _ = params["input"].(string)
	}

	switch operation {
	case "chain_of_thought":
		result, err = m.CoT.Reason(query)
	case "tree_of_thought":
		result, err = m.ToT.Reason(query)
	case "mcts_reasoning":
		result, err = m.MCTS.Reason(query)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{
			Protocol:    bus.ERROR,
			Topic:       fmt.Sprintf("tasks.error.%s", taskID),
			SenderID:    m.ID,
			RecipientID: msg.SenderID,
			Payload:     map[string]interface{}{"error": err.Error(), "task_id": taskID},
		})
		return
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}
