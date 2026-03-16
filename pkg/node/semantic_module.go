package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// SemanticModule handles high-level semantic analysis natively in Go
type SemanticModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	NLP        *service.NLPService
	Subfield   *service.SubconsciousService
}

func NewSemanticModule(swarmBus *bus.SwarmBus, nlp *service.NLPService, sub *service.SubconsciousService) *SemanticModule {
	return &SemanticModule{
		ID:         "go_native_semantic_engine",
		ModuleName: "semantic_search_service",
		Operations: []string{"calculate_similarity", "get_context_bias", "vibrate_field"},
		Bus:        swarmBus,
		NLP:        nlp,
		Subfield:   sub,
	}
}

func (m *SemanticModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[SemanticModule] %s started and listening for semantic tasks.", m.ModuleName)
}

func (m *SemanticModule) onCFP(msg bus.Message) {
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

func (m *SemanticModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[SemanticModule] Executing native semantic %s for task %s", operation, taskID)

	var result interface{}

	switch operation {
	case "calculate_similarity":
		t1, _ := params["text1"].(string)
		t2, _ := params["text2"].(string)
		result = map[string]float64{"similarity": m.NLP.CalculateSimilarity(t1, t2)}
	case "get_context_bias":
		state, count := m.Subfield.GetMentalState()
		result = map[string]interface{}{
			"bias_vector": state,
			"active":      count > 0,
		}
	case "vibrate_field":
		vectorData, _ := params["vector"].([]interface{})
		var vector []float32
		for _, v := range vectorData {
			if f, ok := v.(float64); ok { vector = append(vector, float32(f)) }
		}
		m.Subfield.Vibrate(vector, 1.0, "semantic_routing")
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
