package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type TemporalModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.TemporalService
}

func NewTemporalModule(swarmBus *bus.SwarmBus, svc *service.TemporalService) *TemporalModule {
	return &TemporalModule{
		ID:         "go_native_temporal",
		ModuleName: "chronos_agent",
		Operations: []string{"record_event", "get_history"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *TemporalModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[TemporalModule] %s active. Chronological grounding online.", m.ModuleName)
}

func (m *TemporalModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok { return }

	supported := false
	for _, op := range m.Operations {
		if op == operation {
			supported = true
			break
		}
	}

	if !supported { return }

	taskID, _ := msg.Payload["task_id"].(string)

	m.Bus.Publish(bus.Message{
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    m.ID,
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"operation":     operation,
			"confidence":    1.0,
			"compute_cost":  0.1,
			"node_id":       m.ID,
			"module_name":   m.ModuleName,
		},
	})
}

func (m *TemporalModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result interface{}
	var err error

	switch operation {
	case "record_event":
		eType, _ := params["type"].(string)
		desc, _ := params["description"].(string)
		meta, _ := params["metadata"].(map[string]interface{})
		result, err = m.Service.RecordEvent(eType, desc, meta)
		
	case "get_history":
		limit := 10
		if val, ok := params["limit"].(float64); ok {
			limit = int(val)
		}
		result, err = m.Service.GetRecentHistory(limit)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{
			Protocol: bus.ERROR,
			Topic:    fmt.Sprintf("tasks.error.%s", taskID),
			SenderID: m.ID,
			Payload:  map[string]interface{}{"error": err.Error(), "task_id": taskID},
		})
		return
	}

	m.Bus.Publish(bus.Message{
		Protocol: bus.RESULT,
		Topic:    "tasks.result",
		SenderID: m.ID,
		Payload:  map[string]interface{}{"result": result, "task_id": taskID},
	})
}
