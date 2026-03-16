package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// --- RETRIEVER AGENT ---

type RetrieverAgentModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.SwarmAgentService
}

func NewRetrieverAgentModule(swarmBus *bus.SwarmBus, svc *service.SwarmAgentService) *RetrieverAgentModule {
	return &RetrieverAgentModule{
		ID:         "go_native_retriever",
		ModuleName: "retriever_agent",
		Operations: []string{"retrieve_documents", "retrieve_from_sources", "expand_query", "filter_candidates", "process_retrieval", "generate_response"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *RetrieverAgentModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[SwarmAgent] %s started natively.", m.ModuleName)
}

func (m *RetrieverAgentModule) onCFP(msg bus.Message) {
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

func (m *RetrieverAgentModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "retrieve_documents", "retrieve_from_sources", "process_retrieval", "generate_response":
		result, err = m.Service.RetrieveDocuments(params)
	case "expand_query":
		result, err = m.Service.ExpandQuery(params)
	case "filter_candidates":
		result, err = m.Service.FilterCandidates(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}
	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}

// --- VERIFIER AGENT ---

type VerifierAgentModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.SwarmAgentService
}

func NewVerifierAgentModule(swarmBus *bus.SwarmBus, svc *service.SwarmAgentService) *VerifierAgentModule {
	return &VerifierAgentModule{
		ID:         "go_native_verifier",
		ModuleName: "verifier_agent",
		Operations: []string{"verify_facts", "check_citations", "validate_consistency", "assess_confidence", "process_verification"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *VerifierAgentModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[SwarmAgent] %s started natively.", m.ModuleName)
}

func (m *VerifierAgentModule) onCFP(msg bus.Message) {
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
	m.Bus.Publish(bus.Message{Protocol: bus.BID, Topic: fmt.Sprintf("tasks.bid.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"task_id": taskID, "operation": operation, "confidence": 1.0, "compute_cost": 2, "node_id": m.ID, "module_name": m.ModuleName}})
}

func (m *VerifierAgentModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "verify_facts", "process_verification":
		result, err = m.Service.VerifyFacts(params)
	case "check_citations":
		result, err = m.Service.CheckCitations(params)
	case "validate_consistency", "assess_confidence":
		result, err = m.Service.ValidateConsistency(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}
	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}

// --- CREATIVE WRITING AGENT ---

type CreativeWritingModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.SwarmAgentService
}

func NewCreativeWritingModule(swarmBus *bus.SwarmBus, svc *service.SwarmAgentService) *CreativeWritingModule {
	return &CreativeWritingModule{
		ID:         "go_native_creative_writing",
		ModuleName: "creative_writing",
		Operations: []string{"generate_story", "create_narrative", "apply_structure", "add_creative_elements", "generate_character", "create_setting"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *CreativeWritingModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[SwarmAgent] %s started natively.", m.ModuleName)
}

func (m *CreativeWritingModule) onCFP(msg bus.Message) {
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
	m.Bus.Publish(bus.Message{Protocol: bus.BID, Topic: fmt.Sprintf("tasks.bid.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"task_id": taskID, "operation": operation, "confidence": 1.0, "compute_cost": 2, "node_id": m.ID, "module_name": m.ModuleName}})
}

func (m *CreativeWritingModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "generate_story", "create_narrative", "apply_structure", "add_creative_elements", "create_setting":
		result, err = m.Service.GenerateStory(params)
	case "generate_character":
		result, err = m.Service.GenerateCharacter(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}
	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}
