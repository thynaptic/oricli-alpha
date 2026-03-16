package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type CodeToCodeModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.CodeEngineService
}

func NewCodeToCodeModule(swarmBus *bus.SwarmBus, svc *service.CodeEngineService) *CodeToCodeModule {
	return &CodeToCodeModule{
		ID:         "go_native_code_to_code",
		ModuleName: "code_to_code_reasoning",
		Operations: []string{
			"relate_code",
			"compare_code",
			"trace_code_evolution",
			"map_to_requirements",
			"find_code_dependencies",
			"find_similar_code",
		},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *CodeToCodeModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[CodeToCodeModule] %s started and listening for code-relationship tasks.", m.ModuleName)
}

func (m *CodeToCodeModule) onCFP(msg bus.Message) {
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
			"compute_cost": 1, // Fast native code analysis
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *CodeToCodeModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "relate_code":
		result, err = m.Service.RelateCode(params)
	case "compare_code":
		result, err = m.Service.CompareCode(params)
	case "trace_code_evolution":
		result, err = m.Service.TraceCodeEvolution(params)
	case "map_to_requirements":
		result, err = m.Service.MapToRequirements(params)
	case "find_code_dependencies":
		result, err = m.Service.FindCodeDependencies(params)
	case "find_similar_code":
		result, err = m.Service.FindSimilarCode(params)
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
