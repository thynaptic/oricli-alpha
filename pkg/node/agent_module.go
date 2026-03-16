package node

import (
	"fmt"
	"log"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// AgentModule handles agent fleet coordination natively in Go
type AgentModule struct {
	ID          string
	ModuleName  string
	Operations  []string
	Bus         *bus.SwarmBus
	Coordinator *service.AgentCoordinator
}

func NewAgentModule(swarmBus *bus.SwarmBus, coord *service.AgentCoordinator) *AgentModule {
	return &AgentModule{
		ID:          "go_native_coordinator",
		ModuleName:  "agent_coordinator",
		Operations:  []string{"execute_task", "execute_parallel", "status"},
		Bus:         swarmBus,
		Coordinator: coord,
	}
}

func (m *AgentModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[AgentModule] %s started and listening for fleet tasks.", m.ModuleName)
}

func (m *AgentModule) onCFP(msg bus.Message) {
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

func (m *AgentModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[AgentModule] Executing native %s for task %s", operation, taskID)

	var result interface{}
	var err error

	switch operation {
	case "execute_task":
		taskData, _ := params["task"].(map[string]interface{})
		task := service.AgentTask{
			ID:        taskData["id"].(string),
			AgentType: service.AgentType(taskData["agent_type"].(string)),
			Query:     taskData["query"].(string),
			Context:   taskData["context"].(map[string]interface{}),
		}
		result, err = m.Coordinator.ExecuteTask(task, 60*time.Second)
	case "execute_parallel":
		tasksData, _ := params["tasks"].([]interface{})
		var tasks []service.AgentTask
		for _, td := range tasksData {
			tObj := td.(map[string]interface{})
			tasks = append(tasks, service.AgentTask{
				ID:        tObj["id"].(string),
				AgentType: service.AgentType(tObj["agent_type"].(string)),
				Query:     tObj["query"].(string),
				Context:   tObj["context"].(map[string]interface{}),
			})
		}
		result = m.Coordinator.ExecuteParallel(tasks, 60*time.Second)
	case "status":
		result = map[string]string{"status": "active", "coordinator": "go_native"}
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
