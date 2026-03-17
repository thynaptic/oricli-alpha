package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// WebIngestionModule handles autonomous crawling and indexing
type WebIngestionModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.WebIngestionService
}

func NewWebIngestionModule(swarmBus *bus.SwarmBus, svc *service.WebIngestionService) *WebIngestionModule {
	return &WebIngestionModule{
		ID:         "go_native_web_ingest",
		ModuleName: "web_ingestion_agent",
		Operations: []string{"crawl_and_ingest"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *WebIngestionModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[WebIngestModule] %s started and listening for crawl tasks.", m.ModuleName)
}

func (m *WebIngestionModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok || operation != "crawl_and_ingest" {
		return
	}

	taskID, _ := msg.Payload["task_id"].(string)

	m.Bus.Publish(bus.Message{
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    m.ID,
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"operation":     operation,
			"confidence":    1.0,
			"compute_cost":  0.2,
			"node_id":       m.ID,
			"module_name":   m.ModuleName,
		},
	})
}

func (m *WebIngestionModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	url, _ := params["url"].(string)
	maxPages := 5
	if val, ok := params["max_pages"].(float64); ok {
		maxPages = int(val)
	}
	maxDepth := 2
	if val, ok := params["max_depth"].(float64); ok {
		maxDepth = int(val)
	}
	metadata, _ := params["metadata"].(map[string]interface{})

	log.Printf("[WebIngestModule] Starting native crawl: %s", url)
	result, err := m.Service.CrawlAndIngest(url, maxPages, maxDepth, metadata)

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
