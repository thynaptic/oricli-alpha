package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// HolisticSafetyModule handles sensitive safety audits natively in Go
type HolisticSafetyModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.HolisticSafetyService
}

func NewHolisticSafetyModule(swarmBus *bus.SwarmBus, svc *service.HolisticSafetyService) *HolisticSafetyModule {
	return &HolisticSafetyModule{
		ID:         "go_native_heart",
		ModuleName: "holistic_safety", // The Heart of Oricli
		Operations: []string{"audit_safety", "check_distress", "get_crisis_resources"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *HolisticSafetyModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[SafetyModule] %s (The Heart) started and listening for sensitive tasks.", m.ModuleName)
}

func (m *HolisticSafetyModule) onCFP(msg bus.Message) {
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

	// Heart operations are absolute priority
	bidPayload := map[string]interface{}{
		"task_id":      taskID,
		"operation":     operation,
		"confidence":    1.0,
		"compute_cost":  -500, // Heart must always beat first
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

func (m *HolisticSafetyModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[SafetyModule] Executing native Heart operation %s for task %s", operation, taskID)

	var result interface{}

	switch operation {
	case "audit_safety", "check_distress":
		text, _ := params["input"].(string)
		if text == "" {
			text, _ = params["text"].(string)
		}
		auditRes := m.Service.Audit(text)
		result = auditRes
	case "get_crisis_resources":
		result = map[string]string{
			"US_Suicide_Lifeline": "988",
			"Crisis_Text_Line":    "741741",
			"Website":             "https://988lifeline.org",
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
