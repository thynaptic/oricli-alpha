package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// SubconsciousModule handles the persistent mental state in Go
type SubconsciousModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.SubconsciousService
}

func NewSubconsciousModule(swarmBus *bus.SwarmBus, svc *service.SubconsciousService) *SubconsciousModule {
	return &SubconsciousModule{
		ID:         "go_native_subconscious",
		ModuleName: "subconscious_field",
		Operations: []string{"vibrate", "get_mental_state", "clear_field"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *SubconsciousModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[SubconsciousModule] %s started and listening for neural bias tasks.", m.ModuleName)
}

func (m *SubconsciousModule) onCFP(msg bus.Message) {
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

func (m *SubconsciousModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[SubconsciousModule] Executing native neural bias %s for task %s", operation, taskID)

	var result interface{}

	switch operation {
	case "vibrate":
		vectorData, _ := params["vector"].([]interface{})
		var vector []float32
		for _, v := range vectorData {
			if f, ok := v.(float64); ok { vector = append(vector, float32(f)) }
		}
		weight := 1.0
		if w, ok := params["weight"].(float64); ok { weight = w }
		source, _ := params["source"].(string)
		
		m.Service.Vibrate(vector, weight, source)
		result = map[string]bool{"success": true}
	case "get_mental_state":
		state, count := m.Service.GetMentalState()
		result = map[string]interface{}{
			"mental_state":    state,
			"vibration_count": count,
		}
	case "clear_field":
		m.Service.Buffer = nil
		m.Service.MentalState = nil
		m.Service.Save()
		result = map[string]bool{"success": true}
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}
