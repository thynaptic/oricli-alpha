package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// GraphModule wraps the GraphService for the Go Swarm
type GraphModule struct {
	ID           string
	ModuleName   string
	Operations   []string
	Bus          *bus.SwarmBus
	GraphService *service.GraphService
}

func NewGraphModule(swarmBus *bus.SwarmBus, gs *service.GraphService) *GraphModule {
	return &GraphModule{
		ID:           "go_native_graph",
		ModuleName:   "neo4j_service",
		Operations:   []string{"execute_query", "add_node", "add_relationship", "find_path", "get_neighbors"},
		Bus:          swarmBus,
		GraphService: gs,
	}
}

func (m *GraphModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[GraphModule] %s started and listening for graph tasks.", m.ModuleName)
}

func (m *GraphModule) onCFP(msg bus.Message) {
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

	// Graph operations are native and fast in Go
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

func (m *GraphModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[GraphModule] Executing native %s for task %s", operation, taskID)

	var result interface{}
	var err error

	switch operation {
	case "execute_query":
		query, _ := params["query"].(string)
		qParams, _ := params["parameters"].(map[string]interface{})
		result, err = m.GraphService.ExecuteQuery(query, qParams)
	case "add_node":
		label, _ := params["label"].(string)
		props, _ := params["properties"].(map[string]interface{})
		result, err = m.GraphService.AddNode(label, props)
	case "add_relationship":
		src, _ := params["source_id"].(string)
		tgt, _ := params["target_id"].(string)
		rel, _ := params["rel_type"].(string)
		props, _ := params["properties"].(map[string]interface{})
		result, err = m.GraphService.AddRelationship(src, tgt, rel, props)
	case "find_path":
		start, _ := params["start_id"].(string)
		end, _ := params["end_id"].(string)
		depth := 3
		if d, ok := params["max_depth"].(float64); ok {
			depth = int(d)
		}
		result, err = m.GraphService.FindPath(start, end, depth)
	case "get_neighbors":
		id, _ := params["node_id"].(string)
		depth := 1
		if d, ok := params["depth"].(float64); ok {
			depth = int(d)
		}
		result, err = m.GraphService.GetNeighbors(id, depth)
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
