package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// MemoryGraphModule handles advanced knowledge mapping natively in Go
type MemoryGraphModule struct {
	ID           string
	ModuleName   string
	Operations   []string
	Bus          *bus.SwarmBus
	Service      *service.MemoryGraphService
}

func NewMemoryGraphModule(swarmBus *bus.SwarmBus, svc *service.MemoryGraphService) *MemoryGraphModule {
	return &MemoryGraphModule{
		ID:         "go_native_memory_graph",
		ModuleName: "memory_graph",
		Operations: []string{"add_node", "add_edge", "traverse_memory", "recall_memories"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *MemoryGraphModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[MemoryGraphModule] %s started and listening for knowledge graph tasks.", m.ModuleName)
}

func (m *MemoryGraphModule) onCFP(msg bus.Message) {
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

func (m *MemoryGraphModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[MemoryGraphModule] Executing native knowledge graph %s for task %s", operation, taskID)

	var result interface{}
	var err error

	switch operation {
	case "add_node":
		node := &service.GraphNode{
			ID:      params["id"].(string),
			Content: params["content"].(string),
			Type:    params["type"].(string),
		}
		m.Service.AddNode(node)
		result = map[string]bool{"success": true}
	case "add_edge":
		edge := &service.GraphEdge{
			Source:   params["source"].(string),
			Target:   params["target"].(string),
			Type:     params["type"].(string),
			Strength: 1.0,
		}
		if s, ok := params["strength"].(float64); ok { edge.Strength = s }
		m.Service.AddEdge(edge)
		result = map[string]bool{"success": true}
	case "traverse_memory":
		id, _ := params["start_id"].(string)
		hops := 3
		if h, ok := params["max_hops"].(float64); ok { hops = int(h) }
		result = m.Service.Traverse(id, hops)
	case "recall_memories":
		query, _ := params["query"].(string)
		limit := 5
		if l, ok := params["limit"].(float64); ok { limit = int(l) }
		result, err = m.Service.SemanticSearch(query, limit)
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
