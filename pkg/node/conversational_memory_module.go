package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type ConversationalMemoryModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.MemoryPipelineService
}

func NewConversationalMemoryModule(swarmBus *bus.SwarmBus, svc *service.MemoryPipelineService) *ConversationalMemoryModule {
	return &ConversationalMemoryModule{
		ID:         "go_native_conv_memory",
		ModuleName: "conversational_memory",
		Operations: []string{"remember_context", "get_reference", "build_on_previous", "track_topic_continuity", "natural_reference"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *ConversationalMemoryModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[ConversationalMemory] %s started and listening for fast context operations.", m.ModuleName)
}

func (m *ConversationalMemoryModule) onCFP(msg bus.Message) {
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
		"operation":    operation,
		"confidence":   1.0, 
		"compute_cost": 1,   
		"node_id":      m.ID,
		"module_name":  m.ModuleName,
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     bidPayload,
	})
}

func (m *ConversationalMemoryModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "remember_context":
		result, err = m.Service.RememberContext(params)
	case "get_reference":
		result, err = m.Service.GetReference(params)
	case "build_on_previous":
		result, err = m.Service.BuildOnPrevious(params)
	case "track_topic_continuity":
		result, err = m.Service.TrackTopicContinuity(params)
	case "natural_reference":
		result, err = m.Service.NaturalReference(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
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
