package node

import (
	"context"
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/oracle"
)

// VisionModule handles image-to-text and visual reasoning tasks via Oracle vision.
type VisionModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
}

func NewVisionModule(swarmBus *bus.SwarmBus) *VisionModule {
	return &VisionModule{
		ID:         "go_native_vision",
		ModuleName: "vision_agent",
		Operations: []string{"describe_image", "analyze_visuals"},
		Bus:        swarmBus,
	}
}

func (m *VisionModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[VisionModule] %s started and listening for visual tasks.", m.ModuleName)
}

func (m *VisionModule) onCFP(msg bus.Message) {
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
	m.Bus.Publish(bus.Message{
		Protocol: bus.BID,
		Topic:    fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID: m.ID,
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"operation":    operation,
			"confidence":   1.0,
			"compute_cost": 0.5,
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *VisionModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[VisionModule] Executing visual task: %s", taskID)

	var imageB64 string
	if img, ok := params["image"].(string); ok {
		imageB64 = img
	} else if imgs, ok := params["images"].([]interface{}); ok && len(imgs) > 0 {
		imageB64, _ = imgs[0].(string)
	}

	prompt, _ := params["prompt"].(string)
	if prompt == "" {
		prompt = "Describe this image in detail for a knowledge graph."
	}

	result, err := oracle.AnalyzeImage(context.Background(), prompt, imageB64, "image/png")
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
