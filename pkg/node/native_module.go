package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// NativeModule represents a high-performance Go-native module
type NativeModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	GenService *service.GenerationService
}

func NewNativeGenerationModule(swarmBus *bus.SwarmBus, genService *service.GenerationService) *NativeModule {
	return &NativeModule{
		ID:         "go_native_generation",
		ModuleName: "go_text_gen",
		Operations: []string{"generate", "chat", "generate_full_response"},
		Bus:        swarmBus,
		GenService: genService,
	}
}

func (n *NativeModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
	log.Printf("[NativeModule] %s started and listening for generation tasks.", n.ModuleName)
}

func (n *NativeModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	supported := false
	for _, op := range n.Operations {
		if op == operation {
			supported = true
			break
		}
	}

	if !supported {
		return
	}

	taskID, _ := msg.Payload["task_id"].(string)

	// Native modules bid with high confidence and zero compute cost
	bidPayload := map[string]interface{}{
		"task_id":      taskID,
		"operation":     operation,
		"confidence":    2.0, // Double the standard max
		"compute_cost":  -10, // Negative cost to prioritize
		"node_id":       n.ID,
		"module_name":   n.ModuleName,
	}

	n.Bus.Publish(bus.Message{
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    n.ID,
		RecipientID: msg.SenderID,
		Payload:     bidPayload,
	})
}

func (n *NativeModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[NativeModule] Executing native %s for task %s", operation, taskID)

	var result map[string]interface{}
	var err error

	if operation == "generate" || operation == "generate_full_response" {
		prompt, _ := params["prompt"].(string)
		if prompt == "" {
			prompt, _ = params["input"].(string)
		}
		// Try thoughts if it's coming from a reasoning result
		if prompt == "" {
			if thoughts, ok := params["thoughts"].([]interface{}); ok && len(thoughts) > 0 {
				prompt = fmt.Sprintf("%v", thoughts[0])
			}
		}
		// Try extracting from messages if it's a chat request proxied to generate
		if prompt == "" {
			if msgs, ok := params["messages"].([]interface{}); ok && len(msgs) > 0 {
				// Use the content of the last message
				lastMsg, ok := msgs[len(msgs)-1].(map[string]interface{})
				if ok {
					prompt, _ = lastMsg["content"].(string)
				}
			}
		}
		result, err = n.GenService.Generate(prompt, params)
	} else if operation == "chat" {
		// Convert generic params to messages
		messages := []map[string]string{}
		if msgs, ok := params["messages"].([]interface{}); ok {
			for _, m := range msgs {
				if mObj, ok := m.(map[string]interface{}); ok {
					messages = append(messages, map[string]string{
						"role":    mObj["role"].(string),
						"content": mObj["content"].(string),
					})
				}
			}
		}
		result, err = n.GenService.Chat(messages, params)
	}

	if err != nil {
		n.Bus.Publish(bus.Message{
			Protocol:    bus.ERROR,
			Topic:       fmt.Sprintf("tasks.error.%s", taskID),
			SenderID:    n.ID,
			RecipientID: msg.SenderID,
			Payload:     map[string]interface{}{"error": err.Error(), "task_id": taskID},
		})
		return
	}

	n.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    n.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}
