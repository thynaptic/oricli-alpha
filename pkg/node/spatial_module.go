package node

import (
	"encoding/json"
	"fmt"
	"log"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type SpatialModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	GenService *service.GenerationService
}

func NewSpatialModule(swarmBus *bus.SwarmBus, gen *service.GenerationService) *SpatialModule {
	return &SpatialModule{
		ID:         "go_native_spatial",
		ModuleName: "spatial_reasoning_solver",
		Operations: []string{"solve_spatial_problem", "spatial_reasoning_solver"},
		Bus:        swarmBus,
		GenService: gen,
	}
}

func (m *SpatialModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[SpatialModule] %s started and listening for geometry/spatial tasks.", m.ModuleName)
}

func (m *SpatialModule) onCFP(msg bus.Message) {
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

func (m *SpatialModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[SpatialModule] Executing native %s for task %s", operation, taskID)

	puzzleText, _ := params["text"].(string)
	if puzzleText == "" {
		puzzleText, _ = params["query"].(string)
	}
	if puzzleText == "" {
		puzzleText, _ = params["input"].(string)
	}

	// 1. Extract Constraints
	prompt := fmt.Sprintf(`Extract spatial relations into JSON.
Puzzle: %s

JSON Format:
{
  "entities": ["apple", "box", "chair"],
  "relations": [
    {"entity1": "apple", "relation": "left_of", "entity2": "box"},
    {"entity1": "box", "relation": "above", "entity2": "chair"}
  ],
  "grid_size": 3,
  "question": "What is below the box?"
}`, puzzleText)

	resp, err := m.GenService.Generate(prompt, nil)
	if err != nil {
		m.sendError(taskID, msg.SenderID, err.Error())
		return
	}

	text, _ := resp["text"].(string)
	var problem service.SpatialProblem
	
	jsonStr := text
	if strings.Contains(text, "```json") {
		parts := strings.Split(text, "```json")
		if len(parts) > 1 {
			jsonStr = strings.Split(parts[1], "```")[0]
		}
	}

	if err := json.Unmarshal([]byte(jsonStr), &problem); err != nil {
		m.sendError(taskID, msg.SenderID, "failed to parse spatial constraints")
		return
	}

	// 2. Solve Grid
	solver := service.NewSpatialSolver(problem)
	assignments, err := solver.Solve()
	
	var result interface{}
	if err != nil {
		result = map[string]interface{}{"success": false, "error": err.Error()}
	} else {
		answer := solver.AnswerQuestion(assignments)
		result = map[string]interface{}{
			"success": true, 
			"assignments": assignments,
			"text": answer,
		}
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}

func (m *SpatialModule) sendError(taskID, recipient, err string) {
	m.Bus.Publish(bus.Message{
		Protocol:    bus.ERROR,
		Topic:       fmt.Sprintf("tasks.error.%s", taskID),
		SenderID:    m.ID,
		RecipientID: recipient,
		Payload:     map[string]interface{}{"error": err, "task_id": taskID},
	})
}
