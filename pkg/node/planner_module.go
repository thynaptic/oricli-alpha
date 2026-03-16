package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// PlannerModule handles structured planning and DAG execution in Go
type PlannerModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Planner    *service.PlannerService
}

func NewPlannerModule(swarmBus *bus.SwarmBus, p *service.PlannerService) *PlannerModule {
	return &PlannerModule{
		ID:         "go_native_planner",
		ModuleName: "tool_calling_plan_service",
		Operations: []string{"create_plan", "execute_plan", "should_create_plan"},
		Bus:        swarmBus,
		Planner:    p,
	}
}

func (m *PlannerModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[PlannerModule] %s started and listening for strategy tasks.", m.ModuleName)
}

func (m *PlannerModule) onCFP(msg bus.Message) {
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

func (m *PlannerModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[PlannerModule] Executing native strategy %s for task %s", operation, taskID)

	var result interface{}
	var err error

	switch operation {
	case "should_create_plan":
		query, _ := params["query"].(string)
		// Basic logic for now
		result = map[string]bool{"should_plan": len(query) > 50}
	case "create_plan":
		query, _ := params["query"].(string)
		result, err = m.Planner.CreatePlan(query)
	case "execute_plan":
		// This would need to decode the plan from params
		log.Println("[PlannerModule] execute_plan called (logic pending full serialization)")
		result = map[string]string{"status": "pending_implementation"}
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
