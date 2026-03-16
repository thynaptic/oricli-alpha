package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// --- REASONING CODE COMPLETION MODULE ---

type ReasoningCodeCompletionModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.RealtimeCodeService
}

func NewReasoningCodeCompletionModule(swarmBus *bus.SwarmBus, svc *service.RealtimeCodeService) *ReasoningCodeCompletionModule {
	return &ReasoningCodeCompletionModule{
		ID:         "go_native_code_completion",
		ModuleName: "reasoning_code_completion",
		Operations: []string{
			"complete_code_reasoning",
			"complete_with_explanation",
			"verify_completion",
			"complete_with_style",
			"complete_multi_line",
		},
		Bus:     swarmBus,
		Service: svc,
	}
}

func (m *ReasoningCodeCompletionModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[RealtimeCodeModule] %s started. Lightning fast code completion active.", m.ModuleName)
}

func (m *ReasoningCodeCompletionModule) onCFP(msg bus.Message) {
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
			"compute_cost": 1,
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *ReasoningCodeCompletionModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "complete_code_reasoning", "complete_with_style", "complete_multi_line":
		result, err = m.Service.CompleteCode(params)
	case "complete_with_explanation":
		result, err = m.Service.CompleteWithExplanation(params)
	case "verify_completion":
		result, err = m.Service.VerifyCompletion(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}

	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}

// --- PROGRAM BEHAVIOR REASONING MODULE ---

type ProgramBehaviorModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.RealtimeCodeService
}

func NewProgramBehaviorModule(swarmBus *bus.SwarmBus, svc *service.RealtimeCodeService) *ProgramBehaviorModule {
	return &ProgramBehaviorModule{
		ID:         "go_native_program_behavior",
		ModuleName: "program_behavior_reasoning",
		Operations: []string{
			"predict_execution",
			"trace_execution_path",
			"find_edge_cases",
			"analyze_side_effects",
			"verify_correctness",
			"analyze_complexity",
		},
		Bus:     swarmBus,
		Service: svc,
	}
}

func (m *ProgramBehaviorModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[ProgramBehaviorModule] %s started.", m.ModuleName)
}

func (m *ProgramBehaviorModule) onCFP(msg bus.Message) {
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
			"compute_cost": 2,
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *ProgramBehaviorModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "predict_execution", "trace_execution_path":
		result, err = m.Service.PredictExecution(params)
	case "find_edge_cases":
		result, err = m.Service.FindEdgeCases(params)
	case "analyze_side_effects":
		result, err = m.Service.AnalyzeSideEffects(params)
	case "analyze_complexity":
		result, err = m.Service.AnalyzeComplexity(params)
	case "verify_correctness":
		result, err = m.Service.VerifyCompletion(params) // Reuse verifier
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}

	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}

// --- TEST GENERATION REASONING MODULE ---

type TestGenerationModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.RealtimeCodeService
}

func NewTestGenerationModule(swarmBus *bus.SwarmBus, svc *service.RealtimeCodeService) *TestGenerationModule {
	return &TestGenerationModule{
		ID:         "go_native_test_generation",
		ModuleName: "test_generation_reasoning",
		Operations: []string{
			"generate_tests",
			"identify_test_cases",
			"generate_edge_case_tests",
			"generate_property_tests",
			"analyze_coverage",
		},
		Bus:     swarmBus,
		Service: svc,
	}
}

func (m *TestGenerationModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[TestGenerationModule] %s started.", m.ModuleName)
}

func (m *TestGenerationModule) onCFP(msg bus.Message) {
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
			"compute_cost": 2,
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *TestGenerationModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "generate_tests", "generate_edge_case_tests", "generate_property_tests":
		result, err = m.Service.GenerateTests(params)
	case "identify_test_cases":
		result, err = m.Service.IdentifyTestCases(params)
	case "analyze_coverage":
		result, err = m.Service.AnalyzeCoverage(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}

	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}
