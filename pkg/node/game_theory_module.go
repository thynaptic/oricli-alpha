package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// GameTheoryModule handles symbolic game theory calculations natively in Go
type GameTheoryModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.GameTheoryService
}

func NewGameTheoryModule(swarmBus *bus.SwarmBus, svc *service.GameTheoryService) *GameTheoryModule {
	return &GameTheoryModule{
		ID:         "go_native_game_theory",
		ModuleName: "game_theory_solver",
		Operations: []string{"solve_game", "best_response", "analyze_scenario"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *GameTheoryModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[GameTheoryModule] %s started and listening for symbolic math tasks.", m.ModuleName)
}

func (m *GameTheoryModule) onCFP(msg bus.Message) {
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
		"operation":    operation,
		"confidence":   1.0, // Native Go is highly confident in pure math
		"compute_cost": 1,   // Extremely cheap in Go
		"node_id":      m.ID,
		"module_name":  m.ModuleName,
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     bidPayload,
	})
}

func (m *GameTheoryModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "solve_game":
		result, err = m.Service.SolveGame(params)
	case "best_response":
		result, err = m.Service.BestResponse(params)
	case "analyze_scenario":
		result, err = m.Service.AnalyzeScenario(params)
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
