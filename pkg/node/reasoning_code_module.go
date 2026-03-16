package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type ReasoningCodeModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.CodeEngineService
}

func NewReasoningCodeModule(swarmBus *bus.SwarmBus, svc *service.CodeEngineService) *ReasoningCodeModule {
	return &ReasoningCodeModule{
		ID:         "go_native_reasoning_code",
		ModuleName: "reasoning_code_generator",
		Operations: []string{
			"generate_code_reasoning",
			"explore_code_paths",
			"generate_with_verification",
			"refine_code",
			"generate_with_context",
		},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *ReasoningCodeModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[ReasoningCodeModule] %s started and listening for heavy code-generation tasks.", m.ModuleName)
}

func (m *ReasoningCodeModule) onCFP(msg bus.Message) {
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
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"operation":    operation,
			"confidence":   1.0,
			"compute_cost": 2, // Slightly higher cost due to LLM calls
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *ReasoningCodeModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "generate_code_reasoning":
		result, err = m.Service.GenerateCodeReasoning(params)
	case "explore_code_paths":
		result, err = m.Service.ExploreCodePaths(params)
	case "generate_with_verification":
		result, err = m.Service.GenerateWithVerification(params)
	case "refine_code":
		result, err = m.Service.RefineCode(params)
	case "generate_with_context":
		result, err = m.Service.GenerateWithContext(params)
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
