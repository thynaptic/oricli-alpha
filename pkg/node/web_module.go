package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// WebModule wraps the WebFetchService for the Go Swarm
type WebModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	WebService *service.WebFetchService
}

func NewWebModule(swarmBus *bus.SwarmBus, ws *service.WebFetchService) *WebModule {
	return &WebModule{
		ID:         "go_native_web",
		ModuleName: "web_fetch_service",
		Operations: []string{"fetch_url", "fetch_multiple"},
		Bus:        swarmBus,
		WebService: ws,
	}
}

func (m *WebModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[WebModule] %s started and listening for web ingestion tasks.", m.ModuleName)
}

func (m *WebModule) onCFP(msg bus.Message) {
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

	// Web ingestion is highly efficient in Go
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

func (m *WebModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[WebModule] Executing native %s for task %s", operation, taskID)

	var result interface{}

	switch operation {
	case "fetch_url":
		url, _ := params["url"].(string)
		result = m.WebService.FetchURL(url)
	case "fetch_multiple":
		var urls []string
		if u, ok := params["urls"].([]interface{}); ok {
			for _, val := range u {
				if s, ok := val.(string); ok {
					urls = append(urls, s)
				}
			}
		}
		result = m.WebService.FetchMultiple(urls)
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}
