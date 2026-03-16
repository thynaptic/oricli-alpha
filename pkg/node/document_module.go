package node

import (
	"context"
	"fmt"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// DocumentModule provides document analysis and ranking via the Swarm Bus
type DocumentModule struct {
	Bus     *bus.SwarmBus
	Service *service.DocumentService
	ID      string
}

// NewDocumentModule creates a new document module
func NewDocumentModule(swarmBus *bus.SwarmBus, svc *service.DocumentService) *DocumentModule {
	return &DocumentModule{
		Bus:     swarmBus,
		Service: svc,
		ID:      "document_service",
	}
}

// Start initiates the subscription to the bus
func (n *DocumentModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *DocumentModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok { return }

	supportedOps := map[string]bool{
		"analyze_document":   true,
		"summarize_document": true,
		"rank_documents":     true,
	}

	if !supportedOps[operation] { return }

	taskID, _ := msg.Payload["task_id"].(string)

	n.Bus.Publish(bus.Message{
		Protocol: bus.BID,
		Topic:    fmt.Sprintf("tasks.bid.%s", taskID),
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"agent_id":     n.ID,
			"compute_cost": 0.25,
			"confidence":   1.0,
		},
	})
}

func (n *DocumentModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})
	operation, _ := msg.Payload["operation"].(string)

	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	var result interface{}
	var err error

	switch operation {
	case "analyze_document":
		text, _ := params["text"].(string)
		fileName, _ := params["file_name"].(string)
		result, err = n.Service.AnalyzeDocument(ctx, text, fileName)
	case "summarize_document":
		text, _ := params["text"].(string)
		maxSents := int(service.ToFloat64(params["max_sentences"]))
		if maxSents == 0 { maxSents = 3 }
		result, err = n.Service.SummarizeDocument(ctx, text, maxSents)
	case "rank_documents":
		query, _ := params["query"].(string)
		docsRaw, _ := params["documents"].([]interface{})
		docs := make([]map[string]interface{}, len(docsRaw))
		for i, d := range docsRaw {
			docs[i], _ = d.(map[string]interface{})
		}
		result = n.Service.RankDocuments(query, docs)
	}

	resPayload := map[string]interface{}{
		"task_id": taskID,
		"success": err == nil,
	}
	if err != nil {
		resPayload["error"] = err.Error()
	} else {
		resPayload["result"] = result
	}

	var protocol bus.Protocol
	if err != nil {
		protocol = bus.ERROR
	} else {
		protocol = bus.RESULT
	}

	n.Bus.Publish(bus.Message{
		Protocol: protocol,
		Topic:    "tasks.result",
		Payload:  resPayload,
	})
}
