package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// OrchestratorModule wraps the module management logic for the Go Hive
type OrchestratorModule struct {
	ID           string
	ModuleName   string
	Operations   []string
	Bus          *bus.SwarmBus
	Orchestrator *service.GoOrchestrator
}

func NewOrchestratorModule(swarmBus *bus.SwarmBus, orch *service.GoOrchestrator) *OrchestratorModule {
	return &OrchestratorModule{
		ID:           "go_native_orchestrator",
		ModuleName:   "module_orchestrator",
		Operations:   []string{"get_status", "get_load_order", "get_all_states"},
		Bus:          swarmBus,
		Orchestrator: orch,
	}
}

func (m *OrchestratorModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[OrchestratorModule] %s started and listening for lifecycle tasks.", m.ModuleName)
}

func (m *OrchestratorModule) onCFP(msg bus.Message) {
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

func (m *OrchestratorModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)

	log.Printf("[OrchestratorModule] Executing native management %s for task %s", operation, taskID)

	var result interface{}

	switch operation {
	case "get_status":
		result = map[string]string{
			"status": string(m.Orchestrator.Status),
			"broker": m.Orchestrator.BrokerID,
		}
	case "get_load_order":
		result = m.Orchestrator.LoadOrder
	case "get_all_states":
		result = map[string]string{"state": "operational"}
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}
