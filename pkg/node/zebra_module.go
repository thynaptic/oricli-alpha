package node

import (
	"encoding/json"
	"fmt"
	"log"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ZebraModule handles logic puzzle solving natively in Go
type ZebraModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	GenService *service.GenerationService
}

func NewZebraModule(swarmBus *bus.SwarmBus, gen *service.GenerationService) *ZebraModule {
	return &ZebraModule{
		ID:         "go_native_zebra",
		ModuleName: "zebra_puzzle_solver",
		Operations: []string{"solve_zebra_puzzle", "parse_puzzle", "zebra_puzzle_solver"},
		Bus:        swarmBus,
		GenService: gen,
	}
}

func (m *ZebraModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[ZebraModule] %s started and listening for logic tasks.", m.ModuleName)
}

func (m *ZebraModule) onCFP(msg bus.Message) {
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

func (m *ZebraModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[ZebraModule] Executing native %s for task %s", operation, taskID)

	var result interface{}

	if operation == "solve_zebra_puzzle" || operation == "zebra_puzzle_solver" || operation == "parse_puzzle" {
		puzzleText, _ := params["input"].(string)
		if puzzleText == "" {
			puzzleText, _ = params["text"].(string)
		}

		// 1. Use GenService to extract constraints into JSON
		extractionPrompt := fmt.Sprintf(`Extract categories and constraints from this Zebra puzzle into JSON.
Puzzle: %s

JSON Format:
{
  "categories": { "color": ["red", "green"], "nation": ["british", "danish"] },
  "constraints": [
    { "type": "same", "value1": "british", "value2": "red" },
    { "type": "position", "value1": "danish", "pos": 1 },
    { "type": "left_of", "value1": "green", "value2": "white" }
  ],
  "num_houses": 5
}`, puzzleText)

		resp, err := m.GenService.Generate(extractionPrompt, nil)
		if err != nil {
			m.sendError(taskID, msg.SenderID, err.Error())
			return
		}

		text, _ := resp["text"].(string)
		var puzzle service.ZebraPuzzle
		
		// Clean up JSON
		jsonStr := text
		if strings.Contains(text, "```json") {
			parts := strings.Split(text, "```json")
			if len(parts) > 1 {
				jsonStr = strings.Split(parts[1], "```")[0]
			}
		}

		if err := json.Unmarshal([]byte(jsonStr), &puzzle); err != nil {
			m.sendError(taskID, msg.SenderID, "failed to parse puzzle constraints")
			return
		}

		// 2. Run the Go Solver
		solver := service.NewZebraSolver(puzzle)
		sol, err := solver.Solve()
		if err != nil {
			result = map[string]interface{}{"success": false, "error": err.Error()}
		} else {
			result = map[string]interface{}{"success": true, "solution": sol}
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

func (m *ZebraModule) sendError(taskID, recipient, err string) {
	m.Bus.Publish(bus.Message{
		Protocol:    bus.ERROR,
		Topic:       fmt.Sprintf("tasks.error.%s", taskID),
		SenderID:    m.ID,
		RecipientID: recipient,
		Payload:     map[string]interface{}{"error": err, "task_id": taskID},
	})
}
