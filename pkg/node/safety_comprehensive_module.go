package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ComprehensiveSafetyModule handles professional advice and code safety audits in Go
type ComprehensiveSafetyModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	ProService *service.ProfessionalSafetyService
	CodeService *service.CodeSafetyService
}

func NewComprehensiveSafetyModule(swarmBus *bus.SwarmBus, pro *service.ProfessionalSafetyService, code *service.CodeSafetyService) *ComprehensiveSafetyModule {
	return &ComprehensiveSafetyModule{
		ID:         "go_native_safety_v2",
		ModuleName: "comprehensive_safety",
		Operations: []string{"check_professional_advice", "check_code_safety", "detect_dangerous_topics"},
		Bus:        swarmBus,
		ProService: pro,
		CodeService: code,
	}
}

func (m *ComprehensiveSafetyModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[SafetyModule] %s (Comprehensive) started and listening for safety tasks.", m.ModuleName)
}

func (m *ComprehensiveSafetyModule) onCFP(msg bus.Message) {
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
		"compute_cost":  -1000, // Safety must always win
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

func (m *ComprehensiveSafetyModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[SafetyModule] Executing native comprehensive safety %s for task %s", operation, taskID)

	var result interface{}

	switch operation {
	case "check_professional_advice", "detect_dangerous_topics":
		text, _ := params["input"].(string)
		if text == "" {
			text, _ = params["text"].(string)
		}
		detected, adviceType, message := m.ProService.Check(text)
		result = map[string]interface{}{
			"detected":    detected,
			"advice_type": adviceType,
			"message":     message,
		}
	case "check_code_safety":
		code, _ := params["code"].(string)
		issues := m.CodeService.Analyze(code)
		result = map[string]interface{}{
			"issues": issues,
			"count":  len(issues),
			"safe":   len(issues) == 0,
		}
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}
