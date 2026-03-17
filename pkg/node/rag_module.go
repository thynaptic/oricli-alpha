package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/rag"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// RagModule wraps the RagService for the Go Swarm
type RagModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	RagService *service.RagService
}

func NewRagModule(swarmBus *bus.SwarmBus, rs *service.RagService) *RagModule {
	return &RagModule{
		ID:         "go_native_rag",
		ModuleName: "ingestion_agent",
		Operations: []string{"ingest_text", "ingest_file", "chunk_text"},
		Bus:        swarmBus,
		RagService: rs,
	}
}

func (m *RagModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[RagModule] %s started and listening for ingestion tasks.", m.ModuleName)
}

func (m *RagModule) onCFP(msg bus.Message) {
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

	// Ingestion is a priority Go native task
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

func (m *RagModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[RagModule] Executing native %s for task %s", operation, taskID)

	var result interface{}
	var err error

	switch operation {
	case "ingest_text":
		text, _ := params["text"].(string)
		source, _ := params["source"].(string)
		metaRaw, _ := params["metadata"].(map[string]interface{})
		
		// Convert map[string]interface{} to map[string]string for P-LMv1 compatibility
		meta := make(map[string]string)
		for k, v := range metaRaw {
			meta[k] = fmt.Sprintf("%v", v)
		}
		
		err = m.RagService.IngestText(text, source, meta)
		result = map[string]interface{}{"success": err == nil, "error": fmt.Sprintf("%v", err)}
		
	case "ingest_file":
		// Handle direct file ingestion via P-LMv1 indexer
		path, _ := params["file_path"].(string)
		opts := rag.DefaultIndexOptions()
		
		stats, ingestErr := m.RagService.IngestFile(path, opts)
		result = stats
		err = ingestErr
		
	case "chunk_text":
		// Native Go chunking placeholder
		result = map[string]interface{}{"success": true, "count": 0}
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
