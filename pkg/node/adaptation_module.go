package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// AdaptationModule handles behavioral tracking and adapter routing natively in Go
type AdaptationModule struct {
	ID              string
	ModuleName      string
	Operations      []string
	Bus             *bus.SwarmBus
	AdaptSvc        *service.AdaptationService
	RouterSvc       *service.AdapterRouterService
}

func NewAdaptationModule(swarmBus *bus.SwarmBus, adapt *service.AdaptationService, router *service.AdapterRouterService) *AdaptationModule {
	return &AdaptationModule{
		ID:         "go_native_adaptation_engine",
		ModuleName: "adaptation_tracker", // Combined for Go speed
		Operations: []string{"analyze_adaptation", "route_input", "apply_routing", "adapter_status"},
		Bus:        swarmBus,
		AdaptSvc:   adapt,
		RouterSvc:  router,
	}
}

func (m *AdaptationModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[AdaptationModule] %s started and listening for behavioral tasks.", m.ModuleName)
}

func (m *AdaptationModule) onCFP(msg bus.Message) {
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

func (m *AdaptationModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[AdaptationModule] Executing native adaptation/routing %s for task %s", operation, taskID)

	var result interface{}
	var err error

	switch operation {
	case "analyze_adaptation":
		historyData, _ := params["conversation_history"].([]interface{})
		var history []string
		for _, h := range historyData {
			if s, ok := h.(string); ok { history = append(history, s) }
		}
		result = m.AdaptSvc.Analyze(history)
	case "route_input":
		text, _ := params["text"].(string)
		intent, adapter, conf := m.RouterSvc.RouteInput(text)
		result = map[string]interface{}{
			"intent":     intent,
			"adapter_id": adapter,
			"confidence": conf,
		}
	case "apply_routing":
		adapterID, _ := params["adapter_id"].(string)
		success, routerErr := m.RouterSvc.ApplyRouting(adapterID)
		result = map[string]bool{"success": success}
		err = routerErr
	case "adapter_status":
		result = m.RouterSvc.ActiveAdapters
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
