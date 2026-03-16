package node

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ToolModule handles tool execution and management natively in Go
type ToolModule struct {
	ID          string
	ModuleName  string
	Operations  []string
	Bus         *bus.SwarmBus
	ToolService *service.ToolService
}

func NewToolModule(swarmBus *bus.SwarmBus, svc *service.ToolService) *ToolModule {
	return &ToolModule{
		ID:         "go_native_tool_master",
		ModuleName: "tool_execution_service", // Match Python name for compatibility
		Operations: []string{"execute_tool", "execute_tools_parallel", "list_tools", "register_tool"},
		Bus:        swarmBus,
		ToolService: svc,
	}
}

func (m *ToolModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[ToolModule] %s started and listening for tool tasks.", m.ModuleName)
}

func (m *ToolModule) onCFP(msg bus.Message) {
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

func (m *ToolModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[ToolModule] Executing native tool operation %s for task %s", operation, taskID)

	var result interface{}
	var err error

	switch operation {
	case "execute_tool":
		name, _ := params["name"].(string)
		args, _ := params["arguments"].(map[string]interface{})
		result, err = m.ToolService.ExecuteTool(context.Background(), name, args)
	case "list_tools":
		result = m.ToolService.ListTools()
	case "register_tool":
		var t service.Tool
		data, _ := json.Marshal(params["tool"])
		json.Unmarshal(data, &t)
		m.ToolService.RegisterTool(t)
		result = map[string]bool{"success": true}
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
