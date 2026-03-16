package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type MemoryProcessorModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.MemoryPipelineService
}

func NewMemoryProcessorModule(swarmBus *bus.SwarmBus, svc *service.MemoryPipelineService) *MemoryProcessorModule {
	return &MemoryProcessorModule{
		ID:         "go_native_mem_processor",
		ModuleName: "memory_processor",
		Operations: []string{"process_memories", "clean_and_deduplicate", "cluster_memories", "extract_patterns", "detect_outliers"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *MemoryProcessorModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[MemoryProcessor] %s started and listening for fast data operations.", m.ModuleName)
}

func (m *MemoryProcessorModule) onCFP(msg bus.Message) {
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

func (m *MemoryProcessorModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "process_memories":
		result, err = m.Service.ProcessMemories(params)
	case "clean_and_deduplicate":
		result, err = m.Service.CleanAndDeduplicate(params)
	case "cluster_memories":
		result, err = m.Service.ClusterMemories(params)
	case "extract_patterns":
		result, err = m.Service.ExtractPatterns(params)
	case "detect_outliers":
		result, err = m.Service.DetectOutliers(params)
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
