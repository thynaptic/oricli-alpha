package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type ResearchAgentModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	GenService *service.GenerationService
	WebFetch   *service.WebFetchService
	RagSvc     *service.RagService
}

func NewResearchAgentModule(swarmBus *bus.SwarmBus, gs *service.GenerationService, ws *service.WebFetchService, rs *service.RagService) *ResearchAgentModule {
	return &ResearchAgentModule{
		ID:         "go_native_researcher",
		ModuleName: "research_agent",
		Operations: []string{"research_task", "synthesize_findings"},
		Bus:        swarmBus,
		GenService: gs,
		WebFetch:   ws,
		RagSvc:     rs,
	}
}

func (m *ResearchAgentModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[ResearchAgent] %s active. Autonomous discovery online.", m.ModuleName)
}

func (m *ResearchAgentModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok { return }

	// Researcher also bids on 'execute_task' if agent_type is 'research'
	if operation == "execute_task" {
		task, _ := msg.Payload["params"].(map[string]interface{})["task"].(map[string]interface{})
		if task != nil && task["agent_type"] == "research" {
			m.bid(msg)
			return
		}
	}

	supported := false
	for _, op := range m.Operations {
		if op == operation {
			supported = true
			break
		}
	}

	if supported {
		m.bid(msg)
	}
}

func (m *ResearchAgentModule) bid(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	m.Bus.Publish(bus.Message{
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"confidence":    1.0,
			"compute_cost":  0.5,
			"node_id":       m.ID,
			"module_name":   m.ModuleName,
		},
	})
}

func (m *ResearchAgentModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result interface{}
	var err error

	if operation == "execute_task" {
		taskData, _ := params["task"].(map[string]interface{})
		query, _ := taskData["query"].(string)
		result, err = m.performResearch(query)
	} else if operation == "research_task" {
		query, _ := params["query"].(string)
		result, err = m.performResearch(query)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{
			Protocol: bus.ERROR,
			Topic:    fmt.Sprintf("tasks.error.%s", taskID),
			SenderID: m.ID,
			RecipientID: msg.SenderID,
			Payload:  map[string]interface{}{"error": err.Error(), "task_id": taskID},
		})
		return
	}

	m.Bus.Publish(bus.Message{
		Protocol: bus.RESULT,
		Topic:    fmt.Sprintf("tasks.result.%s", taskID),
		SenderID: m.ID,
		RecipientID: msg.SenderID,
		Payload:  map[string]interface{}{"result": result, "task_id": taskID},
	})
}

func (m *ResearchAgentModule) performResearch(query string) (map[string]interface{}, error) {
	log.Printf("[ResearchAgent] Performing deep research on: %s", query)
	
	// 1. Initial Synthesis (Planning)
	planPrompt := fmt.Sprintf("Research Plan for: %s\nOutline 3 key areas to investigate.", query)
	planRes, _ := m.GenService.Generate(planPrompt, nil)
	plan := planRes["text"].(string)

	// 2. Mock Web Search / Knowledge Retrieval (In a real scenario, we'd use WebFetch here)
	// For now, let's use the LLM to 'simulate' discovery based on its training data
	// but grounding it in our 'Research' persona.
	
	reportPrompt := fmt.Sprintf("Deep Research Report\nTopic: %s\nResearch Plan: %s\n\nProvide a detailed, technical report with breakthroughs and current status.", query, plan)
	reportRes, err := m.GenService.Generate(reportPrompt, map[string]interface{}{
		"system": "You are a world-class research agent. Provide detailed, factual, and technical reports.",
	})
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"query":  query,
		"plan":   plan,
		"report": reportRes["text"].(string),
		"method": "go_native_research",
	}, nil
}
