package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// SafetyModule handles adversarial auditing and prompt injection safety in Go
type SafetyModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.SafetyService
}

func NewSafetyModule(swarmBus *bus.SwarmBus, svc *service.SafetyService) *SafetyModule {
	return &SafetyModule{
		ID:         "go_native_safety",
		ModuleName: "safety_sentinel", // Combined adversarial_auditor and prompt_injection_safety
		Operations: []string{"audit_plan", "check_input", "detect_prompt_injection", "check_response"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *SafetyModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[SafetyModule] %s started and listening for safety tasks.", m.ModuleName)
}

func (m *SafetyModule) onCFP(msg bus.Message) {
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

	// Safety is the HIGHEST priority
	bidPayload := map[string]interface{}{
		"task_id":      taskID,
		"operation":     operation,
		"confidence":    1.0,
		"compute_cost":  -100, // Safety checks must always win and run first
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

func (m *SafetyModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[SafetyModule] Executing native %s for task %s", operation, taskID)

	var result interface{}

	switch operation {
	case "audit_plan":
		text, _ := params["text"].(string)
		result = m.Service.AuditPlan(text)
	case "check_input", "detect_prompt_injection":
		text, _ := params["input"].(string)
		if text == "" {
			text, _ = params["text"].(string)
		}
		detected, patterns := m.Service.DetectInjection(text)
		result = map[string]interface{}{
			"detected":          detected,
			"detected_patterns": patterns,
			"confidence":        1.0,
		}
	case "check_response":
		text, _ := params["response"].(string)
		detected, _ := m.Service.DetectInjection(text) // Re-use for leakage
		result = map[string]bool{"is_safe": !detected}
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}
