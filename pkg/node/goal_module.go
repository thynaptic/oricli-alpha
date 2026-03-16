package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// GoalModule handles goal persistence and orchestration natively in Go
type GoalModule struct {
	ID          string
	ModuleName  string
	Operations  []string
	Bus         *bus.SwarmBus
	GoalService *service.GoalService
}

func NewGoalModule(swarmBus *bus.SwarmBus, svc *service.GoalService) *GoalModule {
	return &GoalModule{
		ID:         "go_native_goal",
		ModuleName: "goal_service",
		Operations: []string{"add_objective", "list_objectives", "update_objective"},
		Bus:        swarmBus,
		GoalService: svc,
	}
}

func (m *GoalModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[GoalModule] %s started and listening for executive tasks.", m.ModuleName)
}

func (m *GoalModule) onCFP(msg bus.Message) {
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

func (m *GoalModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[GoalModule] Executing native %s for task %s", operation, taskID)

	var result interface{}
	var err error

	switch operation {
	case "add_objective":
		goal, _ := params["goal"].(string)
		priority := 1
		if p, ok := params["priority"].(float64); ok {
			priority = int(p)
		}
		meta, _ := params["metadata"].(map[string]interface{})
		result, err = m.GoalService.AddObjective(goal, priority, meta)
	case "list_objectives":
		status, _ := params["status"].(string)
		result, err = m.GoalService.ListObjectives(status)
	case "update_objective":
		id, _ := params["id"].(string)
		updates, _ := params["updates"].(map[string]interface{})
		result, err = m.GoalService.UpdateObjective(id, updates)
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
