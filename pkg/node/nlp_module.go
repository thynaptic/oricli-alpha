package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// NLPModule handles high-speed linguistic analysis natively in Go
type NLPModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.NLPService
}

func NewNLPModule(swarmBus *bus.SwarmBus, svc *service.NLPService) *NLPModule {
	return &NLPModule{
		ID:         "go_native_nlp",
		ModuleName: "advanced_nlp",
		Operations: []string{"analyze_sentiment", "calculate_similarity"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *NLPModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[NLPModule] %s started and listening for linguistic tasks.", m.ModuleName)
}

func (m *NLPModule) onCFP(msg bus.Message) {
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

func (m *NLPModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[NLPModule] Executing native linguistic %s for task %s", operation, taskID)

	var result interface{}

	switch operation {
	case "analyze_sentiment":
		text, _ := params["text"].(string)
		result = m.Service.AnalyzeSentiment(text)
	case "calculate_similarity":
		t1, _ := params["text1"].(string)
		t2, _ := params["text2"].(string)
		result = map[string]float64{"similarity": m.Service.CalculateSimilarity(t1, t2)}
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}
