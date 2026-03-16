package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type StateManagerModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.StateMemoryToolsService
}

func NewStateManagerModule(swarmBus *bus.SwarmBus, svc *service.StateMemoryToolsService) *StateManagerModule {
	return &StateManagerModule{
		ID:         "go_native_state_manager",
		ModuleName: "state_manager",
		Operations: []string{"get_state", "update_state", "transition_state", "merge_states", "get_state_history", "create_snapshot"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *StateManagerModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[StateManagerModule] %s started.", m.ModuleName)
}

func (m *StateManagerModule) onCFP(msg bus.Message) {
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
	m.Bus.Publish(bus.Message{Protocol: bus.BID, Topic: fmt.Sprintf("tasks.bid.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"task_id": taskID, "operation": operation, "confidence": 1.0, "compute_cost": 1, "node_id": m.ID, "module_name": m.ModuleName}})
}

func (m *StateManagerModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "get_state":
		result, err = m.Service.GetState(params)
	case "update_state":
		result, err = m.Service.UpdateState(params)
	case "transition_state":
		result, err = m.Service.TransitionState(params)
	case "merge_states":
		result, err = m.Service.MergeStates(params)
	case "get_state_history":
		result, err = m.Service.GetStateHistory(params)
	case "create_snapshot":
		result, err = m.Service.CreateSnapshot(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}
	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}

// --- MEMORY TOOL ---

type MemoryToolModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.StateMemoryToolsService
}

func NewMemoryToolModule(swarmBus *bus.SwarmBus, svc *service.StateMemoryToolsService) *MemoryToolModule {
	return &MemoryToolModule{
		ID:         "go_native_memory_tool",
		ModuleName: "memory_tool",
		Operations: []string{"view", "create", "str_replace", "insert", "delete", "rename"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *MemoryToolModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[MemoryToolModule] %s started.", m.ModuleName)
}

func (m *MemoryToolModule) onCFP(msg bus.Message) {
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
	m.Bus.Publish(bus.Message{Protocol: bus.BID, Topic: fmt.Sprintf("tasks.bid.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"task_id": taskID, "operation": operation, "confidence": 1.0, "compute_cost": 1, "node_id": m.ID, "module_name": m.ModuleName}})
}

func (m *MemoryToolModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "view":
		result, err = m.Service.View(params)
	case "create":
		result, err = m.Service.Create(params)
	case "str_replace":
		result, err = m.Service.StrReplace(params)
	case "insert":
		result, err = m.Service.Insert(params)
	case "delete":
		result, err = m.Service.Delete(params)
	case "rename":
		result, err = m.Service.Rename(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}
	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}
