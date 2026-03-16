package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ComplexityModule handles query complexity analysis in Go
type ComplexityModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.ComplexityService
}

func NewComplexityModule(swarmBus *bus.SwarmBus, svc *service.ComplexityService) *ComplexityModule {
	return &ComplexityModule{
		ID:         "go_native_complexity",
		ModuleName: "complexity_detector",
		Operations: []string{"analyze_cot_complexity", "should_activate_cot", "analyze_tot_complexity"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *ComplexityModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[ComplexityModule] %s started and listening for analysis tasks.", m.ModuleName)
}

func (m *ComplexityModule) onCFP(msg bus.Message) {
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

func (m *ComplexityModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[ComplexityModule] Executing native %s for task %s", operation, taskID)

	var result interface{}
	query, _ := params["query"].(string)
	if query == "" {
		query, _ = params["input"].(string)
	}

	score := m.Service.Analyze(query)

	if operation == "should_activate_cot" {
		result = map[string]bool{"should_activate": score.RequiresCoT}
	} else {
		result = score
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}
