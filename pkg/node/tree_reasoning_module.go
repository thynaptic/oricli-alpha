package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type TreeReasoningModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	MCTS       *service.MCTSReasoningService
	ToT        *service.ToTReasoningService
}

func NewTreeReasoningModule(swarmBus *bus.SwarmBus, mcts *service.MCTSReasoningService, tot *service.ToTReasoningService) *TreeReasoningModule {
	return &TreeReasoningModule{
		ID:         "go_native_tree_reasoning",
		ModuleName: "mcts_search_engine", // Claiming the Python module name
		Operations: []string{
			"search",              // Standard MCTS search
			"mcts_search",         // Explicit MCTS
			"tot_search",          // Tree of Thoughts search
			"reason",              // Generic reasoning entrypoint
			"evaluate_thought",    // Sub-operation for evaluation
			"execute_mcts",
			"analyze_mcts_complexity",
			"should_activate",
			"format_reasoning_output",
		},
		Bus:  swarmBus,
		MCTS: mcts,
		ToT:  tot,
	}
}

func (m *TreeReasoningModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[TreeReasoningModule] %s started. 32-core parallel MCTS/ToT online.", m.ModuleName)
}

func (m *TreeReasoningModule) onCFP(msg bus.Message) {
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

	m.Bus.Publish(bus.Message{
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"operation":    operation,
			"confidence":   1.0,
			"compute_cost": 5.0, // High compute cost due to parallel rollouts
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *TreeReasoningModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result interface{}
	var err error

	query, _ := params["query"].(string)
	if query == "" {
		query, _ = params["input"].(string)
	}

	switch operation {
	case "search", "mcts_search", "reason", "execute_mcts":
		// Execute parallel Monte-Carlo Tree Search
		result, err = m.MCTS.Reason(query)
	case "tot_search":
		// Execute parallel Tree of Thoughts Search
		result, err = m.ToT.Reason(query)
	case "evaluate_thought":
		thought, _ := params["thought"].(string)
		// Quick native evaluation
		score, evalErr := m.MCTS.EvaluateThought(query, thought)
		result = map[string]interface{}{"score": score}
		err = evalErr
	case "analyze_mcts_complexity", "should_activate", "format_reasoning_output":
		// Provide basic heuristics native-speed
		result = map[string]interface{}{"success": true, "should_activate": true}
	default:
		err = fmt.Errorf("unknown operation %s", operation)
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
