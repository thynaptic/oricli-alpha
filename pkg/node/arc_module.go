package node

import (
	"encoding/json"
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type ARCModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	ARCSolver  *service.ARCSolver
}

func NewARCModule(swarmBus *bus.SwarmBus, solver *service.ARCSolver) *ARCModule {
	return &ARCModule{
		ID:         "go_native_arc",
		ModuleName: "arc_solver",
		Operations: []string{"solve_arc_problem", "solve_arc_task", "arc_solver"},
		Bus:        swarmBus,
		ARCSolver:  solver,
	}
}

func (m *ARCModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[ARCModule] %s started and listening for grid tasks.", m.ModuleName)
}

func (m *ARCModule) onCFP(msg bus.Message) {
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
		"compute_cost":  0,
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

func (m *ARCModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[ARCModule] Executing native %s for task %s", operation, taskID)

	var result interface{}

	// Convert raw JSON to ARCProblem
	var problem service.ARCProblem
	data, _ := json.Marshal(params["problem"])
	if err := json.Unmarshal(data, &problem); err == nil {
		solution, err := m.ARCSolver.Solve(problem)
		if err != nil {
			result = map[string]interface{}{"success": false, "error": err.Error()}
		} else {
			result = map[string]interface{}{"success": true, "grid": solution}
		}
	} else {
		result = map[string]interface{}{"success": false, "error": "Invalid ARC problem payload"}
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}
