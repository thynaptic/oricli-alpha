package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type MetaEvaluatorModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.MetaEvaluatorService
}

func NewMetaEvaluatorModule(swarmBus *bus.SwarmBus, svc *service.MetaEvaluatorService) *MetaEvaluatorModule {
	return &MetaEvaluatorModule{
		ID:         "go_native_meta_evaluator",
		ModuleName: "meta_evaluator",
		Operations: []string{
			"evaluate_and_repair",
			"check_structure",
			"repair_formatting",
			"align_answers",
			"remove_disclaimers",
			"close_tags",
			// Claiming regulatory auditor's fast operations
			"check_compliance",
			"get_active_frameworks",
		},
		Bus:     swarmBus,
		Service: svc,
	}
}

func (m *MetaEvaluatorModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[MetaEvaluatorModule] %s started. High-speed regex checks online.", m.ModuleName)
}

func (m *MetaEvaluatorModule) onCFP(msg bus.Message) {
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
			"compute_cost": 1, // Almost free native string ops
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *MetaEvaluatorModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "evaluate_and_repair":
		result, err = m.Service.EvaluateAndRepair(params)
	case "check_structure":
		result, err = m.Service.CheckStructure(params)
	case "repair_formatting":
		result, err = m.Service.RepairFormatting(params)
	case "align_answers":
		result, err = m.Service.AlignAnswers(params)
	case "remove_disclaimers":
		result, err = m.Service.RemoveDisclaimers(params)
	case "close_tags":
		result, err = m.Service.CloseTags(params)
	case "check_compliance":
		result, err = m.Service.CheckCompliance(params)
	case "get_active_frameworks":
		result, err = m.Service.GetActiveFrameworks(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}

	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}
