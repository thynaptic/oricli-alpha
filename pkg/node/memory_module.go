package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// MemoryModule wraps the MemoryBridge for the Go Swarm
type MemoryModule struct {
	ID           string
	ModuleName   string
	Operations   []string
	Bus          *bus.SwarmBus
	MemoryBridge *service.MemoryBridge
}

func NewMemoryModule(swarmBus *bus.SwarmBus, mb *service.MemoryBridge) *MemoryModule {
	return &MemoryModule{
		ID:           "go_native_memory",
		ModuleName:   "memory_bridge",
		Operations:   []string{"put", "get", "vector_search", "list_ids"},
		Bus:          swarmBus,
		MemoryBridge: mb,
	}
}

func (m *MemoryModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[MemoryModule] %s started and listening for data tasks.", m.ModuleName)
}

func (m *MemoryModule) onCFP(msg bus.Message) {
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

	// Memory operations are extremely high priority in Go
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

func (m *MemoryModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[MemoryModule] Executing native %s for task %s", operation, taskID)

	var result interface{}
	var err error

	categoryStr, _ := params["category"].(string)
	category := service.MemoryCategory(categoryStr)

	switch operation {
	case "get":
		id, _ := params["id"].(string)
		result, err = m.MemoryBridge.Get(category, id)
	case "put":
		id, _ := params["id"].(string)
		data, _ := params["data"].(map[string]interface{})
		metadata, _ := params["metadata"].(map[string]interface{})
		err = m.MemoryBridge.Put(category, id, data, metadata)
		result = map[string]bool{"success": err == nil}
	case "vector_search":
		// Handle vector extraction from interface slice
		var queryVector []float32
		if v, ok := params["query_vector"].([]interface{}); ok {
			for _, val := range v {
				if f, ok := val.(float64); ok {
					queryVector = append(queryVector, float32(f))
				}
			}
		}
		topK := 10
		if k, ok := params["top_k"].(float64); ok {
			topK = int(k)
		}
		minScore := float32(0.0)
		if s, ok := params["min_score"].(float64); ok {
			minScore = float32(s)
		}
		result, err = m.MemoryBridge.VectorSearch(queryVector, topK, minScore)
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
