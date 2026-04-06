package node

import (
	"context"
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type BrowserModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Module     *service.BrowserAutomationModule
}

func NewBrowserModule(swarmBus *bus.SwarmBus, module *service.BrowserAutomationModule) *BrowserModule {
	return &BrowserModule{
		ID:         "go_native_browser",
		ModuleName: "browser_automation_service",
		Operations: []string{
			"health_check",
			"browser_health",
			"browser_create_session",
			"browser_open",
			"browser_snapshot",
			"browser_action",
			"browser_screenshot",
			"browser_save_state",
			"browser_load_state",
			"browser_close",
		},
		Bus:    swarmBus,
		Module: module,
	}
}

func (m *BrowserModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[BrowserModule] %s started and listening for browser tasks.", m.ModuleName)
}

func (m *BrowserModule) onCFP(msg bus.Message) {
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
			"confidence":   0.98,
			"compute_cost": 0.15,
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *BrowserModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[BrowserModule] Executing %s for task %s", operation, taskID)
	result, err := m.Module.Execute(context.Background(), operation, params)
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
