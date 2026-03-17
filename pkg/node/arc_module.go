package node

import (
	"context"
	"fmt"
	"time"

	"github.com/thynaptic/oricli-go/pkg/arc"
	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ARCSwarmModule provides ARC solving capabilities via the Swarm Bus
type ARCSwarmModule struct {
	Bus    *bus.SwarmBus
	Solver *service.ARCSolverService
	ID     string
}

// NewARCSwarmModule creates a new ARC swarm module
func NewARCSwarmModule(swarmBus *bus.SwarmBus, solver *service.ARCSolverService) *ARCSwarmModule {
	return &ARCSwarmModule{
		Bus:    swarmBus,
		Solver: solver,
		ID:     "arc_solver_native",
	}
}

// Start initiates the subscription to the bus
func (n *ARCSwarmModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *ARCSwarmModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	if operation != "solve_arc" {
		return
	}

	taskID, _ := msg.Payload["task_id"].(string)

	// Bid for the task
	n.Bus.Publish(bus.Message{
		Protocol: bus.BID,
		Topic:    fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID: n.ID,
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"agent_id":     n.ID,
			"compute_cost": 0.8,
			"confidence":   1.0, // High confidence for native solver
		},
	})
}

func (n *ARCSwarmModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	// Execute
	ctx, cancel := context.WithTimeout(context.Background(), 300*time.Second)
	defer cancel()

	// Parse task
	taskMap, _ := params["task"].(map[string]interface{})
	task := n.parseARCTask(taskMap)

	result, err := n.Solver.SolveTask(ctx, task)

	if err != nil {
		n.Bus.Publish(bus.Message{
			Protocol: bus.ERROR,
			Topic:    "tasks.error",
			SenderID: n.ID,
			Payload: map[string]interface{}{
				"task_id": taskID,
				"error":   err.Error(),
			},
		})
		return
	}

	// Map to result structure
	resMap := map[string]interface{}{
		"prediction": result.Prediction,
		"confidence": result.Confidence,
		"method":     result.Method,
		"program":    result.Program,
	}

	// Publish result
	n.Bus.Publish(bus.Message{
		Protocol: bus.RESULT,
		Topic:    "tasks.result",
		SenderID: n.ID,
		Payload: map[string]interface{}{
			"task_id": taskID,
			"success": true,
			"result":  resMap,
		},
	})
}

func (n *ARCSwarmModule) parseARCTask(m map[string]interface{}) arc.Task {
	task := arc.Task{}

	trainRaw, _ := m["train"].([]interface{})
	for _, entry := range trainRaw {
		item := entry.(map[string]interface{})
		in := n.castGrid(item["input"].([]interface{}))
		out := n.castGrid(item["output"].([]interface{}))
		task.Train = append(task.Train, struct {
			Input  arc.Grid
			Output arc.Grid
		}{Input: in, Output: out})
	}

	testRaw, _ := m["test"].([]interface{})
	for _, entry := range testRaw {
		item := entry.(map[string]interface{})
		in := n.castGrid(item["input"].([]interface{}))
		task.Test = append(task.Test, struct {
			Input arc.Grid
		}{Input: in})
	}

	return task
}

func (n *ARCSwarmModule) castGrid(raw []interface{}) arc.Grid {
	grid := make(arc.Grid, len(raw))
	for i, r := range raw {
		rowRaw, _ := r.([]interface{})
		grid[i] = make([]int, len(rowRaw))
		for j, v := range rowRaw {
			grid[i][j] = int(service.ToFloat64(v))
		}
	}
	return grid
}
